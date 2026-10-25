"""Receipted native API stages; fixed caps sum to 40 CNY across the entire task.

Reuses 008's official transport, conservative reservations and dated pricing.
Saved HTTP 200 answers are terminal. Transient failures retry identically at most
three times; unknown outcomes at most twice, with their old reservations retained.
Terminal missing jobs do not stop untouched jobs. No user credentials are logged.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import os
import time
import study009 as s
from verifact_research.inference.siliconflow_pool import save,require,file_hash,fingerprint,load_accounts,balance_exhausted

POLICY=dict(transient_attempts=3,unknown_attempts=2,max_total_attempts=12,retry_wait_seconds=20,
    http_200="terminal_even_if_invalid_or_truncated",missing="retain_and_continue_unsent",stage_caps=s.STAGE_CAPS)
TRANSIENT={408,429,500,502,503,504}


class StageRunner:
    def __init__(self,phase,jobs,accounts,client=None,output=None):
        require(phase in s.STAGE_CAPS,"Unknown budget stage")
        require(len({j["request_id"] for j in jobs})==len(jobs),"Duplicate requests")
        self.phase,self.jobs,self.accounts=phase,jobs,accounts
        require(output is None or client is not None,"Custom output only permitted with an injected offline client")
        self.out=Path(output) if output else s.OUT/"live"/phase
        self.client=client or s.native.HttpClient()
        for j in jobs:
            require(j["body"]["model"]=={"chat":s.CHAT_MODEL,"embedding":s.EMBED_MODEL,"rerank":s.RERANK_MODEL}[j["kind"]],"Unexpected model")
            require(not any(a.key in s.pilot.canonical(j["body"]) for a in accounts),"Credential in request body")
        self.spec=dict(phase=phase,cap_cny=s.STAGE_CAPS[phase],jobs=jobs,policy=POLICY,
            driver_sha256=file_hash(Path(__file__)),transport_sha256=file_hash(Path(s.native.__file__)),
            endpoints=s.native.ENDPOINTS,price_BGE_cny_per_million=s.native.BGE_RATE_CNY_PER_M)
        self.run_id=fingerprint(self.spec)

    def checkpoint(self):
        save(self.out/"state.json",self.state)

    def receipt_path(self,index,attempt):
        return self.out/f"receipt_{index+1:06d}_{attempt:02d}.json"

    def finish(self,index,job,receipt):
        progress=self.state["jobs"][job["request_id"]]
        require(receipt["run_id"]==self.run_id and receipt["job_sha256"]==fingerprint(job)
            and receipt["request_id"]==job["request_id"] and receipt["attempt"]==progress["attempts"],"Receipt identity mismatch")
        charge,basis=s.native.cost(job,receipt["transport"])
        self.state["used_or_reserved_cny"]=float(Decimal(str(self.state["used_or_reserved_cny"]))-Decimal(str(s.native.bound(job)))+Decimal(str(charge)))
        tr=receipt["transport"]
        if balance_exhausted(tr):
            if receipt["account"] not in self.state["exhausted_accounts"]:
                self.state["exhausted_accounts"].append(receipt["account"])
            progress["status"]="pending"
        elif tr["http_status"]==200:
            progress["status"]="received"
        elif tr.get("outcome_unknown"):
            progress["unknown_failures"]+=1
            progress["status"]="retry_wait" if progress["unknown_failures"]<POLICY["unknown_attempts"] else "failed_unknown"
        elif tr["http_status"] in TRANSIENT:
            progress["transient_failures"]+=1
            progress["status"]="retry_wait" if progress["transient_failures"]<POLICY["transient_attempts"] else "failed_service"
        else:
            progress["status"]="failed_service"
            self.state["service_configuration_pause"]=tr["http_status"]
        if progress["attempts"]>=POLICY["max_total_attempts"] and progress["status"] in {"pending","retry_wait"}:
            progress["status"]="failed_attempt_limit"
        if charge>s.native.bound(job)+1e-12:
            self.state["bound_violation"]=True
        path=self.receipt_path(index,progress["attempts"])
        progress["receipts"].append(dict(file=path.name,sha256=file_hash(path),charge_cny=charge,charge_basis=basis))
        self.checkpoint()

    def send(self,index,job,account,attempt):
        try:
            tr=self.client.send(account,job)
        except Exception:
            tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,error_kind="redacted_transport_exception")
        safe=s.pilot.canonical(tr)
        for a in self.accounts:
            safe=safe.replace(json.dumps(a.key,ensure_ascii=False)[1:-1],"[REDACTED_API_KEY]")
        return dict(run_id=self.run_id,request_id=job["request_id"],job_sha256=fingerprint(job),account=account.alias,
            attempt=attempt,transport=json.loads(safe))

    def run(self,workers=4,retry_wait=None):
        require(type(workers) is int and 1<=workers<=4,"Bad worker count")
        wait_seconds=POLICY["retry_wait_seconds"] if retry_wait is None else retry_wait
        self.out.mkdir(parents=True,exist_ok=True)
        lock=self.out/"runner.lock"
        with lock.open("x",encoding="utf-8") as f:
            f.write(str(os.getpid()))
        try:
            if (self.out/"manifest.json").exists():
                require(s.read_json(self.out/"manifest.json")==self.spec,"Frozen jobs, code or budget changed")
                self.state=s.read_json(self.out/"state.json")
            else:
                require({p.name for p in self.out.iterdir()}=={"runner.lock"},"Nonempty new stage")
                self.state=dict(run_id=self.run_id,used_or_reserved_cny=0.0,exhausted_accounts=[],
                    jobs={j["request_id"]:dict(status="pending",attempts=0,unknown_failures=0,transient_failures=0,receipts=[]) for j in self.jobs})
                save(self.out/"manifest.json",self.spec,new=True)
                self.checkpoint()
            require(not self.state.get("bound_violation"),"Cost bound violated")
            for i,j in enumerate(self.jobs):
                p=self.state["jobs"][j["request_id"]]
                for ptr in p["receipts"]:
                    require(file_hash(self.out/ptr["file"])==ptr["sha256"],"Saved receipt changed")
                if p["status"]=="in_flight":
                    path=self.receipt_path(i,p["attempts"])
                    if path.exists():
                        self.finish(i,j,s.read_json(path))
                    else:
                        # Keep the old byte reservation and record this unrecoverable outcome.
                        p["unknown_failures"]+=1
                        p["status"]="retry_wait" if p["unknown_failures"]<POLICY["unknown_attempts"] else "failed_unknown"
                        p.setdefault("unreceipted_attempts",[]).append(dict(attempt=p["attempts"],reserved_cny=s.native.bound(j)))
            self.checkpoint()
            with ThreadPoolExecutor(max_workers=workers) as pool:
                while not self.state.get("bound_violation") and not self.state.get("service_configuration_pause"):
                    retries=[p for p in self.state["jobs"].values() if p["status"]=="retry_wait"]
                    if retries:
                        time.sleep(wait_seconds)
                        for p in retries:
                            p["status"]="pending"
                        self.checkpoint()
                    pending=[(i,j) for i,j in enumerate(self.jobs) if self.state["jobs"][j["request_id"]]["status"]=="pending"]
                    if not pending:
                        break
                    account=next((a for a in self.accounts if a.alias not in self.state["exhausted_accounts"]),None)
                    if account is None:
                        break
                    batch=[]
                    for i,j in pending[:workers]:
                        reserve=Decimal(str(self.state["used_or_reserved_cny"]))+Decimal(str(s.native.bound(j)))
                        if reserve>Decimal(str(self.spec["cap_cny"])):
                            continue
                        p=self.state["jobs"][j["request_id"]]
                        p.update(status="in_flight",attempts=p["attempts"]+1,account=account.alias)
                        self.state["used_or_reserved_cny"]=float(reserve)
                        self.checkpoint()
                        batch.append((i,j,account,p["attempts"]))
                    if not batch:
                        break
                    futures={pool.submit(self.send,*v):v[:2] for v in batch}
                    for future in as_completed(futures):
                        i,j=futures[future]
                        receipt=future.result()
                        save(self.receipt_path(i,receipt["attempt"]),receipt,new=True)
                        self.finish(i,j,receipt)
                    n=sum(p["status"]=="received" for p in self.state["jobs"].values())
                    if n%20<workers:
                        print(self.phase,"received",n,"budget",round(self.state["used_or_reserved_cny"],4),flush=True)
            counts={key:sum(p["status"]==key for p in self.state["jobs"].values()) for key in sorted({p["status"] for p in self.state["jobs"].values()})}
            summary=dict(phase=self.phase,status_counts=counts,expected=len(self.jobs),used_or_reserved_cny=self.state["used_or_reserved_cny"],
                cap_cny=self.spec["cap_cny"],complete=counts.get("received",0)==len(self.jobs),service_configuration_pause=self.state.get("service_configuration_pause"),invoice_verified=False)
            save(self.out/"summary.json",summary)
            return summary
        finally:
            lock.unlink()


def execute(phase,jobfile,workers=4):
    auth=s.read_json(s.OUT/"authority_001.json")
    require(auth["stage_caps_cny"]==s.STAGE_CAPS and auth["expected_total_cny"]<=40,"Missing 009 task budget authority")
    require(auth["native_stage_sha256"]==file_hash(Path(__file__)),"Driver changed after authorization record")
    require(auth["protocol_sha256"]==file_hash(s.OUT/"execution_protocol_001.md"),"Task protocol changed")
    for name,digest in auth["immutable_source_sha256"].items():
        require(file_hash(s.ROOT/name)==digest,"Frozen implementation changed: "+name)
    require(jobfile.resolve().is_relative_to(s.OUT.resolve()),"Jobs must be frozen inside 009")
    manifest=s.check(jobfile.parent)
    for name,digest in {**manifest.get("dependencies",{}),**manifest.get("code_sha256",{})}.items():
        require(file_hash(s.ROOT/name)==digest,"Frozen stage dependency changed: "+name)
    task_lock=s.OUT/"task_api.lock"
    with task_lock.open("x",encoding="utf-8") as f:
        f.write(str(os.getpid()))
    try:
        result=StageRunner(phase,s.pilot.jsonl(jobfile),load_accounts(s.ROOT/".env.siliconflow_pool")).run(workers)
        print(s.pilot.canonical(result))
    finally:
        task_lock.unlink()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("phase",choices=list(s.STAGE_CAPS))
    p.add_argument("jobs",type=Path)
    p.add_argument("--workers",type=int,default=4)
    a=p.parse_args()
    execute(a.phase,a.jobs,a.workers)
