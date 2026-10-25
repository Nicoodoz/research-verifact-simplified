"""Task-scoped bounded scheduler. Qwen whitelist is prediction-only and frozen."""
import argparse,concurrent.futures,os
from collections import Counter,deque
import common026 as c
def run(stage,workers=24,retry=False):
    jobs=c.verify_inputs();attempts,terminal=c.load_attempts(jobs);allowed=c.eligible(jobs,stage);counts=Counter(a['request_id'] for a in attempts)
    pending=[j for j in allowed if j['request_id'] not in terminal and (not counts[j['request_id']] or (retry and counts[j['request_id']]<3))]
    cfg=c.load_config(c.ROOT/'.env.aliyun');reg=c.read(c.OUT/'preparation_001/registry.json');c.require(cfg.endpoint==reg['endpoint'],'Endpoint changed')
    clients={m:c.DirectClient(c.Config(cfg.api_key,cfg.base_url,model),timeout=180) for m,model in c.MODELS.items()}
    for j in pending:clients[j['model_key']].validate(j['body'])
    used=sum(a['charge_cny'] for a in attempts);observed={m:[a['charge_cny'] for a in attempts if a['model_key']==m and a['charge_basis']=='peak_no_cache_usage_estimate'] for m in c.MODELS}
    lock=c.OUT/'live.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    pos=done=0;reserved=0.;inflight={};stop=False;reason=None;window=deque(maxlen=100);streak=0
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while (pos<len(pending) and not stop) or inflight:
                if (c.OUT/'stop_after_inflight.flag').exists():stop=True;reason='control_flag'
                means={m:sum(observed[m])/len(observed[m]) if len(observed[m])>=8 else reg['expected_per_request'][m] for m in c.MODELS}
                rem=Counter(j['model_key'] for j in pending[pos:]);future_q=650*means['qwen'] if stage=='deepseek' else 0.
                if used+reserved+1.15*(future_q+sum(rem[m]*means[m] for m in rem))>80:stop=True;reason='cost_forecast'
                while not stop and pos<len(pending) and len(inflight)<workers:
                    j=pending[pos];b=c.bound(j)
                    if used+reserved+b>80:stop=True;reason='budget_reservation';break
                    rid=j['request_id'];d=c.OUT/'attempts'/f'{rid}_{counts[rid]+1:02d}'
                    c.put(d/'request.json',dict(request_id=rid,attempt=counts[rid]+1,stage=stage,created_utc=c.now(),endpoint=cfg.endpoint,body=j['body'],body_sha256=c.fingerprint(j['body']),reservation_cny=b,prior_task_used_or_reserved_cny=used+reserved,cap_cny=80))
                    reserved+=b;pos+=1;inflight[pool.submit(clients[j['model_key']].send,j['body'])]=(j,d,b)
                if not inflight:break
                completed,_=concurrent.futures.wait(inflight,timeout=5,return_when=concurrent.futures.FIRST_COMPLETED)
                for future in completed:
                    j,d,b=inflight.pop(future);reserved-=b
                    try:tr=future.result()
                    except Exception:
                        used+=b;streak+=1
                        if streak>=10:stop=True;reason='systemic_transport_failure'
                        continue
                    c.put(d/'receipt.json',dict(request_sha256=c.sha(d/'request.json'),transport=tr));cost,basis=c.charge(j,tr);used+=cost;done+=1
                    if basis=='peak_no_cache_usage_estimate':observed[j['model_key']].append(cost)
                    parsed=c.parse(tr,j['arm']=='S');streak=streak+1 if tr['http_status']!=200 else 0
                    if tr['http_status']==200:window.append(parsed['status'] not in c.VALID)
                    if tr['http_status'] in (400,401,403,404) or parsed.get('model_returned') not in (None,j['body']['model']):stop=True;reason='interface_or_model_error'
                    if streak>=10:stop=True;reason='systemic_transport_failure'
                    if len(window)>=10 and sum(window)>=10 and sum(window)/len(window)>=.1:stop=True;reason='systemic_core_failure'
                    if done%50==0 or parsed['status'] not in c.VALID or stop:print(c.canonical(dict(stage=stage,completed_now=done,inflight=len(inflight),http=tr['http_status'],parse=parsed['status'],used_cny=used,reserved_cny=reserved,stop=stop,reason=reason)),flush=True)
        print(c.canonical(dict(stage=stage,completed_now=done,stopped=stop,reason=reason,occupied_cny=used)),flush=True)
    finally:lock.unlink()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['deepseek','qwen'],required=True);p.add_argument('--workers',type=int,default=24);p.add_argument('--retry-unanswered',action='store_true');a=p.parse_args();c.require(1<=a.workers<=32,'Unregistered workers');run(a.stage,a.workers,a.retry_unanswered)
