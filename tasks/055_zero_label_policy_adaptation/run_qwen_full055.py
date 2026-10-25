"""055 append-only Qwen full-view runner. Target GT never enters requests."""
from pathlib import Path
from collections import Counter,deque
import concurrent.futures,json,os,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation";CAP=10.5;BOUND=.022
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"));import common053 as c
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding="utf-8-sig").splitlines() if s.strip()]
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def put(p,v):
 with Path(p).open("x",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
def state():
 attempts=[];terminal={};base=OUT/"qwen_full_attempts"
 if not base.exists():return attempts,terminal
 for p in sorted(base.glob("*/request.json")):
  rq=read(p);j=rq["job"];rp=p.parent/"receipt.json";tr=None
  if rp.exists():
   rec=read(rp);assert rec["request_sha256"]==c.sha(p);tr=rec["transport"]
  amount=c.actual_charge(j,tr) if tr else float(rq["reservation_cny"])
  attempts.append(dict(request_id=j["request_id"],cost=amount,http_status=tr.get("http_status") if tr else None,path=str(p.relative_to(ROOT))))
  if tr and tr.get("http_status")==200:
   if j["request_id"] in terminal:raise RuntimeError("duplicate HTTP200 "+j["request_id"])
   terminal[j["request_id"]]=dict(job=j,transport=tr,parsed=c.parse_response(tr,True,False))
 return attempts,terminal
def run(workers=6):
 jobs=lines(OUT/"qwen_full_jobs.jsonl");attempts,terminal=state();used=sum(x["cost"] for x in attempts);counts=Counter(x["request_id"] for x in attempts);pending=[]
 for j in jobs:
  if j["request_id"] in terminal:continue
  if counts[j["request_id"]]:raise RuntimeError("unresolved prior request "+j["request_id"])
  pending.append(j)
 cfg=load_config(ROOT/".env.aliyun");client=DirectClient(Config(cfg.api_key,cfg.base_url,c.MODEL_Q),timeout=240)
 for j in pending:client.validate(j["body"])
 lock=OUT/"qwen_full.live.lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 q=deque(pending);inflight={};reserved=0.;done=0
 try:
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
   while q or inflight:
    while q and len(inflight)<workers:
     j=q.popleft()
     if used+reserved+BOUND>CAP:raise RuntimeError(f"055 cap used={used:.4f} reserved={reserved:.4f}")
     num=counts[j["request_id"]]+1;dst=OUT/"qwen_full_attempts"/f"{c.digest(j['request_id'])[:24]}_{num:02}";dst.mkdir(parents=True)
     put(dst/"request.json",dict(created_utc=c.now(),job=j,attempt=num,reservation_cny=BOUND,prior_used_reserved_cny=used+reserved,cap_cny=CAP,body_sha256=c.digest(j["body"])))
     counts[j["request_id"]]+=1;reserved+=BOUND;fut=pool.submit(client.send,j["body"]);inflight[fut]=(j,dst)
    ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
    for fut in ready:
     j,dst=inflight.pop(fut);reserved-=BOUND
     try:tr=fut.result()
     except Exception as e:tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,exception_type=type(e).__name__)
     put(dst/"receipt.json",dict(request_sha256=c.sha(dst/"request.json"),transport=tr));used+=c.actual_charge(j,tr);done+=1
     if tr.get("http_status")!=200:raise RuntimeError("non200 "+str(tr.get("http_status")))
     native=json.loads(tr["body_text"])
     if native.get("model")!=c.MODEL_Q:raise RuntimeError("model mismatch")
     if done%40==0:print("qwen_full",done,"remaining",len(q)+len(inflight),"used",round(used,4),flush=True)
  c.put(OUT/"qwen_full_execution.json",dict(completed_utc=c.now(),planned=len(jobs),completed_now=done,cumulative_cost_cny=used))
  print("COMPLETE",len(jobs),"cost",round(used,6),flush=True)
 finally:
  if lock.exists():lock.unlink()
if __name__=="__main__":
 import argparse;ap=argparse.ArgumentParser();ap.add_argument("--workers",type=int,default=6);a=ap.parse_args();run(a.workers)
