"""Only paid entry point for 087; append-only receipts, cap includes retries."""
import argparse, concurrent.futures, os, time
from collections import Counter
from common087 import *
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
RETRY={0,429,500,502,503,504}

def reservation(job):return ((len(canonical(job['body']).encode())+2000)*3+8192*9)/1e6
def charge(req,tr):
    if not tr or tr.get('http_status')==0:return req['reservation_cny']
    if tr['http_status']!=200:return 0.0
    try:
        u=json.loads(tr['body_text'])['usage'];i,o=int(u['prompt_tokens']),int(u['completion_tokens'])
        if not (0<=i<=len(canonical(req['job']['body']).encode())+2000 and 0<=o<=8192):raise ValueError('usage outside reserved bound')
        return (i*3+o*9)/1e6
    except (KeyError,TypeError,ValueError):return req['reservation_cny']

def client():
    c=load_config(ROOT/'.env.aliyun')
    if c.base_url!='https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1':raise RuntimeError('endpoint drift')
    return DirectClient(Config(c.api_key,c.base_url,MODEL),timeout=240)

def state():
    rows=[];success={};counts=Counter()
    for p in sorted((OUT/'attempts').glob('*/request.json')):
        req=read(p);rp=p.parent/'receipt.json';tr=read(rp)['transport'] if rp.exists() else None
        if rp.exists() and read(rp)['request_sha256']!=sha(p):raise RuntimeError('receipt binding')
        j=req['job'];rid=j['request_id'];counts[rid]+=1
        row=dict(request_id=rid,attempt_no=req['attempt_no'],id=j['id'],sid=j['sid'],arm=j['arm'],
                 created_utc=req['created_utc'],http_status=tr.get('http_status') if tr else None,
                 cost_or_unknown_cny=charge(req,tr),request_source=p.relative_to(ROOT).as_posix(),
                 receipt_source=rp.relative_to(ROOT).as_posix() if tr else None)
        rows.append(row)
        if tr and tr.get('http_status')==200:
            if rid in success:raise RuntimeError('duplicate successful logical request')
            success[rid]=row
    return rows,success,counts

def check_jobs():
    f=read(OUT/'freeze.json')
    if f['status']!='FROZEN_BEFORE_087_API_AND_TARGET_GT' or f['cap']!=CAP:raise RuntimeError('freeze/cap drift')
    for name,digest in f['files'].items():
        if sha(OUT/name)!=digest:raise RuntimeError('frozen input drift: '+name)
    for rel,digest in f['sources'].items():
        if sha(ROOT/rel)!=digest:raise RuntimeError('source drift: '+rel)
    jobs=lines(OUT/'jobs.jsonl');assert len(jobs)==f['jobs']==440
    assert len({j['request_id'] for j in jobs})==440
    for j in jobs:
        b=j['body'];assert h(canonical(b))==j['body_sha256']
        assert b['model']==MODEL and b['enable_thinking'] is True and b['reasoning_effort']=='high'
        assert b['temperature']==0 and b['max_tokens']==8192
    return jobs

def attempt(cli,j,n):
    folder=OUT/'attempts'/h(j['request_id']+f'/try{n}')[:24];folder.mkdir(parents=True,exist_ok=False)
    req=dict(created_utc=now(),attempt_no=n,job=j,reservation_cny=reservation(j),hard_cap=20,price_input=3,price_output=9)
    put(folder/'request.json',req)
    t=time.monotonic()
    try:tr=cli.send(j['body'])
    except Exception as exc:tr=dict(http_status=0,body_text='',outcome_unknown=True,error_type=type(exc).__name__)
    tr['client_elapsed_seconds']=time.monotonic()-t
    put(folder/'receipt.json',dict(request_sha256=sha(folder/'request.json'),transport=tr))
    if tr.get('http_status')==200:
        payload=json.loads(tr['body_text'])
        if payload.get('model')!=MODEL:raise RuntimeError('returned model mismatch')
        u=payload.get('usage',{})
        if u.get('prompt_tokens',0)>len(canonical(j['body']).encode())+2000 or u.get('completion_tokens',0)>8192:raise RuntimeError('usage reservation mismatch')
    return tr

def process(j,past,cli=None,sleep=time.sleep):
    cli=cli or client()
    for n in range(past+1,4):
        tr=attempt(cli,j,n);status=tr['http_status']
        if status==200:return
        if status not in RETRY:raise RuntimeError(f'nonretryable_http_{status}')
        if n==3:raise RuntimeError(f'recovery_exhausted_http_{status}')
        sleep(3*2**(n-1))

def can_dispatch(rows,running,job,count):
    active={x['request_id'] for x in running}
    used=sum(x['cost_or_unknown_cny'] for x in rows if x['request_id'] not in active)
    inflight=sum(reservation(x)*3 for x in running)
    return used+inflight+reservation(job)*(3-count)<=CAP+1e-9

def run(workers=8):
    assert 1<=workers<=8
    jobs=check_jobs();cli=client()
    for j in jobs:cli.validate(j['body'])
    lock=OUT/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    running={};stop=None;last=time.monotonic()
    try:
        rows,success,counts=state();pending=[j for j in jobs if j['request_id'] not in success]
        allowed={j['request_id'] for j in jobs};assert all(x['request_id'] in allowed for x in rows)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while pending or running:
                while pending and len(running)<workers and stop is None:
                    rows,success,counts=state();j=pending[0];count=counts[j['request_id']]
                    if count>=3:stop='previous_attempts_exhausted';break
                    if not can_dispatch(rows,list(running.values()),j,count):
                        if not running:stop='budget_reservation_limit'
                        break
                    pending.pop(0);running[pool.submit(process,j,count)]=j
                if not running:break
                done,_=concurrent.futures.wait(running,timeout=3,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in done:
                    running.pop(fut)
                    try:fut.result()
                    except Exception as exc:stop=type(exc).__name__+':'+str(exc)[:100]
                if time.monotonic()-last>=30:
                    rows,success,_=state();print(canonical(dict(success=len(success),pending=len(pending),running=len(running),
                        used_or_unknown_cny=round(sum(x['cost_or_unknown_cny'] for x in rows),6),stop=stop)),flush=True);last=time.monotonic()
        rows,success,_=state();result=dict(attempts=len(rows),success=len(success),jobs=len(jobs),stop=stop,
                                         used_or_unknown_cny=sum(x['cost_or_unknown_cny'] for x in rows))
        print(canonical(result),flush=True)
        assert result['used_or_unknown_cny']<=CAP+1e-9
        if stop or len(success)!=len(jobs):raise RuntimeError(stop or 'incomplete')
    finally:lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('preflight','run','status'));p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    if a.action=='run':run(a.workers)
    elif a.action=='preflight':
        jobs=check_jobs();c=client()
        for j in jobs:c.validate(j['body'])
        print(canonical(dict(jobs=len(jobs),network_calls=0,cap=CAP)))
    else:
        rows,s,_=state();print(canonical(dict(attempts=len(rows),success=len(s),cost=sum(x['cost_or_unknown_cny'] for x in rows))))
