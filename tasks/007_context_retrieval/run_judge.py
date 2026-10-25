"""Metered same-Judge execution of frozen 007 inputs under the <=16 CNY policy."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import prepare as p
sys.path.insert(0,str(p.ROOT/"tasks/006_source_context_feasibility"))
from run_context_pilot import MeteredRunner, charge_for
from verifact_research.inference.siliconflow_pool import load_accounts, file_hash, fingerprint, require, save


class RetrievalRunner(MeteredRunner):
    def __init__(self,*args,terminal_unknown=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.terminal_unknown=terminal_unknown or {}
        self.spec.update(retrieval_execution_sha256=file_hash(Path(__file__)),
            unknown_policy="Pause; verify saved empty transport receipts; register them as unretried failures and resume pending work")
        self.run_id=fingerprint(self.spec)

    def _initialize(self):
        super()._initialize()
        actual={k:v for k,v in self.state["jobs"].items() if v["status"]=="unknown"}
        require(actual==self.terminal_unknown,"Unregistered unknown outcomes")
        if actual and self.halt=="unknown_previous_outcome":
            self.halt=None

    def _one(self,index,job):
        if job["request_id"] in self.terminal_unknown:
            return
        super()._one(index,job)


def load_preparation(prep):
    manifest=json.loads((prep/"manifest.json").read_text(encoding="utf-8"))
    for name,digest in manifest["output_sha256"].items():
        require(file_hash(prep/name)==digest,"Frozen input changed")
    for name,digest in manifest["code_sha256"].items():
        require(file_hash(p.ROOT/name)==digest,"Frozen preparation code changed")
    return p.pilot.jsonl(prep/"requests.jsonl")


def execute(prep,output,authorization,workers=2):
    jobs=load_preparation(prep)
    approval=json.loads(authorization.read_text(encoding="utf-8"))
    require(approval["authority"]=="user_standing_approval_task_estimate_leq_16_CNY"
        and approval["budget_cny"]==16 and approval["estimated_cny"]<=16
        and approval["preparation_manifest_sha256"]==file_hash(prep/"manifest.json")
        and approval["execution_sha256"]==file_hash(Path(__file__))
        and approval["run_directory"]==output.relative_to(p.ROOT).as_posix()
        and approval["logical_requests"]==len(jobs),"Authorization binding differs")
    require(output.parent==p.OUT and not (output/"completion.json").exists(),"Use the authorized unfinished run")
    accounts=load_accounts(p.ROOT/".env.siliconflow_pool")
    terminal={}
    if (output/"continuation.json").exists():
        terminal=json.loads((output/"continuation.json").read_text(encoding="utf-8"))["terminal_unknown"]
    previous=-1
    while True:
        runner=RetrievalRunner(accounts,jobs,output,16,file_hash(prep/"manifest.json"),terminal_unknown=terminal)
        result=runner.run(workers)
        unknown={k:v for k,v in runner.state["jobs"].items() if v["status"]=="unknown"}
        if unknown!=terminal:
            for request_id,progress in unknown.items():
                receipt=runner._read_receipt(progress["receipts"][-1])
                require(receipt["transport"]["outcome_unknown"] and not receipt["transport"]["body_text"],"Unknown transport has uninspected content")
            terminal=unknown
            record=dict(created_utc=datetime.now(timezone.utc).isoformat(),terminal_unknown=terminal,
                original_state_sha256=file_hash(output/"state.json"),no_unknown_request_retried=True)
            save(output/("continuation_%03d.json"%len(terminal)),record,new=True)
            save(output/"continuation.json",record)
            continue
        remaining=[k for k,v in runner.state["jobs"].items() if v["status"]!="response_received" and k not in terminal]
        if not remaining:
            result.update(status="completed_with_failures" if terminal else "completed",pause_reason=None)
            break
        if result["pause_reason"]!="budget_reservation_limit" or result["completed"]<=previous:
            break
        previous=result["completed"]
    result.update(unknown_failures=sorted(terminal),remaining_requests=remaining,
        estimated_settled_and_reserved_cny=runner.state["reserved_budget_cny"],invoice_verified=False)
    save(output/"completion.json" if not remaining else output/"paused.json",result,new=True)
    print(p.pilot.canonical(result))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation",type=Path,default=p.OUT/"preparation_003")
    parser.add_argument("--output",type=Path,default=p.OUT/"run_001")
    parser.add_argument("--authorization",type=Path,default=p.OUT/"authorization_001.json")
    parser.add_argument("--workers",type=int,default=2)
    a=parser.parse_args()
    execute(a.preparation.resolve(),a.output.resolve(),a.authorization.resolve(),a.workers)
