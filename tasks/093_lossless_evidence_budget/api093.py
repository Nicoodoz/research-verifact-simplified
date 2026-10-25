"""Append-only task accounting and finite recovery; no successful-answer retries."""
import argparse,concurrent.futures,json,os,sys,threading,time
from collections import Counter
import common093 as c
from prepare093 import bound,MODEL
sys.path.insert(0,str(c.ROOT/'src'));sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
LOCK=threading.Lock();RETRY={0,408,429,500,502,503,504}
def cost(req,tr):
    if tr and tr.get('http_status')==200:
        try:
            u=json.loads(tr['body_text'])['usage'];i,o=u['prompt_tokens'],u['completion_tokens']
            assert type(i)is int and type(o)is int and 0<=i<=len(json.dumps(req['job']['body'],ensure_ascii=False).encode())+2000 and 0<=o<=8192
            return (i*3+o*9)/1e6
        except (KeyError,ValueError,TypeError,AssertionError):pass
    # All unresolved/failed requests retain a conservative reservation; no free retry assumption.
    return req['reserved_cny']
def state():
    rows=[];success={};counts=Counter()
    for p in sorted((c.PRIVATE/'attempts').glob('*/request.json')):
        q=c.read(p);rp=p.parent/'receipt.json';rec=c.read(rp) if rp.exists() else None;tr=rec['transport'] if rec else None
        if rec:assert rec['request_sha256']==c.sha(p)
        j=q['job'];rid=j['request_id'];counts[rid]+=1
        r=dict(request_id=rid,id=j['id'],phase=j['phase'],attempt=q['attempt'],http_status=tr['http_status'] if tr else 0,cost_or_reserved_cny=cost(q,tr),request_path=p.relative_to(c.ROOT).as_posix(),receipt_path=rp.relative_to(c.ROOT).as_posix() if rec else None,body_sha256=j['body_sha256'])
        rows.append(r)
        if tr and tr['http_status']==200:
            assert rid not in success,'successful request repeated'
            success[rid]=r
    return rows,success,counts
def load_jobs():
    f=c.read(c.OUT/'main_freeze.json')
    assert f['cap_cny']==20
    for p,d in f['sources'].items():assert c.sha(c.ROOT/p)==d,p
    e=c.read(c.OUT/'execution_freeze.json')
    for p,d in e['source_sha256'].items():assert c.sha(c.ROOT/p)==d,p
    return [c.read(c.PRIVATE/'preflight.json')]+c.lines(c.PRIVATE/'main_jobs.jsonl')
def check_budget(rows,success,counts,j,alljobs):
    remaining=sum(x['bound_cny'] for x in alljobs if x['request_id']!=j['request_id'] and x['request_id'] not in success and counts[x['request_id']]==0)
    return sum(r['cost_or_reserved_cny'] for r in rows)+j['bound_cny']+remaining<=20+1e-9
def process(j,alljobs):
    cfg=load_config(c.ROOT/'.env.aliyun')
    assert cfg.base_url=='https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1','endpoint changed'
    cli=DirectClient(Config(cfg.api_key,cfg.base_url,MODEL),timeout=240);cli.validate(j['body'])
    while True:
        with LOCK:
            rows,success,counts=state()
            if j['request_id'] in success:return
            n=counts[j['request_id']]+1
            if n>3:raise RuntimeError('finite retries exhausted')
            if not check_budget(rows,success,counts,j,alljobs):raise RuntimeError('whole-task budget including remaining cohort exhausted')
            folder=c.PRIVATE/'attempts'/f"{j['request_id']}_try{n}";folder.mkdir(parents=True,exist_ok=False)
            c.put(folder/'request.json',dict(job=j,attempt=n,utc=c.now(),reserved_cny=j['bound_cny'],task_cap_cny=20))
        started=time.monotonic()
        try:tr=cli.send(j['body'])
        except Exception as e:tr=dict(http_status=0,body_text='',outcome_unknown=True,error_type=type(e).__name__)
        tr['client_elapsed_seconds']=time.monotonic()-started
        c.put(folder/'receipt.json',dict(request_sha256=c.sha(folder/'request.json'),transport=tr))
        if tr['http_status']==200:
            native=json.loads(tr['body_text'])
            if native.get('model')!=MODEL:raise RuntimeError('returned model mismatch')
            return
        if tr['http_status'] not in RETRY:raise RuntimeError('nonretryable HTTP '+str(tr['http_status']))
        if n>=3:raise RuntimeError('persistent HTTP '+str(tr['http_status']))
        time.sleep(3*2**(n-1))
def run(stage):
    alljobs=load_jobs();jobs=[j for j in alljobs if j['phase']==stage]
    if stage=='main':assert c.read(c.OUT/'preflight_result.json')['valid']
    path=c.PRIVATE/'run.lock';fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        _,s,_=state();pending=[j for j in jobs if j['request_id'] not in s];active={};last=time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            while pending or active:
                while pending and len(active)<4:
                    j=pending.pop(0);active[pool.submit(process,j,alljobs)]=j
                done,_=concurrent.futures.wait(active,timeout=3,return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:active.pop(future);future.result()
                if time.monotonic()-last>30:
                    rows,s,_=state();print(dict(success_main=sum(r['phase']=='main' for r in s.values()),total_main=len(alljobs)-1,pending=len(pending),active=len(active),cost_or_reserved=sum(r['cost_or_reserved_cny'] for r in rows)),flush=True);last=time.monotonic()
    finally:path.unlink()
    rows,s,_=state();assert all(j['request_id'] in s for j in jobs) and sum(r['cost_or_reserved_cny'] for r in rows)<=20
    print('Complete',stage,len(jobs),'cost/reserve',sum(r['cost_or_reserved_cny'] for r in rows),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['preflight','main','status']);a=p.parse_args()
    if a.stage=='status':
        rows,s,_=state();print(dict(attempts=len(rows),success=len(s),cost=sum(r['cost_or_reserved_cny'] for r in rows)))
    else:run(a.stage)
