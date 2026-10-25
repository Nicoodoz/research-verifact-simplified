"""One task ledger for constructor/reviewer/main; finite recovery and append-only I/O."""
import argparse,concurrent.futures,time
from collections import Counter
from common089 import *
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
RETRY={0,429,500,502,503,504}

def bound(j):
    assert len(canonical(j['body']).encode())+2000<128000,'price tier bound'
    ip,op=PRICES[j['body']['model']]
    return ((len(canonical(j['body']).encode())+2000)*ip+j['body']['max_tokens']*op)/1e6
def charge(req,tr):
    if not tr or tr.get('http_status')==0:return req['reserved_cny']
    if tr['http_status']!=200:return 0.
    try:
        u=json.loads(tr['body_text'])['usage'];i,o=u['prompt_tokens'],u['completion_tokens']
        assert type(i) is int and type(o) is int and 0<=i<=len(canonical(req['job']['body']).encode())+2000 and 0<=o<=req['job']['body']['max_tokens']
        ip,op=PRICES[req['job']['body']['model']];return (i*ip+o*op)/1e6
    except (ValueError,KeyError,TypeError,AssertionError):return req['reserved_cny']
def client(model):
    c=load_config(ROOT/'.env.aliyun')
    if c.base_url!='https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1':raise RuntimeError('endpoint drift')
    return DirectClient(Config(c.api_key,c.base_url,model),timeout=240)
def state():
    rows=[];success={};counts=Counter()
    for p in sorted((OUT/'attempts').glob('*/request.json')):
        req=read(p);rp=p.parent/'receipt.json';rec=read(rp) if rp.exists() else None;tr=rec['transport'] if rec else None
        if rec:assert rec['request_sha256']==sha(p)
        j=req['job'];rid=j['request_id'];counts[rid]+=1
        x=dict(request_id=rid,id=j['id'],sid=j['sid'],arm=j['arm'],phase=j['phase'],attempt_no=req['attempt_no'],
               created_utc=req['created_utc'],http_status=tr.get('http_status') if tr else None,cost_or_unknown_cny=charge(req,tr),
               request_source=p.relative_to(ROOT).as_posix(),receipt_source=rp.relative_to(ROOT).as_posix() if tr else None)
        rows.append(x)
        if tr and tr.get('http_status')==200:
            assert rid not in success,'successful request repeated';success[rid]=x
    return rows,success,counts
def freeze_job(phase,arm,pid,sid,body):
    digest=h(canonical(body));rid=h('089/'+phase+'/'+arm+'/'+pid+'/'+digest)[:28]
    j=dict(request_id=rid,phase=phase,arm=arm,id=pid,sid=sid,body=body,body_sha256=digest)
    p=OUT/'registered_jobs'/f'{rid}.json'
    if p.exists():assert read(p)==j
    else:put(p,j)
    return j
def attempt(j,n):
    cli=client(j['body']['model']);cli.validate(j['body'])
    folder=OUT/'attempts'/h(j['request_id']+f'/try{n}')[:24];folder.mkdir(parents=True,exist_ok=False)
    req=dict(job=j,attempt_no=n,created_utc=now(),reserved_cny=bound(j),cap_cny=20)
    put(folder/'request.json',req);t=time.monotonic()
    try:tr=cli.send(j['body'])
    except Exception as e:tr=dict(http_status=0,body_text='',outcome_unknown=True,error_type=type(e).__name__)
    tr['client_elapsed_seconds']=time.monotonic()-t
    put(folder/'receipt.json',dict(request_sha256=sha(folder/'request.json'),transport=tr))
    if tr.get('http_status')==200:
        native=json.loads(tr['body_text'])
        if native.get('model')!=j['body']['model']:raise RuntimeError('returned_model_mismatch')
    return tr
def process(j,past,sleep=time.sleep):
    for n in range(past+1,4):
        tr=attempt(j,n);s=tr['http_status']
        if s==200:return
        if s not in RETRY:raise RuntimeError(f'nonretryable_http_{s}')
        if n==3:raise RuntimeError(f'persistent_http_{s}')
        sleep(3*2**(n-1))
def can_dispatch(rows,active,j,count,limit):
    ids={x['request_id'] for x in active}
    used=sum(x['cost_or_unknown_cny'] for x in rows if x['request_id'] not in ids)
    return used+sum(3*bound(x) for x in active)+(3-count)*bound(j)<=limit+1e-9
def run_jobs(jobs,workers=1,limit=20):
    assert 1<=workers<=8 and limit<=20
    for j in jobs:
        assert read(OUT/'registered_jobs'/f"{j['request_id']}.json")==j
        client(j['body']['model']).validate(j['body'])
    lock=OUT/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    running={};stop=None;last=time.monotonic()
    try:
        _,success,_=state();pending=[j for j in jobs if j['request_id'] not in success]
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while pending or running:
                while pending and len(running)<workers and stop is None:
                    rows,success,counts=state();j=pending[0];count=counts[j['request_id']]
                    if count>=3:stop='attempts_exhausted';break
                    if not can_dispatch(rows,list(running.values()),j,count,limit):
                        if not running:stop='budget_reservation_limit'
                        break
                    pending.pop(0);running[pool.submit(process,j,count)]=j
                if not running:break
                done,_=concurrent.futures.wait(running,timeout=3,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in done:
                    running.pop(fut)
                    try:fut.result()
                    except Exception as e:stop=type(e).__name__+':'+str(e)[:120]
                if time.monotonic()-last>=30:
                    rows,s,_=state();print(canonical(dict(success_main=sum(x['phase']=='main' for x in s.values()),pending=len(pending),running=len(running),
                        used_or_unknown=sum(x['cost_or_unknown_cny'] for x in rows),stop=stop)),flush=True);last=time.monotonic()
        rows,s,_=state();assert sum(x['cost_or_unknown_cny'] for x in rows)<=20+1e-9
        if stop or any(j['request_id'] not in s for j in jobs):raise RuntimeError(stop or 'incomplete')
    finally:lock.unlink()
def call_json(j):
    run_jobs([j],workers=1,limit=2)
    _,s,_=state();path=ROOT/s[j['request_id']]['receipt_source'];tr=read(path)['transport']
    native=json.loads(tr['body_text']);content=native['choices'][0]['message'].get('content')
    try:obj=json.loads(content)
    except (ValueError,TypeError):obj=None
    return obj,path.relative_to(ROOT).as_posix()
def validate_main():
    f=read(OUT/'main_freeze.json');assert f['cap']==20
    for rel,d in f['sources'].items():assert sha(ROOT/rel)==d,rel
    for name,d in f['files'].items():assert sha(OUT/name)==d,name
    jobs=lines(OUT/'main_jobs.jsonl');assert len(jobs)==f['physical_jobs']
    return jobs
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('main','status','preflight'));a=p.parse_args()
    if a.action=='main':run_jobs(validate_main(),workers=8)
    elif a.action=='preflight':print(canonical(dict(jobs=len(validate_main()),network_calls=0)))
    else:
        rows,s,_=state();print(canonical(dict(attempts=len(rows),success=len(s),cost=sum(x['cost_or_unknown_cny'] for x in rows))))
