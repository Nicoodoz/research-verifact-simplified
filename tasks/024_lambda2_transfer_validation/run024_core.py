"""Bounded rolling scheduler; sparse core/format errors never stop remaining jobs."""
import argparse,concurrent.futures,os
from collections import Counter,deque
import core024 as c
def run(workers=32,retry=False):
    c.require(1<=workers<=64,'Invalid workers')
    jobs=c.verify_inputs();attempts,terminal=c.load_attempts(jobs)
    count=Counter(a['request_id'] for a in attempts)
    pending=[j for j in jobs if j['request_id'] not in terminal and (not count[j['request_id']] or (retry and count[j['request_id']]<3))]
    cfg=c.load_config(c.ROOT/'.env.aliyun');reg=c.read(c.OUT/'preparation_001/registry.json')
    c.require(cfg.endpoint==reg['endpoint'],'Endpoint changed')
    clients={m:c.AliyunClient(c.Config(cfg.api_key,cfg.base_url,model),timeout=180) for m,model in c.MODELS.items()}
    for j in pending:clients[j['model_key']].validate(j['body'])
    used=sum(a['charge_cny'] for a in attempts)
    observed={m:[a['charge_cny'] for a in attempts if a['model_key']==m and a['charge_basis']=='peak_no_cache_usage_estimate'] for m in c.MODELS}
    core_window=deque(maxlen=100);streak=0
    lock=c.OUT/'live.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    inflight={};reserved=0.;pos=done=0;stop=False;stop_reason=None
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while (pos<len(pending) and not stop) or inflight:
                if (c.OUT/'stop_after_inflight.flag').exists():stop=True;stop_reason='control_flag'
                rem=Counter(j['model_key'] for j in pending[pos:])
                forecast=used+reserved+sum(n*(sum(observed[m])/len(observed[m]) if len(observed[m])>=8 else reg['expected_cny'][m]/1758)*1.15 for m,n in rem.items())
                if forecast>c.CAP:stop=True;stop_reason='cost_forecast'
                while not stop and pos<len(pending) and len(inflight)<workers:
                    j=pending[pos];b=c.bound(j)
                    if used+reserved+b>c.CAP:stop=True;stop_reason='budget_reservation';break
                    rid=j['request_id'];d=c.OUT/'attempts'/f'{rid}_{count[rid]+1:02d}'
                    c.put(d/'request.json',dict(request_id=rid,attempt=count[rid]+1,created_utc=c.now(),endpoint=cfg.endpoint,body=j['body'],body_sha256=c.fingerprint(j['body']),reservation_cny=b,prior_task_used_or_reserved_cny=used+reserved,cap_cny=80))
                    reserved+=b;pos+=1;inflight[pool.submit(clients[j['model_key']].send,j['body'])]=(j,d,b)
                if not inflight:break
                completed,_=concurrent.futures.wait(inflight,timeout=5,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in completed:
                    j,d,b=inflight.pop(f);reserved-=b
                    try:tr=f.result()
                    except Exception:
                        used+=b;streak+=1
                        if streak>=10:stop=True;stop_reason='systemic_transport_failure'
                        continue
                    c.put(d/'receipt.json',dict(request_sha256=c.file_hash(d/'request.json'),transport=tr))
                    cost,basis=c.charge(j,tr);used+=cost;done+=1
                    if basis=='peak_no_cache_usage_estimate':observed[j['model_key']].append(cost)
                    parsed=c.parse(tr,j['arm']=='S')
                    streak=streak+1 if tr['http_status']!=200 else 0
                    if tr['http_status']==200:core_window.append(parsed['status'] not in c.VALID)
                    if tr['http_status'] in (400,401,403,404) or parsed.get('model_returned') not in (None,j['body']['model']):stop=True;stop_reason='interface_or_model_error'
                    if streak>=10:stop=True;stop_reason='systemic_transport_failure'
                    if len(core_window)>=10 and sum(core_window)>=10 and sum(core_window)/len(core_window)>=.1:stop=True;stop_reason='systemic_core_failure'
                    if done%25==0 or stop or parsed['status'] not in c.VALID:
                        print(c.canonical(dict(completed_now=done,submitted_now=pos,inflight=len(inflight),model=j['model_key'],http_status=tr['http_status'],parse=parsed['status'],errors=parsed['errors'],used_cny=used,inflight_reserved_cny=reserved,stop=stop,stop_reason=stop_reason)),flush=True)
            print(c.canonical(dict(completed_now=done,submitted_now=pos,stopped=stop,stop_reason=stop_reason,used_or_reserved_cny=used)),flush=True)
    finally:lock.unlink()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=32);p.add_argument('--retry-unanswered',action='store_true');a=p.parse_args();run(a.workers,a.retry_unanswered)
