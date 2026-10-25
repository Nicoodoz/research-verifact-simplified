"""024 same frozen jobs, rolling bounded concurrency; no result-dependent experiment changes."""
import argparse,concurrent.futures,os
from collections import Counter
import format024 as c

def run(workers=32,retry=False):
    c.require(1<=workers<=64,'Workers outside registered engineering limit')
    jobs=c.verify_inputs();attempts,terminal=c.load_attempts(jobs)
    c.require(all(x['status']=='success' for x in terminal.values()),'Invalid terminal output; no replacement')
    count=Counter(a['request_id'] for a in attempts)
    pending=[j for j in jobs if j['request_id'] not in terminal and (not count[j['request_id']] or (retry and count[j['request_id']]<3))]
    cfg=c.load_config(c.ROOT/'.env.aliyun');reg=c.read(c.OUT/'preparation_001/registry.json')
    c.require(cfg.endpoint==reg['endpoint'],'Endpoint changed')
    clients={m:c.AliyunClient(c.Config(cfg.api_key,cfg.base_url,model),timeout=180) for m,model in c.MODELS.items()}
    for j in pending:clients[j['model_key']].validate(j['body'])
    used=sum(x['charge_cny'] for x in attempts)
    observed={m:[x['charge_cny'] for x in attempts if x['model_key']==m and x['charge_basis']=='peak_no_cache_usage_estimate'] for m in c.MODELS}
    lock=c.OUT/'live.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    inflight={};reserved=0.;pos=done=0;stop=False
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while (pos<len(pending) and not stop) or inflight:
                if (c.OUT/'stop_after_inflight.flag').exists():stop=True
                # Forecast is conservative: in-flight upper bounds plus unsent mean costs with15% margin.
                rem=Counter(j['model_key'] for j in pending[pos:])
                forecast=used+reserved+sum(n*(sum(observed[m])/len(observed[m]) if len(observed[m])>=8 else reg['expected_cny'][m]/1758)*1.15 for m,n in rem.items())
                if forecast>c.CAP:stop=True
                while not stop and pos<len(pending) and len(inflight)<workers:
                    j=pending[pos];b=c.bound(j)
                    if used+reserved+b>c.CAP:stop=True;break
                    rid=j['request_id'];d=c.OUT/'attempts'/f'{rid}_{count[rid]+1:02d}'
                    c.put(d/'request.json',dict(request_id=rid,attempt=count[rid]+1,created_utc=c.now(),endpoint=cfg.endpoint,body=j['body'],body_sha256=c.fingerprint(j['body']),reservation_cny=b,prior_task_used_or_reserved_cny=used+reserved,cap_cny=80))
                    reserved+=b;pos+=1;inflight[pool.submit(clients[j['model_key']].send,j['body'])]=(j,d,b)
                if not inflight:break
                completed,_=concurrent.futures.wait(inflight,timeout=5,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in completed:
                    j,d,b=inflight.pop(f);reserved-=b
                    try:tr=f.result()
                    except Exception:
                        used+=b;stop=True;continue
                    c.put(d/'receipt.json',dict(request_sha256=c.file_hash(d/'request.json'),transport=tr))
                    cost,basis=c.charge(j,tr);used+=cost;done+=1
                    if basis=='peak_no_cache_usage_estimate':observed[j['model_key']].append(cost)
                    parsed=c.parse(tr,j['arm']=='S')
                    if tr['http_status']!=200 or parsed['status']!='success' or parsed.get('model_returned')!=j['body']['model']:stop=True
                    if done%25==0 or stop:
                        print(c.canonical(dict(completed_now=done,submitted_now=pos,inflight=len(inflight),model=j['model_key'],http_status=tr['http_status'],parse=parsed['status'],errors=parsed['errors'],used_cny=used,inflight_reserved_cny=reserved,stop=stop)),flush=True)
            print(c.canonical(dict(completed_now=done,submitted_now=pos,stopped=stop,used_or_reserved_cny=used)),flush=True)
    finally:lock.unlink()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=32);p.add_argument('--retry-unanswered',action='store_true');a=p.parse_args();run(a.workers,a.retry_unanswered)
