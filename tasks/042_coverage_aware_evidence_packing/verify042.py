"""Executor verification for 042. No network calls."""
import json
from collections import Counter
import common042 as c
import api042

PLAN=c.OUT/"planning_001";AN=c.OUT/"screen_analysis_001"
R031=c.ROOT/"outputs/031_training_expansion_confirmation"

def main():
    checks={}
    freeze=c.read(PLAN/"freeze.json")
    for rel,h in freeze["source_sha256"].items():c.require(c.sha(c.ROOT/rel)==h,"frozen source changed "+rel)
    checks["source_hashes"]=True

    outputs=c.lines(PLAN/"selector_outputs.jsonl");c.require(len(outputs)==1401,"eligible output count")
    mats={r["proposition_id"]:r for r in c.lines(R031/"judge_inputs_001/materials.jsonl")}
    c.require(all(x["baseline_reference"]==mats[x["id"]]["reference"] for x in outputs),"baseline byte reproduction")
    checks["baseline_reproduced_1401"]=True
    checks["eligibility"]=Counter(x["role"] for x in outputs)

    blind=c.lines(PLAN/"screen_cohort_blind.jsonl");logical=c.lines(PLAN/"screen_logical.jsonl");jobs=c.lines(PLAN/"screen_jobs.jsonl")
    c.require(len(blind)==240 and len({x["id"] for x in blind})==240,"screen cohort")
    c.require(len(logical)==720 and Counter(x["condition"] for x in logical)==Counter({"baseline":240,"softnote":240,"covmmr":240}),"logical coverage")
    c.require(len(jobs)==537 and len({j["request_id"] for j in jobs})==537,"job dedup")
    claim={x["id"]:x["claim"] for x in blind}
    selector={x["id"]:x for x in outputs}
    refkey={"baseline":"baseline_reference","softnote":"softnote_reference","covmmr":"covmmr_reference"}
    byreq={j["request_id"]:j for j in jobs}
    for x in logical:
        job=byreq[x["request_id"]];payload=json.loads(job["body"]["messages"][1]["content"])
        c.require(set(payload)=={"proposition","reference"} and payload["proposition"]==claim[x["id"]],"request whitelist")
        c.require(payload["reference"]==selector[x["id"]][refkey[x["condition"]]],"reference binding")
        c.require(job["body"]["model"]=="deepseek-v4-flash-0731","model")
    checks["GT_blind_request_whitelist"]=True

    attempts,terminal=api042.state();c.require(len(attempts)==537 and len(terminal)==537,"API coverage")
    c.require(all(v["parsed"]["status"] in c.VALID for v in terminal.values()),"invalid response")
    c.require(all(a["http_status"]==200 for a in attempts),"non200")
    c.require(len({a["request_id"] for a in attempts})==537,"repeat HTTP200")
    used=sum(a["charge_cny"] for a in attempts);c.require(used<c.CAP,"budget")
    checks["API"]=dict(attempts=len(attempts),http200=len(terminal),statuses=dict(Counter(v["parsed"]["status"] for v in terminal.values())),cost_cny=used,cap_cny=c.CAP)
    d=c.read(AN/"decision.json");c.require(d["winner"] is None and not d["proceed_confirmation"],"stop rule")
    c.require(not (c.OUT/"confirmation_001").exists(),"confirmation must not run")
    checks["preregistered_stop_obeyed"]=True
    checks["reserved_used_for_selection"]=False
    checks["deployment_new_API_stage"]=False
    result=dict(status="pass",checked_utc=c.now(),checks=checks,n_checks=len(checks),independent_audit=False)
    c.put(c.OUT/"verification_001.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
