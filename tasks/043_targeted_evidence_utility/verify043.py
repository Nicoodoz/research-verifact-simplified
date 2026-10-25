"""Executor verification for 043. No network calls."""
import json
from collections import Counter
import common043 as c
import api043

PLAN=c.OUT/"planning_001";AUD=c.OUT/"audit_001";AN=c.OUT/"analysis_001"
R036=c.ROOT/"outputs/036_final_validation"

def main():
    checks={}
    freeze=c.read(PLAN/"freeze.json")
    for rel,h in freeze["source_sha256"].items():c.require(c.sha(c.ROOT/rel)==h,"source changed "+rel)
    checks["source_hashes"]=True
    cases=c.lines(PLAN/"cases.jsonl");c.require(len(cases)==55 and len({x["id"] for x in cases})==55,"cohort")
    mats={r["proposition_id"]:r for r in c.lines(R036/"judge_inputs_001/materials.jsonl")}
    c.require(all(x["A_reference"]==mats[x["id"]]["reference"] for x in cases),"A not original C48")
    c.require(sum(len(x["B_passage_ids"]) for x in cases)==78,"B passage count")
    c.require(all(len(x["B_passage_ids"])==len(x["C_passage_ids"]) for x in cases),"matched count")
    c.require(all(set(x["B_passage_ids"]).isdisjoint(x["C_passage_ids"]) for x in cases),"B/C overlap")
    checks["conditions"]=dict(cohort=55,B_passages=78,matched_control_count=True,no_BC_passage_overlap=True)

    jobs=c.lines(PLAN/"score_jobs.jsonl");c.require(len(jobs)==201,"score jobs")
    for j in jobs:
        payload=json.loads(j["body"]["messages"][1]["content"])
        c.require(set(payload)=={"proposition","reference"},"score whitelist")
    checks["score_input_blinding"]=True
    attempts,terminal=api043.state()
    sj=[v for v in terminal.values() if v["job"]["kind"]=="score"];aj=[v for v in terminal.values() if v["job"]["kind"]=="audit"]
    c.require(len(sj)==201 and len(aj)==164,"terminal coverage")
    c.require(all(v["transport"]["http_status"]==200 for v in terminal.values()),"non200 terminal")
    ss=Counter(v["parsed"]["status"] for v in sj);aa=Counter(v["parsed"]["status"] for v in aj)
    c.require(ss==Counter({"valid":200,"invalid_core_fields":1}),"score status drift")
    c.require(aa==Counter({"valid":162,"invalid":2}),"audit status drift")
    c.require(len(attempts)==365 and len({x["request_id"] for x in attempts})==365,"attempt coverage/repeat")
    used=sum(x["charge_cny"] for x in attempts);c.require(used<c.CAP,"budget")
    checks["API"]=dict(attempts=365,http200=365,score_status=dict(ss),audit_status=dict(aa),cost_cny=used,cap_cny=c.CAP)

    auditjobs=c.lines(AUD/"jobs.jsonl")
    for j in auditjobs:
        payload=json.loads(j["body"]["messages"][1]["content"])
        c.require(set(payload)=={"proposition","reference","answer","appended_reference_ids"},"audit whitelist")
        c.require(set(payload["answer"])=={"verdict","reason","checks"},"audit answer whitelist")
    checks["audit_input_blinding"]=True

    key=c.read(AN/"key_results.json")
    c.require(key["B_vs_A_score"]["rescue_nonS_to_S"]==13 and key["B_vs_A_score"]["harm_S_to_nonS"]==0,"B vs A recount")
    c.require(key["B_vs_C_score"]["rescue_nonS_to_S"]==14 and key["B_vs_C_score"]["harm_S_to_nonS"]==3,"B vs C recount")
    checks["key_effect_recount"]=True
    result=dict(status="pass",checked_utc=c.now(),checks=checks,n_checks=len(checks),
      independent_audit=False,reserved_posthoc_mechanism=True,reserved_used_for_method_selection=False)
    c.put(c.OUT/"verification_001.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
