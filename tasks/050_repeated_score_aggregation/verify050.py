"""Offline verification for 050 stopped screen."""
from pathlib import Path
from collections import defaultdict
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/050_repeated_score_aggregation"))
import common050 as c
import run050

def main():
    checks=[]
    def ck(name,ok,detail=None):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
        if not ok:raise RuntimeError(name)
    freeze=c.read(c.OUT/"freeze.json")
    screen=c.lines(c.OUT/"screen_cases.jsonl");confirm=c.lines(c.OUT/"confirmation_cases_frozen.jsonl")
    ck("sizes",len(screen)==32 and len(confirm)==58)
    sp=set(freeze["screen_patients"]);cp=set(freeze["confirmation_patients"])
    ck("patient_disjoint",not(sp&cp))
    ck("screen_membership",all(x["sid"] in sp for x in screen))
    ck("confirm_membership",all(x["sid"] in cp for x in confirm))
    ck("case_disjoint",not({x["id"] for x in screen}&{x["id"] for x in confirm}))
    jobs=c.lines(c.OUT/"screen_score_jobs.jsonl")
    ck("job_count",len(jobs)==192)
    by=defaultdict(set)
    for j in jobs:
        by[j["id"]].add(c.digest(j["body"]))
        payload=json.loads(j["body"]["messages"][-1]["content"])
        ck("payload_keys_"+j["request_id"],set(payload)=={"proposition","reference"})
    ck("six_rounds_each",all(sum(j["id"]==pid for j in jobs)==6 for pid in by))
    ck("identical_body_each",all(len(v)==1 for v in by.values()))
    attempts,term=run050.state()
    ck("attempt_count",len(attempts)==192)
    ck("all_http200",all(a["http_status"]==200 for a in attempts))
    ck("screen_budget",sum(a["cost"] for a in attempts)<=c.SCREEN_CAP)
    ck("no_confirmation",not any(a["stage"].startswith("confirmation") for a in attempts))
    analysis=c.read(c.OUT/"screen_analysis.json")
    ck("no_promoted",analysis["promoted"]==[])
    result=dict(created_utc=c.now(),status="PASS",checks=checks,cost_cny=sum(a["cost"] for a in attempts),
      code_sha256={p.name:c.sha(p) for p in [
        ROOT/"tasks/050_repeated_score_aggregation/protocol.md",
        ROOT/"tasks/050_repeated_score_aggregation/common050.py",
        ROOT/"tasks/050_repeated_score_aggregation/run050.py",
        ROOT/"tasks/050_repeated_score_aggregation/prepare050.py",
        ROOT/"tasks/050_repeated_score_aggregation/analyze_screen050.py"]})
    c.put(c.OUT/"verification_001.json",result)
    print(json.dumps(dict(status="PASS",checks=len(checks),cost_cny=result["cost_cny"]),indent=2))

if __name__=="__main__":main()
