from pathlib import Path
from collections import Counter,deque
import concurrent.futures,json,os,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/067_conservative_evidence_packing"))
import common067 as c
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config

def state():
    attempts=[];term={};base=c.OUT/"attempts"
    if not base.exists():return attempts,term
    for p in sorted(base.glob("*/request.json")):
        rq=c.read(p);j=rq["job"];rp=p.parent/"receipt.json";tr=None
        if rp.exists():tr=c.read(rp)["transport"]
        amount=c.charge(j,tr) if tr else float(rq["reservation_cny"])
        attempts.append(dict(request_id=j["request_id"],stage=rq["stage"],cost=amount,
                             http_status=tr.get("http_status") if tr else None,path=str(p.relative_to(ROOT))))
        if tr and tr.get("http_status")==200:
            c.require(j["request_id"] not in term,"duplicate HTTP200")
            term[j["request_id"]]=dict(job=j,transport=tr,parsed=c.parse(j,tr))
    return attempts,term
def run(stage,workers=6):
    jobs=c.lines(c.OUT/f"{stage}_jobs.jsonl")
    attempts,term=state();used=sum(x["cost"] for x in attempts)
    counts=Counter(x["request_id"] for x in attempts);pending=[]
    for j in jobs:
        if j["request_id"] in term:continue
        if counts[j["request_id"]]:raise RuntimeError("unresolved prior "+j["request_id"])
        pending.append(j)
    cfg=load_config(ROOT/".env.aliyun")
    clients={k:DirectClient(Config(cfg.api_key,cfg.base_url,m),timeout=180) for k,m in c.MODELS.items()}
    for j in pending:
        c.require(j["body"]["model"]==c.MODELS[j["model_key"]],"model mismatch")
        clients[j["model_key"]].validate(j["body"])
    lock=c.OUT/"live.lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    q=deque(pending);inflight={};reserved=0.;done=0
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while q or inflight:
                while q and len(inflight)<workers:
                    j=q.popleft();res=c.bound(j)
                    if used+reserved+res>c.CAP:raise RuntimeError("067 budget cap")
                    num=counts[j["request_id"]]+1;dst=c.OUT/"attempts"/f"{c.digest(j['request_id'])[:24]}_{num:02}"
                    c.require(not dst.exists(),"attempt collision");dst.mkdir(parents=True)
                    c.put(dst/"request.json",dict(created_utc=c.now(),stage=stage,job=j,attempt=num,
                          reservation_cny=res,prior_used_reserved=used+reserved,cap_cny=c.CAP,
                          body_sha256=c.digest(j["body"])))
                    counts[j["request_id"]]+=1;reserved+=res
                    f=pool.submit(clients[j["model_key"]].send,j["body"]);inflight[f]=(j,dst,res)
                ready,_=concurrent.futures.wait(inflight,timeout=10,
                    return_when=concurrent.futures.FIRST_COMPLETED)
                for f in ready:
                    j,dst,res=inflight.pop(f);reserved-=res
                    try:tr=f.result()
                    except Exception as e:tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,exception_type=type(e).__name__)
                    c.put(dst/"receipt.json",dict(request_sha256=c.sha(dst/"request.json"),transport=tr))
                    used+=c.charge(j,tr);done+=1
                    if tr.get("http_status")!=200:raise RuntimeError("non200 "+str(tr.get("http_status")))
                    if done%20==0:print(stage,done,"remaining",len(q)+len(inflight),"used",round(used,4),flush=True)
        c.put(c.OUT/f"{stage}_execution.json",dict(completed_utc=c.now(),stage=stage,
              planned=len(jobs),completed_now=done,cumulative_cost_cny=used))
        print("COMPLETE",stage,len(jobs),"cost",round(used,6),flush=True)
    finally:
        if lock.exists():lock.unlink()
if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("stage");ap.add_argument("--workers",type=int,default=6)
    a=ap.parse_args();run(a.stage,a.workers)
