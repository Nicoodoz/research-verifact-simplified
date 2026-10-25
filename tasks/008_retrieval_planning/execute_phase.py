"""Execute one approved, frozen native-service phase; never regenerate stored 200s."""
import argparse
import json
from pathlib import Path
import common as c
from services import NativeRunner,load_accounts,file_hash,save,require

JOB_FILES={"planner":"preparation_001/planner_jobs.jsonl","embedding_base":"preparation_001/embedding_base_jobs.jsonl",
    "embedding_plans":"plans_001/embedding_jobs.jsonl","rerank":"candidates_001/rerank_jobs.jsonl","judge":"judge_preparation_001/jobs.jsonl"}


def execute(phase,workers=3,recovery_path=None):
    auth=c.read_json(c.OUT/"authority_001.json")
    require(auth["authority"]=="user_standing_approval_estimate_leq_40_CNY" and auth["task_cap_cny"]==40 and auth["expected_total_cny"]<=40,"No task budget authority")
    require(auth["phase_caps_cny"]==c.PHASE_CAPS and sum(c.PHASE_CAPS.values())==40,"Phase allocation differs")
    require(auth["services_sha256"]==file_hash(c.TASK/"services.py") and auth["executor_sha256"]==file_hash(Path(__file__)),"Execution code changed")
    require(auth["preparation_manifest_sha256"]==file_hash(c.OUT/"preparation_001/manifest.json"),"Frozen preparation changed")
    require(auth["protocol_sha256"]==file_hash(c.OUT/"execution_protocol_001.md"),"Frozen protocol changed")
    c.check_files(c.OUT/"preparation_001")
    for name,digest in c.read_json(c.OUT/"preparation_001/manifest.json")["code_sha256"].items():
        require(file_hash(c.ROOT/name)==digest,"Frozen preparation code changed")
    if phase=="embedding_plans":
        c.check_files(c.OUT/"plans_001")
    elif phase=="rerank":
        c.check_files(c.OUT/"candidates_001")
    elif phase=="judge":
        c.check_files(c.OUT/"judge_preparation_001")
    path=c.OUT/JOB_FILES[phase]
    jobs=c.pilot.jsonl(path)
    if not jobs:
        print(c.pilot.canonical(dict(phase=phase,empty=True,reason="All texts or bodies already cached")))
        return
    out=c.OUT/"live"/phase
    recovery=c.read_json(recovery_path) if recovery_path else None
    previous=-1
    while True:
        runner=NativeRunner(jobs,out,phase,load_accounts(c.ROOT/".env.siliconflow_pool"))
        result=runner.run(workers,recovery=recovery)
        recovery=None
        if result["complete"] or result["pause_reason"] or result["received"]<=previous:
            break
        previous=result["received"]
    if recovery_path:
        target=out/("used_"+recovery_path.name)
        if not target.exists():
            save(target,c.read_json(recovery_path),new=True)
    print(c.pilot.canonical(result))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=list(c.PHASE_CAPS))
    parser.add_argument("--workers",type=int,default=3)
    parser.add_argument("--recovery",type=Path)
    a=parser.parse_args()
    execute(a.phase,a.workers,a.recovery)
