"""Execute frozen 038 audit jobs through Aliyun; immutable HTTP200; budget-capped."""
import argparse, concurrent.futures, json, os
from collections import Counter, deque
from pathlib import Path
import common038 as c

PLAN = c.OUT / "planning_001"
ATT = c.OUT / "attempts"

def load_jobs():
    jobs = c.jsonl(PLAN / "jobs.jsonl")
    return jobs

def state():
    attempts=[]; terminal={}
    if not ATT.exists(): return attempts, terminal
    for p in sorted(ATT.glob("*/request.json")):
        req=c.read(p); job=req["job"]; rp=p.parent/"receipt.json"
        tr=None; amount=req["reservation_cny"]; basis="unresolved_request_reservation"
        if rp.exists():
            rec=c.read(rp); c.require(rec["request_sha256"]==c.file_hash(p),"receipt binding")
            tr=rec["transport"]; amount,basis=c.charge(job,tr)
            if tr.get("http_status")==200:
                c.require(job["request_id"] not in terminal,"duplicate HTTP200")
                terminal[job["request_id"]]=dict(job=job,parsed=c.parse_job(job,tr),transport=tr,receipt=str(rp.relative_to(c.ROOT)))
        attempts.append(dict(request_id=job["request_id"],charge_cny=amount,charge_basis=basis,
                             http_status=tr.get("http_status",0) if tr else 0,path=str(p.relative_to(c.ROOT)),job=job))
    return attempts,terminal
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--limit",type=int); ap.add_argument("--workers",type=int,default=10)
    args=ap.parse_args()
    jobs=load_jobs(); attempts,terminal=state(); counts=Counter(a["request_id"] for a in attempts)
    used=sum(a["charge_cny"] for a in attempts)
    pending=[j for j in jobs if j["request_id"] not in terminal and counts[j["request_id"]]<2]
    if args.limit is not None: pending=pending[:args.limit]
    remain_bound=sum(c.bound(j) for j in pending)
    c.require(used+remain_bound<=c.CAP+1e-9,f"budget bound {used+remain_bound:.3f}>{c.CAP}")
    clients={k:c.transport_client(v) for k,v in c.MODELS.items()}
    for j in pending: clients[j["model_key"]].validate(j["body"])
    ATT.mkdir(exist_ok=True)
    queue=deque(pending); inflight={}; reserved=0.; done=0
    lock=c.OUT/"live.lock"; fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.write(fd,str(os.getpid()).encode()); os.close(fd)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            while queue or inflight:
                while queue and len(inflight)<args.workers:
                    j=queue.popleft(); reserve=c.bound(j)
                    c.require(used+reserved+reserve<=c.CAP+1e-9,"budget cap before send")
                    num=counts[j["request_id"]]+1
                    dest=ATT/f"{c.digest(j['request_id'])[:24]}_{num:02}"
                    c.require(not dest.exists(),"attempt collision")
                    c.put(dest/"request.json",dict(created_utc=c.now(),job=j,attempt=num,
                        body_sha256=c.digest(j["body"]),reservation_cny=reserve,
                        prior_used_or_reserved_cny=used+reserved,cap_cny=c.CAP))
                    counts[j["request_id"]]+=1; reserved+=reserve
                    fut=pool.submit(clients[j["model_key"]].send,j["body"])
                    inflight[fut]=(j,dest,reserve)
                if not inflight: break
                ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in ready:
                    j,dest,reserve=inflight.pop(fut); reserved-=reserve
                    try: tr=fut.result()
                    except Exception as exc:
                        tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,
                                started_utc=c.now(),ended_utc=c.now(),exception_type=type(exc).__name__)
                    c.put(dest/"receipt.json",dict(request_sha256=c.file_hash(dest/"request.json"),transport=tr))
                    amount,basis=c.charge(j,tr); used+=amount; done+=1
                    parsed=c.parse_job(j,tr) if tr.get("http_status")==200 else dict(status="no_http200")
                    if done<=5 or done%50==0:
                        print("done",done,"kind",j["kind"],"model",j["model_key"],"http",tr.get("http_status"),
                              "parse",parsed.get("status"),"used",round(used,4),flush=True)
                    status=dict(state="running",completed_this_call=done,pending=len(queue),inflight=len(inflight),used_cny=used,inflight_reserved_cny=reserved,updated_utc=c.now())
                    (c.OUT/"execution_status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        c.put(c.OUT/f"execution_summary_{1+len(list(c.OUT.glob('execution_summary_*.json'))):03}.json",
              dict(created_utc=c.now(),completed_now=done,total_terminal_before=len(terminal),
                   planned_this_call=len(pending),used_cny=used,cap_cny=c.CAP))
        print("038 execution call complete",done,"used CNY",round(used,6))
    finally:
        if lock.exists(): lock.unlink()

if __name__=="__main__":
    main()
