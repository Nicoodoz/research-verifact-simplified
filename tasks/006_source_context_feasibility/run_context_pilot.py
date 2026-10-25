"""Execute only an explicitly budget-approved frozen 006 preparation."""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import sys

import context_feasibility as cf
sys.path.insert(0,str(cf.ROOT/"src"))
from verifact_research.inference.siliconflow_pool import Runner, balance_exhausted, file_hash, fingerprint, load_accounts, require, save


def charge_for(transport,bound):
    """Dated public-price estimate; ambiguous usage retains the reservation."""
    if balance_exhausted(transport):
        return 0.0,"unanswered_balance_error"
    try:
        native=json.loads(transport["body_text"])
        usage=cf.sf.normalize_usage(native)
        require(usage["total_tokens"]==usage["input_tokens"]+usage["output_tokens"],"Inconsistent usage")
        cost=cf.sf.cost_estimate(usage,transport["ended_utc"])["cny"]
        return cost,"public_dated_price_and_provider_usage_not_invoice"
    except (ValueError,TypeError,KeyError,IndexError):
        return bound,"unknown_or_unusable_usage_reserved_bound"


class MeteredRunner(Runner):
    def __init__(self,accounts,jobs,output,budget_cny,preparation_hash,client=None):
        super().__init__(accounts,jobs,output,budget_cny,max_attempts=5,client=client)
        self.spec.update(preparation_manifest_sha256=preparation_hash,adapter_sha256=file_hash(Path(__file__)),
            billing_estimator_sha256=file_hash(Path(cf.sf.__file__)),
            pricing="SiliconFlow dated announcement effective 2026-09-01; all usage estimates are not invoices")
        self.run_id=fingerprint(self.spec)

    def _finish(self,index,job,receipt):
        super()._finish(index,job,receipt)
        # The base runner already releases known balance failures. For all other
        # attempts settle the reservation using usage, including truncated answers.
        if balance_exhausted(receipt["transport"]):
            return
        charge,basis=charge_for(receipt["transport"],job["max_cost_cny"])
        current=Decimal(str(self.state["reserved_budget_cny"]))
        settled=current-Decimal(str(job["max_cost_cny"]))+Decimal(str(charge))
        self.state["reserved_budget_cny"]=float(max(Decimal(0),settled))
        progress=self.state["jobs"][job["request_id"]]
        progress["receipts"][-1].update(estimated_charge_cny=charge,charge_basis=basis)
        self.state["budget_accounting"]="Estimated settled costs plus in-flight/unknown reservations; not actual invoice"
        if charge>job["max_cost_cny"]:
            self.halt="observed_charge_exceeded_planning_bound"
            self.state["budget_bound_violation"]=True

    def _initialize(self):
        super()._initialize()
        if self.state.get("budget_bound_violation"):
            self.halt="previous_budget_bound_violation"


def load_preparation(prep):
    manifest=json.loads((prep/"manifest.json").read_text(encoding="utf-8"))
    for name,digest in manifest["output_sha256"].items():
        require(file_hash(prep/name)==digest,"Frozen preparation changed")
    for name,digest in manifest["code_sha256"].items():
        require(file_hash(cf.ROOT/name)==digest,"Frozen preparation code changed")
    jobs=cf.pilot.jsonl(prep/"requests.jsonl")
    require(len(jobs)==192,"Unexpected request scope")
    return jobs


def execute(prep,output,authorization,workers=4,client=None,accounts=None):
    jobs=load_preparation(prep)
    approval=json.loads(authorization.read_text(encoding="utf-8"))
    require(approval.get("approved") is True and approval.get("preparation_manifest_sha256")==file_hash(prep/"manifest.json"),"No approval for this preparation")
    require(approval.get("logical_requests")==len(jobs) and approval.get("budget_cny")==8,"Approval scope/budget differs")
    require(approval.get("adapter_sha256")==file_hash(Path(__file__)),"Execution adapter differs from approved version")
    require(output.resolve().parent==cf.OUT.resolve() and output.name.startswith("run_"),"Use a dedicated 006 run directory")
    configured=accounts if accounts is not None else load_accounts(cf.ROOT/".env.siliconflow_pool")
    previous_completed=-1
    while True:
        runner=MeteredRunner(configured,jobs,output,8,file_hash(prep/"manifest.json"),client=client)
        result=runner.run(workers)
        # A conservative reservation may defer queued work while other calls
        # settle below their bounds. Resume only unsent work, under the same cap.
        if result["pause_reason"]!="budget_reservation_limit" or result["completed"]<=previous_completed:
            break
        previous_completed=result["completed"]
    result["cost_meaning"]="Public-price usage estimate plus conservative unknown reservations, not provider invoice"
    save(output/"run_summary.json",result)
    print(cf.pilot.canonical(result))
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preparation",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--authorization",type=Path,required=True)
    p.add_argument("--workers",type=int,default=4)
    a=p.parse_args()
    execute(a.preparation.resolve(),a.output.resolve(),a.authorization.resolve(),a.workers)
