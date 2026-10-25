"""Explicit live runner. All attempts append-only; HTTP200 is never retried."""
import argparse,concurrent.futures,os,time
from collections import Counter
import format024 as c
def run(limit,workers,health,retry):
    jobs=c.verify_inputs();attempts,terminal=c.load_attempts(jobs)
    c.require(all(p['status']=='success' for p in terminal.values()),'Invalid terminal output: stop, no replacement')
    counts=Counter(a['request_id'] for a in attempts)
    pending=[j for j in jobs if j['request_id'] not in terminal and (not counts[j['request_id']] or (retry and counts[j['request_id']]<3))]
    if health:
        pending=[next(j for j in pending if j['model_key']==m and j['arm']==a) for m in c.MODELS for a in ('B','S')]
    pending=pending[:limit] if limit else pending
    cfg=c.load_config(c.ROOT/'.env.aliyun');reg=c.read(c.OUT/'preparation_001/registry.json')
    c.require(cfg.endpoint==reg['endpoint'],'Endpoint changed')
    clients={m:c.AliyunClient(c.Config(cfg.api_key,cfg.base_url,model),timeout=180) for m,model in c.MODELS.items()}
    for j in pending:clients[j['model_key']].validate(j['body'])
    used=sum(a['charge_cny'] for a in attempts)
    observed={m:[a['charge_cny'] for a in attempts if a['model_key']==m and a['charge_basis']=='peak_no_cache_usage_estimate'] for m in c.MODELS}
    lock=c.OUT/'live.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    done=0;stop=False
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for start in range(0,len(pending),workers):
                remaining=Counter(j['model_key'] for j in pending[start:])
                forecast=used+sum(n*(sum(observed[m])/len(observed[m]) if len(observed[m])>=8 else reg['expected_cny'][m]/1758)*1.15 for m,n in remaining.items())
                if forecast>c.CAP:
                    print(c.canonical(dict(stop_reason='remaining_cost_forecast',forecast_cny=forecast)),flush=True);stop=True;break
                futures={};reserve=0
                for j in pending[start:start+workers]:
                    b=c.bound(j)
                    if used+reserve+b>c.CAP:stop=True;break
                    rid=j['request_id'];no=counts[rid]+1;d=c.OUT/'attempts'/f'{rid}_{no:02d}'
                    c.put(d/'request.json',dict(request_id=rid,attempt=no,created_utc=c.now(),endpoint=cfg.endpoint,body=j['body'],body_sha256=c.fingerprint(j['body']),reservation_cny=b,prior_task_used_or_reserved_cny=used+reserve,cap_cny=80))
                    reserve+=b;futures[pool.submit(clients[j['model_key']].send,j['body'])]=(j,d,b)
                for future in concurrent.futures.as_completed(futures):
                    j,d,b=futures[future]
                    try:tr=future.result()
                    except Exception:
                        # Never expose transport exceptions containing credentials. Durable reservation remains.
                        used+=b;stop=True;continue
                    c.put(d/'receipt.json',dict(request_sha256=c.file_hash(d/'request.json'),transport=tr))
                    cost,basis=c.charge(j,tr);used+=cost;done+=1
                    if basis=='peak_no_cache_usage_estimate':observed[j['model_key']].append(cost)
                    parsed=c.parse(tr,j['arm']=='S')
                    if tr['http_status']!=200 or parsed['status']!='success' or parsed.get('model_returned')!=j['body']['model']:stop=True
                    print(c.canonical(dict(completed_now=done,model=j['model_key'],arm=j['arm'],http_status=tr['http_status'],parse=parsed['status'],errors=parsed['errors'],used_or_reserved_cny=round(used,8))),flush=True)
                if stop:break
        print(c.canonical(dict(stopped=stop,completed_now=done,used_or_reserved_cny=used)),flush=True)
    finally:lock.unlink()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=0);p.add_argument('--workers',type=int,default=8);p.add_argument('--health',action='store_true');p.add_argument('--retry-unanswered',action='store_true');a=p.parse_args();run(a.limit,a.workers,a.health,a.retry_unanswered)
