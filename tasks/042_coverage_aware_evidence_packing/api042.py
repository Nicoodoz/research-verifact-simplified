"""042 chat-only Alibaba runner with immutable receipts and one task budget."""
import concurrent.futures,json,os,time
from collections import Counter,deque
import common042 as c
from verifact_research.inference.aliyun import Config,load_config

def state():
    attempts=[];terminal={}
    base=c.OUT/"attempts"
    if not base.exists():return attempts,terminal
    for p in sorted(base.glob("*/request.json")):
        rq=c.read(p);job=rq["job"];rp=p.parent/"receipt.json";tr=None
        amount=rq["reservation_cny"];basis="unresolved_request_reservation"
        c.require(rq["body_sha256"]==c.body_hash(job["body"]),"request body hash")
        if rp.exists():
            rec=c.read(rp);c.require(rec["request_sha256"]==c.sha(p),"receipt binding")
            tr=rec["transport"];amount,basis=c.charge(job,tr)
            if tr.get("http_status")==200:
                c.require(job["request_id"] not in terminal,"duplicate HTTP200")
                terminal[job["request_id"]]=dict(job=job,parsed=c.parse_score(tr),transport=tr,receipt=str(rp.relative_to(c.ROOT)))
        attempts.append(dict(request_id=job["request_id"],stage=rq["stage"],charge_cny=amount,
          charge_basis=basis,http_status=tr.get("http_status") if tr else None,path=str(p.relative_to(c.ROOT))))
    return attempts,terminal
def run(jobs,stage,workers=8):
    attempts,terminal=state();used=sum(x["charge_cny"] for x in attempts)
    counts=Counter(x["request_id"] for x in attempts)
    for j in jobs:
        if j["request_id"] in terminal:c.require(terminal[j["request_id"]]["job"]==j,"existing job differs")
    pending=[j for j in jobs if j["request_id"] not in terminal and counts[j["request_id"]]<3]
    cfg=load_config(c.ROOT/".env.aliyun");client=c.DirectClient(Config(cfg.api_key,cfg.base_url,"deepseek-v4-flash-0731"),timeout=180)
    for j in pending:
        c.require(j["kind"]=="chat" and j["body"]["model"]=="deepseek-v4-flash-0731","only fixed Judge allowed")
        client.validate(j["body"])
    lock=c.OUT/"live.lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    queue=deque(pending);inflight={};reserved=0.;done=0;stop=None;bad=deque(maxlen=50)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while (queue and stop is None) or inflight:
                while queue and stop is None and len(inflight)<workers:
                    j=queue.popleft();reserve=c.bound(j)
                    if used+reserved+reserve>c.CAP:stop="task_budget45";break
                    number=counts[j["request_id"]]+1;dest=c.OUT/"attempts"/f"{c.digest(j['request_id'])[:24]}_{number:02}"
                    c.require(not dest.exists(),"attempt collision");dest.mkdir(parents=True)
                    req=dict(created_utc=c.now(),stage=stage,job=j,attempt=number,body_sha256=c.body_hash(j["body"]),
                      reservation_cny=reserve,prior_task_used_or_reserved_cny=used+reserved,cap_cny=c.CAP)
                    c.put(dest/"request.json",req);counts[j["request_id"]]+=1;reserved+=reserve
                    fut=pool.submit(client.send,j["body"]);inflight[fut]=(j,dest,reserve)
                if not inflight:break
                ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in ready:
                    j,dest,reserve=inflight.pop(fut);reserved-=reserve
                    try:tr=fut.result()
                    except Exception as exc:
                        tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,started_utc=c.now(),ended_utc=c.now(),
                                transport_diagnostic=dict(exception_type=type(exc).__name__))
                    c.put(dest/"receipt.json",dict(request_sha256=c.sha(dest/"request.json"),transport=tr))
                    amount,basis=c.charge(j,tr);used+=amount;done+=1
                    parsed=c.parse_score(tr);bad.append(tr.get("http_status")!=200 or parsed.get("status") not in c.VALID)
                    if tr.get("http_status")==200:terminal[j["request_id"]]=dict(job=j,parsed=parsed,transport=tr,receipt=str((dest/"receipt.json").relative_to(c.ROOT)))
                    elif counts[j["request_id"]]<3:queue.append(j)
                    if tr.get("http_status") in (400,401,403,404) or parsed.get("model_returned") not in (None,"deepseek-v4-flash-0731"):stop="interface_or_model_error"
                    if len(bad)>=10 and sum(bad)>=10 and sum(bad)/len(bad)>.2:stop="systemic_invalid_or_transport"
                    if amount>reserve+1e-10:stop="reservation_underestimate"
                    if done%50==0 or stop:print(stage,done,"used",round(used,4),"pending",len(queue),"stop",stop,flush=True)
        c.put(c.OUT/f"{stage}_execution_summary_{len(list(c.OUT.glob(stage+'_execution_summary_*.json')))+1:03}.json",
          dict(created_utc=c.now(),completed_now=done,terminal_for_stage=sum(j["request_id"] in terminal for j in jobs),
               planned=len(jobs),stop=stop,used_cny=used))
        if stop:raise RuntimeError(stop)
        return state()
    finally:
        if lock.exists():lock.unlink()

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("stage",choices=("screen","confirmation"));args=ap.parse_args()
    path=c.OUT/("planning_001/screen_jobs.jsonl" if args.stage=="screen" else "confirmation_001/jobs.jsonl")
    run(c.lines(path),args.stage)
