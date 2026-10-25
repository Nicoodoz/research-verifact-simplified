"""051 append-only thinking-mode runner."""
from pathlib import Path
from collections import Counter,deque
import concurrent.futures,json,os,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/051_thinking_mode_validation"))
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import common051 as c
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
            rec=c.read(rp);c.require(rec["request_sha256"]==c.sha(p),"receipt binding")
            tr=rec["transport"]
        amount=c.charge(job,tr) if tr else float(rq["reservation_cny"])
        attempts.append(dict(request_id=job["request_id"],stage=rq["stage"],cost=amount,http_status=tr.get("http_status") if tr else None,path=str(p.relative_to(ROOT))))
        if tr and tr.get("http_status")==200:
            c.require(job["request_id"] not in terminal,"duplicate HTTP200")
            terminal[job["request_id"]]=dict(job=job,transport=tr,parsed=parse(job,tr))
    return attempts,terminal

def stage_cap(stage):
    return c.SCREEN_CAP if stage.startswith("screen") else c.TOTAL_CAP

def run(stage,workers=6):
    jobs=c.lines(c.OUT/f"{stage}_jobs.jsonl")
    attempts,terminal=state();used=sum(x["cost"] for x in attempts)
    counts=Counter(x["request_id"] for x in attempts);pending=[]
    for job in jobs:
        if job["request_id"] in terminal:continue
        if counts[job["request_id"]]:raise RuntimeError("unresolved prior request "+job["request_id"])
        pending.append(job)
    cfg=load_config(ROOT/".env.aliyun")
    client=DirectClient(Config(cfg.api_key,cfg.base_url,c.MODEL),timeout=180)
    for job in pending:
        c.require(job["body"]["model"]==c.MODEL,"model mismatch")
        client.validate(job["body"])
    lock=c.OUT/"live.lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    q=deque(pending);inflight={};reserved=0.;done=0;limit=stage_cap(stage)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while q or inflight:
                while q and len(inflight)<workers:
                    job=q.popleft();res=c.bound(job)
                    if used+reserved+res>limit or used+reserved+res>c.TOTAL_CAP:
                        raise RuntimeError("budget cap before send")
                    num=counts[job["request_id"]]+1
                    dst=c.OUT/"attempts"/f"{c.digest(job['request_id'])[:24]}_{num:02}"
                    c.require(not dst.exists(),"attempt collision");dst.mkdir(parents=True)
                    c.put(dst/"request.json",dict(created_utc=c.now(),stage=stage,job=job,attempt=num,
                      reservation_cny=res,prior_used_reserved=used+reserved,stage_cap_cny=limit,
                      total_cap_cny=c.TOTAL_CAP,body_sha256=c.digest(job["body"])))
                    counts[job["request_id"]]+=1;reserved+=res
                    fut=pool.submit(client.send,job["body"]);inflight[fut]=(job,dst,res)
                ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in ready:
                    job,dst,res=inflight.pop(fut);reserved-=res
                    try:tr=fut.result()
                    except Exception as e:tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,exception_type=type(e).__name__)
                    c.put(dst/"receipt.json",dict(request_sha256=c.sha(dst/"request.json"),transport=tr))
                    used+=c.charge(job,tr);done+=1
                    if tr.get("http_status")!=200:raise RuntimeError("non200 "+str(tr.get("http_status")))
                    native=json.loads(tr["body_text"])
                    if native.get("model")!=c.MODEL:raise RuntimeError("returned model mismatch")
                    if done%20==0:print(stage,done,"remaining",len(q)+len(inflight),"used",round(used,4),flush=True)
        c.put(c.OUT/f"{stage}_execution.json",dict(completed_utc=c.now(),stage=stage,planned=len(jobs),completed_now=done,cumulative_cost_cny=used))
        print("COMPLETE",stage,len(jobs),"cost",round(used,6),flush=True)
    finally:
        if lock.exists():lock.unlink()

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("stage");ap.add_argument("--workers",type=int,default=6)
    a=ap.parse_args();run(a.stage,a.workers)

