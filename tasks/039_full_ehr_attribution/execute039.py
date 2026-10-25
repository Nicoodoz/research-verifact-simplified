"""Execute frozen 039 Qwen jobs with immutable HTTP200 and task budget cap."""
import argparse, concurrent.futures, json, os
from collections import Counter,deque
from pathlib import Path
import common039 as c

ATT=c.OUT/"attempts"

def state():
    attempts=[];terminal={}
    if not ATT.exists():return attempts,terminal
    for p in sorted(ATT.glob("*/request.json")):
        req=c.read(p);j=req["job"];rp=p.parent/"receipt.json";tr=None
        amount=req["reservation_cny"];basis="unresolved_request_reservation"
        if rp.exists():
            rec=c.read(rp);c.require(rec["request_sha256"]==c.file_hash(p),"receipt binding")
            tr=rec["transport"];amount,basis=c.charge(j,tr)
            if tr.get("http_status")==200:
                c.require(j["request_id"] not in terminal,"duplicate HTTP200")
                terminal[j["request_id"]]=dict(job=j,parsed=c.parse_job(j,tr),transport=tr,receipt=str(rp.relative_to(c.ROOT)))
        attempts.append(dict(request_id=j["request_id"],charge_cny=amount,charge_basis=basis,
                             http_status=tr.get("http_status",0) if tr else 0,path=str(p.relative_to(c.ROOT)),job=j))
    return attempts,terminal
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--jobs",required=True);ap.add_argument("--workers",type=int,default=10);ap.add_argument("--limit",type=int)
    args=ap.parse_args();jobs=c.jsonl(c.ROOT/args.jobs);attempts,terminal=state()
    counts=Counter(a["request_id"] for a in attempts);used=sum(a["charge_cny"] for a in attempts)
    pending=[j for j in jobs if j["request_id"] not in terminal and counts[j["request_id"]]<2]
    if args.limit is not None:pending=pending[:args.limit]
    c.require(used+sum(c.bound(j) for j in pending)<=c.CAP+1e-9,"budget bound")
    client=c.transport_client(c.MODEL)
    for j in pending:client.validate(j["body"])
    ATT.mkdir(exist_ok=True);queue=deque(pending);inflight={};reserved=0.;done=0
    lock=c.OUT/"live.lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            while queue or inflight:
                while queue and len(inflight)<args.workers:
                    j=queue.popleft();reserve=c.bound(j);c.require(used+reserved+reserve<=c.CAP+1e-9,"cap before send")
                    n=counts[j["request_id"]]+1;dest=ATT/f"{c.digest(j['request_id'])[:24]}_{n:02}"
                    c.require(not dest.exists(),"attempt collision")
                    c.put(dest/"request.json",dict(created_utc=c.now(),job=j,attempt=n,body_sha256=c.digest(j["body"]),
                        reservation_cny=reserve,prior_used_or_reserved_cny=used+reserved,cap_cny=c.CAP))
                    counts[j["request_id"]]+=1;reserved+=reserve;inflight[pool.submit(client.send,j["body"])]=(j,dest,reserve)
                if not inflight:break
                ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in ready:
                    j,dest,reserve=inflight.pop(fut);reserved-=reserve
                    try:tr=fut.result()
                    except Exception as exc:tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,exception_type=type(exc).__name__,started_utc=c.now(),ended_utc=c.now())
                    c.put(dest/"receipt.json",dict(request_sha256=c.file_hash(dest/"request.json"),transport=tr))
                    amount,basis=c.charge(j,tr);used+=amount;done+=1
                    p=c.parse_job(j,tr) if tr.get("http_status")==200 else dict(status="no_http200")
                    if tr.get("http_status")!=200 and counts[j["request_id"]]<2:queue.append(j)
                    if done<=3 or done%50==0:print("done",done,j["kind"],tr.get("http_status"),p.get("status"),"used",round(used,4),flush=True)
                    status=dict(state="running",jobs=args.jobs,completed_this_call=done,pending=len(queue),inflight=len(inflight),used_cny=used,reserved_cny=reserved,updated_utc=c.now())
                    (c.OUT/"execution_status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        serial=1+len(list(c.OUT.glob("execution_summary_*.json")))
        c.put(c.OUT/f"execution_summary_{serial:03}.json",dict(created_utc=c.now(),jobs=args.jobs,completed_now=done,used_cny=used,cap_cny=c.CAP))
        print("039 execution complete",done,"used",round(used,6))
    finally:
        if lock.exists():lock.unlink()

if __name__=="__main__":main()
