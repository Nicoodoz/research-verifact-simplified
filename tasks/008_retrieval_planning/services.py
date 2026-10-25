"""Native, receipted API phases with fixed caps summing to the task's 40 CNY limit.

No saved 200 response is regenerated. Unknown outcomes retain a conservative charge
and pause; a recovery needs a separate receipt-bound registration after inspection.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

import common as c
from verifact_research.inference.siliconflow_pool import NoRedirect, load_accounts, save, require, fingerprint, file_hash, balance_exhausted

ENDPOINTS={"chat":"https://api.siliconflow.cn/v1/chat/completions",
    "embedding":"https://api.siliconflow.cn/v1/embeddings","rerank":"https://api.siliconflow.cn/v1/rerank"}
BGE_RATE_CNY_PER_M=0.07


def bound(job):
    body=job["body"]
    if job["kind"]=="chat":
        return ((len(c.pilot.canonical(body).encode("utf-8"))+2000)*3+body["max_tokens"]*9)/1e6
    if job["kind"]=="embedding":
        size=sum(len(t.encode("utf-8"))+128 for t in body["input"])+2000
    else:
        size=sum(len(t.encode("utf-8"))+len(body["query"].encode("utf-8"))+256 for t in body["documents"])+2000
    return size*BGE_RATE_CNY_PER_M/1e6


def cost(job,transport):
    if balance_exhausted(transport):
        return 0.0,"unanswered_balance_error"
    try:
        value=json.loads(transport["body_text"])
        if job["kind"]=="chat":
            usage=c.sf.normalize_usage(value)
            require(usage["total_tokens"]==usage["input_tokens"]+usage["output_tokens"],"Bad usage")
            return c.sf.cost_estimate(usage,transport["ended_utc"])["cny"],"dated_public_price_and_provider_usage_not_invoice"
        usage=value.get("usage",{})
        counted=usage.get("prompt_tokens",usage.get("total_tokens"))
        if counted is None:
            counted=value.get("meta",{}).get("billed_units",{}).get("input_tokens")
        if counted is None:
            counted=value.get("meta",{}).get("tokens",{}).get("input_tokens")
        require(type(counted) is int and counted>0,"Missing usage")
        return counted*BGE_RATE_CNY_PER_M/1e6,"public_BGE_price_and_provider_input_usage_not_invoice"
    except (ValueError,TypeError,KeyError,IndexError):
        return bound(job),"unknown_usage_conservative_byte_reservation_not_invoice"


class HttpClient:
    def send(self,account,job):
        started=datetime.now(timezone.utc).isoformat()
        request=urllib.request.Request(ENDPOINTS[job["kind"]],data=c.pilot.canonical(job["body"]).encode("utf-8"),
            method="POST",headers={"Authorization":"Bearer "+account.key,"Content-Type":"application/json"})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=180) as response:
                status,raw,headers=response.status,response.read(),response.headers
        except urllib.error.HTTPError as e:
            status,raw,headers=e.code,e.read(),e.headers or {}
        except (OSError,urllib.error.URLError):
            return dict(http_status=0,body_text="",headers={},outcome_unknown=True,started_utc=started,ended_utc=datetime.now(timezone.utc).isoformat())
        return dict(http_status=status,body_text=raw.decode("utf-8",errors="replace"),
            headers={k.lower():v for k,v in headers.items() if k.lower() in {"retry-after","x-siliconcloud-trace-id"}},
            outcome_unknown=False,started_utc=started,ended_utc=datetime.now(timezone.utc).isoformat())


class NativeRunner:
    def __init__(self,jobs,out,phase,accounts,client=None):
        require(phase in c.PHASE_CAPS,"Unknown phase")
        require(jobs and len({j["request_id"] for j in jobs})==len(jobs),"Duplicate or empty jobs")
        for j in jobs:
            allowed={"chat":c.CHAT_MODEL,"embedding":c.EMBED_MODEL,"rerank":c.RERANK_MODEL}
            require(j["kind"] in ENDPOINTS and j["body"].get("model")==allowed[j["kind"]],"Unapproved service/model")
        self.jobs,self.out,self.phase,self.accounts=jobs,Path(out),phase,accounts
        self.client=client or HttpClient()
        self.lock=threading.Lock()
        self.halt=None
        self.spec=dict(phase=phase,cap_cny=c.PHASE_CAPS[phase],jobs=jobs,driver_sha256=file_hash(Path(__file__)),
            endpoints=ENDPOINTS,max_attempts=5,pricing=dict(BGE_cny_per_million=BGE_RATE_CNY_PER_M,chat="dated DeepSeek V4 Flash prices"))
        self.run_id=fingerprint(self.spec)

    def _save(self):
        save(self.out/"state.json",self.state)

    def _receipt(self,i,attempt):
        return self.out/f"receipt_{i+1:06d}_{attempt:02d}.json"

    def _finish(self,i,job,value):
        progress=self.state["jobs"][job["request_id"]]
        require(value["request_id"]==job["request_id"] and value["job_sha256"]==fingerprint(job)
            and value["run_id"]==self.run_id and value["attempt"]==progress["attempts"],"Receipt identity mismatch")
        charge,basis=cost(job,value["transport"])
        total=Decimal(str(self.state["used_or_reserved_cny"]))-Decimal(str(bound(job)))+Decimal(str(charge))
        self.state["used_or_reserved_cny"]=float(total)
        tr=value["transport"]
        if balance_exhausted(tr):
            if value["account"] not in self.state["exhausted_accounts"]:
                self.state["exhausted_accounts"].append(value["account"])
            progress["status"]="pending"
        elif tr["http_status"]==200:
            progress["status"]="received"
        else:
            progress["status"]="unknown" if tr.get("outcome_unknown") else "service_error"
            self.halt=progress["status"]
        if charge>bound(job)+1e-12:
            self.halt="charge_exceeds_bound"
            self.state["bound_violation"]=True
        path=self._receipt(i,progress["attempts"])
        progress["receipts"].append(dict(file=path.name,sha256=file_hash(path),charge_cny=charge,charge_basis=basis))

    def run(self,workers=3,recovery=None):
        require(type(workers) is int and 1<=workers<=4,"Invalid concurrency")
        self.out.mkdir(parents=True,exist_ok=True)
        lockfile=self.out/"runner.lock"
        with lockfile.open("x",encoding="utf-8") as f:
            f.write(str(os.getpid()))
        try:
            if (self.out/"manifest.json").exists():
                require(c.read_json(self.out/"manifest.json")==self.spec,"Phase inputs/code changed")
                self.state=c.read_json(self.out/"state.json")
            else:
                require(set(x.name for x in self.out.iterdir())=={"runner.lock"},"Output not empty")
                self.state=dict(run_id=self.run_id,used_or_reserved_cny=0.0,exhausted_accounts=[],
                    jobs={j["request_id"]:dict(status="pending",attempts=0,receipts=[]) for j in self.jobs})
                save(self.out/"manifest.json",self.spec,new=True)
            require(not self.state.get("bound_violation"),"Budget bound violation requires inspection")
            for i,j in enumerate(self.jobs):
                progress=self.state["jobs"][j["request_id"]]
                for receipt in progress["receipts"]:
                    require(file_hash(self.out/receipt["file"])==receipt["sha256"],"Stored receipt changed")
                if progress["status"]=="in_flight":
                    path=self._receipt(i,progress["attempts"])
                    if path.exists():
                        self._finish(i,j,c.read_json(path))
                    else:
                        progress["status"]="unknown"
                if progress["status"] in {"unknown","service_error"}:
                    if recovery and j["request_id"] in recovery.get("request_ids",[]):
                        require(recovery["run_id"]==self.run_id and recovery["prior_state_sha256"]==file_hash(self.out/"state.json"),"Recovery not bound to current state")
                        progress["status"]="pending"  # Past cost/unknown reservation is retained.
                        self.halt=None
                    else:
                        self.halt=progress["status"]
            unresolved=[v["status"] for v in self.state["jobs"].values() if v["status"] in {"unknown","service_error"}]
            if unresolved:
                self.halt=unresolved[0]
            self._save()
            def one(i,job):
                while True:
                    with self.lock:
                        progress=self.state["jobs"][job["request_id"]]
                        if self.halt or progress["status"]=="received" or progress["attempts"]>=5:
                            return
                        account=next((a for a in self.accounts if a.alias not in self.state["exhausted_accounts"]),None)
                        reserve=Decimal(str(self.state["used_or_reserved_cny"]))+Decimal(str(bound(job)))
                        if account is None or reserve>Decimal(str(self.spec["cap_cny"])):
                            return
                        progress.update(status="in_flight",attempts=progress["attempts"]+1,account=account.alias)
                        self.state["used_or_reserved_cny"]=float(reserve)
                        self._save()
                        attempt=progress["attempts"]
                    try:
                        tr=self.client.send(account,job)
                    except Exception:
                        tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,error_kind="redacted_transport_exception")
                    safe=c.pilot.canonical(tr)
                    for configured in self.accounts:
                        safe=safe.replace(json.dumps(configured.key,ensure_ascii=False)[1:-1],"[REDACTED_API_KEY]")
                    value=dict(run_id=self.run_id,request_id=job["request_id"],job_sha256=fingerprint(job),account=account.alias,attempt=attempt,transport=json.loads(safe))
                    with self.lock:
                        save(self._receipt(i,attempt),value,new=True)
                        self._finish(i,job,value)
                        self._save()
                        if sum(x["status"]=="received" for x in self.state["jobs"].values())%20==0:
                            print(self.phase,"received",sum(x["status"]=="received" for x in self.state["jobs"].values()),"budget",round(self.state["used_or_reserved_cny"],4),flush=True)
                        if progress["status"]!="pending":
                            return
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures=[pool.submit(one,i,j) for i,j in enumerate(self.jobs)]
                for f in futures:
                    f.result()
            result=dict(phase=self.phase,expected=len(self.jobs),received=sum(x["status"]=="received" for x in self.state["jobs"].values()),
                used_or_reserved_cny=self.state["used_or_reserved_cny"],cap_cny=self.spec["cap_cny"],pause_reason=self.halt,
                exhausted_accounts=self.state["exhausted_accounts"],invoice_verified=False)
            result["complete"]=result["received"]==result["expected"]
            save(self.out/"summary.json",result)
            return result
        finally:
            lockfile.unlink()
