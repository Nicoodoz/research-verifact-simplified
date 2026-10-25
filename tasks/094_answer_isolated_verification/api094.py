"""Append-only staged runner with full remaining-work reservations."""
import argparse,concurrent.futures,json,os,sys,threading,time
import common094 as c
sys.path.insert(0,str(c.ROOT/'src'));sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
LOCK=threading.Lock();RETRY={0,408,429,500,502,503,504}
def state():
    rows=[];success={}
    for p in sorted((c.PRIVATE/'attempts').glob('*/request.json')):
        req=c.read(p);j=req['job'];rp=p.parent/'receipt.json';tr=c.read(rp)['transport'] if rp.exists() else None;charge=j['bound_cny']
        if tr and tr['http_status']==200:
            n=json.loads(tr['body_text']);u=n.get('usage',{})
            assert n['model']==c.MODEL
            if type(u.get('prompt_tokens'))is int and type(u.get('completion_tokens'))is int:
                actual=(u['prompt_tokens']*3+u['completion_tokens']*9)/1e6;assert actual<=charge+1e-8;charge=actual
            assert j['request_id'] not in success
            success[j['request_id']]=dict(job=j,tr=tr)
        rows.append(dict(request_id=j['request_id'],id=j['id'],stage=j['stage'],arm=j['arm'],http_status=tr['http_status'] if tr else 0,charge_cny=charge,attempt=req['attempt'],request_path=p.relative_to(c.ROOT).as_posix(),receipt_sha256=c.sha(rp) if rp.exists() else None))
    return rows,success
def remaining(success,current):
    freeze=c.read(c.OUT/'design_freeze.json');total=0
    for pid,stages in freeze['allocations'].items():
        for key,bound in stages.items():
            stage,arm=('generate','shared') if key=='generate' else key.split('_')
            rid=c.h('094/'+pid+'/'+stage+'/'+arm)[:28]
            if rid!=current and rid not in success:total+=bound
    for j in c.lines(c.PRIVATE/'preflight_jobs.jsonl'):
        if j['request_id']!=current and j['request_id'] not in success:total+=j['bound_cny']
    return total
def process(j):
    cfg=load_config(c.ROOT/'.env.aliyun');assert cfg.base_url=='https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'
    cli=DirectClient(Config(cfg.api_key,cfg.base_url,c.MODEL),timeout=240)
    for attempt in range(1,4):
        with LOCK:
            rows,s=state()
            if j['request_id'] in s:return
            prior=[r for r in rows if r['request_id']==j['request_id']]
            if attempt<=len(prior):continue
            assert sum(r['charge_cny'] for r in rows)+remaining(s,j['request_id'])+j['bound_cny']<=20,'whole-task reserve exceeded'
            folder=c.PRIVATE/'attempts'/f"{j['request_id']}_{attempt}";folder.mkdir(parents=True,exist_ok=False)
            c.put(folder/'request.json',dict(job=j,attempt=attempt,utc=c.now()))
        start=time.monotonic();tr=cli.send(j['body']);tr['client_elapsed_seconds']=time.monotonic()-start
        c.put(folder/'receipt.json',dict(transport=tr,request_sha256=c.sha(folder/'request.json')))
        if tr['http_status']==200:assert json.loads(tr['body_text'])['model']==c.MODEL;return
        if tr['http_status'] not in RETRY:raise RuntimeError('nonretryable '+str(tr['http_status']))
        time.sleep(3*attempt)
    raise RuntimeError('finite recovery exhausted')
def run(stage):
    for p,h in c.read(c.OUT/'design_freeze.json')['sources'].items():assert c.sha(c.ROOT/p)==h,p
    for p,h in c.read(c.OUT/'runner_freeze.json')['sources'].items():assert c.sha(c.ROOT/p)==h,p
    jobs=c.lines(c.PRIVATE/(stage+'_jobs.jsonl'));jobs=sorted(jobs,key=lambda j:c.h('094/dispatch/'+j['request_id']))
    lock=c.PRIVATE/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(process,j) for j in jobs]
            for i,f in enumerate(concurrent.futures.as_completed(futures),1):
                f.result()
                if i%8==0:print(stage,i,'/',len(jobs),flush=True)
    finally:lock.unlink()
    rows,s=state();assert all(j['request_id'] in s for j in jobs)
    print('complete',stage,'whole task cost/reserved',sum(r['charge_cny'] for r in rows),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['preflight','generate','extract','judge']);run(p.parse_args().stage)
