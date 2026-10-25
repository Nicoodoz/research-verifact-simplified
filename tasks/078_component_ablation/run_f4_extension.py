"""078 F4 extension: original spend carried forward under approved cumulative 35 CNY cap."""
import os,time,sys,concurrent.futures
from collections import deque,defaultdict
import common078 as c
c.OUT=c.OUT/'f4_extension_001'
c.CAP=35.
sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
RETRYABLE={0,429,500,502,503,504};MAX_ATTEMPTS=3
def state():
 attempts=[];answered={}
 for p in sorted((c.OUT/'attempts').glob('*/request.json')):
  rq=c.read(p);rp=p.parent/'receipt.json';tr=None
  if rp.exists():
   rc=c.read(rp);assert rc['request_sha256']==c.sha(p);tr=rc['transport']
  job=rq['job'];a=dict(request_id=job['request_id'],id=job['id'],arm=job['arm'],attempt_no=rq['attempt_no'],http_status=tr.get('http_status') if tr else None,cost_cny=c.charge(tr,rq['reservation_cny']),reservation_cny=rq['reservation_cny'],request_source=p.relative_to(c.ROOT).as_posix(),receipt_source=rp.relative_to(c.ROOT).as_posix() if rp.exists() else None)
  attempts.append(a)
  if tr and tr['http_status']==200:
   assert job['request_id'] not in answered,'successful answer repeated';z=c.parse(job,tr);assert z.get('model_returned')==c.MODEL
   answered[job['request_id']]=dict(job=job,parsed=z,transport=tr,request_source=a['request_source'],receipt_source=a['receipt_source'])
 return attempts,answered
def verify():
 f=c.read(c.OUT/'freeze.json');assert f['status']=='FROZEN_BEFORE_078_API' and f['cap_cny']==c.CAP and f['model']==c.MODEL
 for p,h in f['source_sha256'].items():assert c.sha(c.ROOT/p)==h,p
 for p,h in f['artifact_sha256'].items():assert c.sha(c.OUT/p)==h,p
 return f
def run(workers=8):
 assert 1<=workers<=8;verify();jobs=c.lines(c.OUT/'main_jobs.jsonl');assert len({j['request_id'] for j in jobs})==len(jobs)
 attempts,answers=state();history=defaultdict(list)
 for a in attempts:history[a['request_id']].append(a)
 queue=deque()
 for j in jobs:
  assert c.digest(j['body'])==j['body_sha256']
  if j['request_id'] in answers:continue
  past=sorted(history[j['request_id']],key=lambda x:x['attempt_no'])
  if past:
   assert len(past)<MAX_ATTEMPTS,'attempts exhausted'
   assert past[-1]['http_status'] in RETRYABLE or past[-1]['http_status'] is None,'unrecoverable previous response'
  queue.append((j,len(past)+1,0.))
 cfg=load_config(c.ROOT/'.env.aliyun');assert '.cn-beijing.' in cfg.base_url or cfg.base_url.startswith('https://dashscope.aliyuncs.com/')
 cli=DirectClient(Config(cfg.api_key,cfg.base_url,c.MODEL),timeout=240)
 for j,_,_ in queue:cli.validate(j['body'])
 used=c.read(c.OUT/'authorization.json')['old_spent_cny']+sum(a['cost_cny'] for a in attempts);inflight=0.;running={};done=0;stop=None;limit=workers;failstreak=0;goodstreak=0;last_print=time.monotonic();lock=c.OUT/'run.lock'
 fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 try:
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
   while queue or running:
    for _ in range(len(queue)):
     if stop or len(running)>=limit:break
     job,num,ready=queue.popleft()
     if ready>time.monotonic():queue.append((job,num,ready));continue
     res=c.bound(job['body'])
     if used+inflight+res>c.CAP+1e-10:
      queue.appendleft((job,num,ready))
      if not running:stop='task_budget_cap'
      break
     aid=job['request_id']+f'__try{num}';dst=c.OUT/'attempts'/c.digest(aid)[:24];dst.mkdir(parents=True,exist_ok=False)
     c.put(dst/'request.json',dict(created_utc=c.now(),job=job,attempt_id=aid,attempt_no=num,reservation_cny=res,prior_used_and_inflight_cny=used+inflight,cap_cny=c.CAP,price_source='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash'))
     inflight+=res;running[pool.submit(cli.send,job['body'])]=(job,num,dst,res)
    if not running:
     if stop:break
     if queue:time.sleep(.25)
     continue
    ready,_=concurrent.futures.wait(running,timeout=5,return_when=concurrent.futures.FIRST_COMPLETED)
    for future in ready:
     job,num,dst,res=running.pop(future);inflight-=res
     try:tr=future.result()
     except Exception as exc:tr=dict(http_status=0,body_text='',outcome_unknown=True,transport_diagnostic=dict(exception_type=type(exc).__name__),started_utc=None,ended_utc=c.now(),headers={})
     c.put(dst/'receipt.json',dict(request_sha256=c.sha(dst/'request.json'),transport=tr));used+=c.charge(tr,res);done+=1;status=tr.get('http_status')
     if status==200:
      z=c.parse(job,tr)
      if z.get('model_returned')!=c.MODEL:stop='unexpected_model'
      failstreak=0;goodstreak+=1
      if goodstreak>=6:limit=min(workers,limit+1);goodstreak=0
     elif status in RETRYABLE and num<MAX_ATTEMPTS:
      failstreak+=1;goodstreak=0
      if failstreak>=2:limit=1
      queue.append((job,num+1,time.monotonic()+(2 if num==1 else 8)))
     else:stop='nonrecoverable_or_attempts_exhausted'
     if status!=200:print(c.canon(dict(event='transport_recovery',http_status=status,attempt=num,arm=job['arm'],used_reserved_cny=round(used+inflight,6),stop=stop)),flush=True)
    if done%20==0 and ready or time.monotonic()-last_print>25:
     print(c.canon(dict(new_attempts=done,remaining=len(queue)+len(running),in_flight=len(running),used_and_inflight_cny=round(used+inflight,6),workers=limit,stop=stop)),flush=True);last_print=time.monotonic()
  summary=dict(created_utc=c.now(),planned=len(jobs),previous_answered=len(answers),new_attempts=done,remaining_queue=len(queue),used_or_reserved_cny=used,cap_cny=c.CAP,stop_reason=stop)
  c.put(c.OUT/f'execution_{len(attempts)+done:04}.json',summary);print(c.canon(summary),flush=True)
 finally:lock.unlink(missing_ok=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);a=p.parse_args();run(a.workers)
