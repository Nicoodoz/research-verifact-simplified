"""053 append-only Alibaba runner. No success-content retries."""
from pathlib import Path
from collections import Counter,deque
import concurrent.futures,json,os,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"))
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import common053 as c
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config

def parse(job,tr):
    if tr.get("http_status")!=200:return {"status":"invalid","errors":["no_http200"]}
    return c.parse_response(tr,job["scored"],job["thinking"])

def state():
    attempts=[];terminal={}
    base=c.OUT/"attempts"
    if not base.exists():return attempts,terminal
    for p in sorted(base.glob("*/request.json")):
        rq=c.read(p);job=rq["job"];rp=p.parent/"receipt.json";tr=None
        if rp.exists():
            rec=c.read(rp);c.require(rec["request_sha256"]==c.sha(p),"receipt binding");tr=rec["transport"]
        amount=c.actual_charge(job,tr) if tr else float(rq["reservation_cny"])
        attempts.append(dict(request_id=job["request_id"],stage=rq["stage"],cost=amount,
          http_status=tr.get("http_status") if tr else None,path=str(p.relative_to(ROOT))))
        if tr and tr.get("http_status")==200:
            c.require(job["request_id"] not in terminal,"duplicate HTTP200")
            terminal[job["request_id"]]=dict(job=job,transport=tr,parsed=parse(job,tr))
    return attempts,terminal

def run(stage,workers=6):
    jobs=c.lines(c.OUT/f"{stage}_jobs.jsonl");attempts,terminal=state();used=sum(x["cost"] for x in attempts)
    counts=Counter(x["request_id"] for x in attempts);pending=[]
    for j in jobs:
        if j["request_id"] in terminal:continue
        if counts[j["request_id"]]:raise RuntimeError("unresolved prior request "+j["request_id"])
        pending.append(j)
    cfg=load_config(ROOT/".env.aliyun")
    clients={m:DirectClient(Config(cfg.api_key,cfg.base_url,m),timeout=240) for m in (c.MODEL_DS,c.MODEL_Q)}
    for j in pending:clients[j["body"]["model"]].validate(j["body"])
    lock=c.OUT/"live.lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    q=deque(pending);inflight={};reserved=0.;done=0
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while q or inflight:
                while q and len(inflight)<workers:
                    j=q.popleft();res=c.reservation(j)
                    if used+reserved+res>c.CAP:
                        raise RuntimeError(f"053 cap before send used={used:.4f} reserved={reserved:.4f} next={res:.4f}")
                    num=counts[j["request_id"]]+1;dst=c.OUT/"attempts"/f"{c.digest(j['request_id'])[:24]}_{num:02}"
                    c.require(not dst.exists(),"attempt collision");dst.mkdir(parents=True)
                    c.put(dst/"request.json",dict(created_utc=c.now(),stage=stage,job=j,attempt=num,
                      reservation_cny=res,prior_used_reserved_cny=used+reserved,cap_cny=c.CAP,body_sha256=c.digest(j["body"])))
                    counts[j["request_id"]]+=1;reserved+=res
                    fut=pool.submit(clients[j["body"]["model"]].send,j["body"]);inflight[fut]=(j,dst,res)
                ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in ready:
                    j,dst,res=inflight.pop(fut);reserved-=res
                    try:tr=fut.result()
                    except Exception as e:tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,exception_type=type(e).__name__)
                    c.put(dst/"receipt.json",dict(request_sha256=c.sha(dst/"request.json"),transport=tr))
                    used+=c.actual_charge(j,tr);done+=1
                    if tr.get("http_status")!=200:raise RuntimeError("non200 "+str(tr.get("http_status")))
                    native=json.loads(tr["body_text"])
                    if native.get("model")!=j["body"]["model"]:raise RuntimeError("returned model mismatch")
                    if done%40==0:print(stage,done,"remaining",len(q)+len(inflight),"used",round(used,4),flush=True)
        c.put(c.OUT/f"{stage}_execution.json",dict(completed_utc=c.now(),stage=stage,planned=len(jobs),completed_now=done,cumulative_cost_cny=used))
        print("COMPLETE",stage,len(jobs),"cost",round(used,6),flush=True)
    finally:
        if lock.exists():lock.unlink()

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("stage");ap.add_argument("--workers",type=int,default=6)
    a=ap.parse_args();run(a.stage,a.workers)
