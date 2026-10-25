"""310 fixed requests, task-wide80 cap, no HTTP200 rerun, keep all receipts."""
import argparse,os,concurrent.futures
from collections import Counter,deque
import common028 as c
def run(workers=16,retry=False):
    jobs=c.verify_inputs();attempts,terminal=c.load_attempts(jobs);counts=Counter(a['request_id'] for a in attempts);pending=[j for j in jobs if j['request_id'] not in terminal and (counts[j['request_id']]==0 or retry and counts[j['request_id']]<3)]
    reg=c.read(c.OUT/'preparation_001/registry.json');cfg=c.api.load_config(c.ROOT/'.env.aliyun');c.require(cfg.endpoint==reg['endpoint'],'Endpoint changed');client=c.DirectClient(c.api.Config(cfg.api_key,cfg.base_url,c.MODEL),timeout=180)
    for j in pending:client.validate(j['body'])
    used=sum(a['charge_cny'] for a in attempts);c.require(used+sum(c.bound(j) for j in pending)<=80,'Whole remaining task conservative forecast over80')
    lock=c.OUT/'live.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd);pos=done=0;reserved=0.;inflight={};window=deque(maxlen=100);streak=0;stop=False;reason=None
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while pos<len(pending) and not stop or inflight:
                if (c.OUT/'stop_after_inflight.flag').exists():stop=True;reason='control_flag'
                while not stop and pos<len(pending) and len(inflight)<workers:
                    j=pending[pos];b=c.bound(j)
                    if used+reserved+b>80:stop=True;reason='budget_cap';break
                    d=c.OUT/'attempts'/f"{j['request_id']}_{counts[j['request_id']]+1:02}"
                    c.put(d/'request.json',dict(request_id=j['request_id'],attempt=counts[j['request_id']]+1,created_utc=c.now(),endpoint=cfg.endpoint,body=j['body'],body_sha256=c.fingerprint(j['body']),reservation_cny=b,prior_task_used_or_reserved_cny=used+reserved,cap_cny=80));reserved+=b;pos+=1;inflight[pool.submit(client.send,j['body'])]=(j,d,b)
                if not inflight:break
                completed,_=concurrent.futures.wait(inflight,timeout=5,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in completed:
                    j,d,b=inflight.pop(f);reserved-=b
                    try:tr=f.result()
                    except Exception:
                        used+=b;streak+=1
                        if streak>=10:stop=True;reason='systemic_transport_failure'
                        continue
                    c.put(d/'receipt.json',dict(request_sha256=c.sha(d/'request.json'),transport=tr));cost,basis=c.charge(j,tr);used+=cost;done+=1;parsed=c.parse(tr,j)
                    streak=streak+1 if tr['http_status']!=200 else 0
                    if tr['http_status']==200:window.append(parsed['status'] not in c.VALID)
                    if tr['http_status'] in (400,401,403,404) or parsed.get('model_returned') not in (None,c.MODEL):stop=True;reason='interface_or_model_error'
                    if streak>=10:stop=True;reason='systemic_transport_failure'
                    if sum(window)>=10 and sum(window)/len(window)>=.1:stop=True;reason='systemic_core_failure'
                    if done%25==0 or parsed['status'] not in c.VALID or stop:print(c.canonical(dict(completed_now=done,inflight=len(inflight),http=tr['http_status'],arm=j['arm'],parse=parsed['status'],used_cny=used,reserved_cny=reserved,stop=stop,reason=reason)),flush=True)
        print(c.canonical(dict(completed_now=done,stopped=stop,reason=reason,occupied_cny=used)),flush=True)
    finally:lock.unlink()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=16);p.add_argument('--retry-unanswered',action='store_true');a=p.parse_args();c.require(1<=a.workers<=32,'Invalid concurrency');run(a.workers,a.retry_unanswered)
