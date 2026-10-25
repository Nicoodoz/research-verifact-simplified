"""Task-owned append-only receipts and cumulative cost cap; no API at import."""
import json,os,concurrent.futures
from collections import Counter,deque
import common044 as c
from verifact_research.inference.aliyun import Config,load_config

def state():
    attempts=[]; terminal={}
    for p in sorted((c.OUT/'attempts').glob('*/request.json')):
        rq=c.read(p); j=rq['job']; rp=p.parent/'receipt.json'
        c.require(rq['body_sha256']==c.digest(j['body']),'request body binding')
        tr=None; amount=rq['reservation_cny']; basis='unknown_reservation'
        if rp.exists():
            rec=c.read(rp); c.require(rec['request_sha256']==c.sha(p),'receipt binding')
            tr=rec['transport']; amount,basis=c.charge(j,tr)
            if tr.get('http_status')==200:
                c.require(j['request_id'] not in terminal,'duplicate HTTP200')
                terminal[j['request_id']]={'job':j,'parsed':c.parse_job(j,tr),'transport':tr,'receipt':str(rp.relative_to(c.ROOT))}
        attempts.append({'request_id':j['request_id'],'stage':rq['stage'],'model_key':j['model_key'],
          'charge_cny':amount,'basis':basis,'http_status':tr.get('http_status') if tr else None,'path':str(p.relative_to(c.ROOT))})
    return attempts,terminal

def run(stage,workers=8):
    jobs=c.lines(c.OUT/stage/'jobs.jsonl'); a,term=state(); used=sum(x['charge_cny'] for x in a)
    counts=Counter(x['request_id'] for x in a); pending=[]
    for j in jobs:
        if j['request_id'] in term: c.require(term[j['request_id']]['job']==j,'existing job differs'); continue
        if counts[j['request_id']]: raise RuntimeError('Unresolved request; inspect receipt before explicit recovery')
        pending.append(j)
    cfg=load_config(c.ROOT/'.env.aliyun')
    clients={k:c.DirectClient(Config(cfg.api_key,cfg.base_url,m),timeout=180) for k,m in c.MODELS.items()}
    for j in pending: clients[j['model_key']].validate(j['body'])
    lock=c.OUT/'live.lock'; fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd,str(os.getpid()).encode()); os.close(fd)
    queue=deque(pending); inflight={}; reserved=0.; done=0; stop=None; bad=deque(maxlen=50)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while (queue and stop is None) or inflight:
                while queue and stop is None and len(inflight)<workers:
                    j=queue.popleft(); reserve=c.bound(j)
                    if used+reserved+reserve>c.CAP: stop='budget80'; break
                    num=counts[j['request_id']]+1
                    dst=c.OUT/'attempts'/f"{c.digest(j['request_id'])[:24]}_{num:02}"
                    c.require(not dst.exists(),'attempt collision')
                    c.put(dst/'request.json',dict(created_utc=c.now(),stage=stage,job=j,attempt=num,
                      body_sha256=c.digest(j['body']),reservation_cny=reserve,prior_used_reserved=used+reserved,cap=c.CAP))
                    counts[j['request_id']]+=1; reserved+=reserve
                    f=pool.submit(clients[j['model_key']].send,j['body']); inflight[f]=(j,dst,reserve)
                if not inflight: break
                ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in ready:
                    j,dst,reserve=inflight.pop(f); reserved-=reserve
                    try: tr=f.result()
                    except Exception as exc:
                        tr=dict(http_status=0,body_text='',headers={},outcome_unknown=True,
                          started_utc=c.now(),ended_utc=c.now(),exception_type=type(exc).__name__)
                    c.put(dst/'receipt.json',{'request_sha256':c.sha(dst/'request.json'),'transport':tr})
                    amount,basis=c.charge(j,tr); used+=amount; done+=1; parsed=c.parse_job(j,tr)
                    status=tr.get('http_status'); bad.append(status!=200 or parsed.get('status') not in c.VALID)
                    if status==200:
                        returned=json.loads(tr['body_text']).get('model')
                        if returned!=c.MODELS[j['model_key']]: stop='unexpected_model'
                        term[j['request_id']]={'job':j,'parsed':parsed,'transport':tr}
                    elif status in (429,500,502,503,504) and counts[j['request_id']]<2: queue.append(j)
                    elif status in (400,401,403,404): stop='interface_or_auth'
                    elif status==0: stop='unknown_transport_do_not_repeat'
                    if amount>reserve+1e-9: stop='reservation_underestimate'
                    if len(bad)>=10 and sum(bad)>=10 and sum(bad)/len(bad)>.2: stop='systemic_invalid'
                    info=dict(stage=stage,completed_now=done,pending=len(queue),inflight=len(inflight),
                      used_cny=used,reserved_cny=reserved,stop=stop,updated_utc=c.now())
                    c.atomic_status(c.OUT/'execution_status.json',info)
                    if done%50==0 or stop: print(stage,done,'pending',len(queue),'used',round(used,4),'stop',stop,flush=True)
        terminal_count=sum(j['request_id'] in term for j in jobs)
        serial=1+len(list((c.OUT/stage).glob('execution_*.json')))
        c.put(c.OUT/stage/f'execution_{serial:03}.json',dict(created_utc=c.now(),planned=len(jobs),terminal=terminal_count,
          completed_now=done,used_cny=used,stop=stop))
        if stop or terminal_count!=len(jobs): raise RuntimeError(str(stop or 'incomplete_stage'))
        print('COMPLETE',stage,terminal_count,'cumulative_cost',round(used,6),flush=True)
    finally:
        if lock.exists(): lock.unlink()
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('stage'); ap.add_argument('--workers',type=int,default=8)
    args=ap.parse_args(); run(args.stage,args.workers)
