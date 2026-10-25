"""Offline verification for 049 stopped screen."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/049_evidence_decision_utilization"))
import common049 as c
import run049

def main():
    checks=[]
    def ck(name,ok,detail=None):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
        if not ok:raise RuntimeError(name)
    freeze=c.read(c.OUT/"freeze.json");s2=c.read(c.OUT/"screen_stage2_freeze.json")
    cases={x["id"]:x for x in c.lines(c.OUT/"screen_cases.jsonl")}
    recs={x["id"]:x for x in c.lines(c.OUT/"screen_trigger_records.jsonl")}
    jobs1=c.lines(c.OUT/"screen_stage1_jobs.jsonl");jobs2=c.lines(c.OUT/"screen_stage2_jobs.jsonl")
    ck("screen_n",len(cases)==16)
    ck("fresh_trigger_count",sum(r["trigger"] for r in recs.values())==13)
    ck("only_trigger_method_jobs",all((j["condition"]=="B") or recs[j["id"]]["trigger"] for j in jobs1+jobs2))
    attempts,term=run049.state()
    ck("attempt_count",len(attempts)==78,len(attempts))
    ck("all_http200",all(a["http_status"]==200 for a in attempts))
    ck("screen_budget",sum(a["cost"] for a in attempts)<=c.SCREEN_CAP,sum(a["cost"] for a in attempts))
    ck("no_confirmation",not any(a["stage"].startswith("confirmation") for a in attempts))
    ck("stopped",c.read(c.OUT/"screen_decision.json")["stop"] is True)

    by={(j["id"],j["condition"]):j for j in jobs2}
    for pid,r in recs.items():
        if not r["trigger"]:continue
        e=by[(pid,"E")];cc=by[(pid,"C")];rr=by[(pid,"R")]
        ep=json.loads(e["body"]["messages"][-1]["content"])
        cp=json.loads(cc["body"]["messages"][-1]["content"])
        rp=json.loads(rr["body"]["messages"][-1]["content"])
        ck("same_reference_"+pid,ep["reference"]==cp["reference"]==rp["reference"])
        ck("same_proposition_"+pid,ep["proposition"]==cp["proposition"]==rp["proposition"])
        ck("C_index_present_"+pid,"verification_index" in cp)
        ck("R_index_present_"+pid,"verification_index" in rp)
        blob=json.dumps(cp["verification_index"],ensure_ascii=False)
        ck("C_no_relation_"+pid,"relation" not in blob)
        ck("C_no_label_leak_"+pid,all(z not in blob for z in ("audit_label","GT","U2","gold")))
        blob2=json.dumps(rp["verification_index"],ensure_ascii=False)
        ck("R_no_overall_label_leak_"+pid,all(z not in blob2 for z in ("audit_label","GT","U2","gold")))
    analysis=c.read(c.OUT/"screen_analysis.json")
    ck("no_promoted",analysis["promoted"]==[])
    result=dict(created_utc=c.now(),status="PASS",checks=checks,cost_cny=sum(a["cost"] for a in attempts),
      code_sha256={p.name:c.sha(p) for p in [
        ROOT/"tasks/049_evidence_decision_utilization/protocol.md",
        ROOT/"tasks/049_evidence_decision_utilization/common049.py",
        ROOT/"tasks/049_evidence_decision_utilization/run049.py",
        ROOT/"tasks/049_evidence_decision_utilization/build_screen_methods049.py",
        ROOT/"tasks/049_evidence_decision_utilization/analyze_screen049.py"]})
    c.put(c.OUT/"verification_001.json",result)
    print(json.dumps(dict(status="PASS",checks=len(checks),cost_cny=result["cost_cny"]),indent=2))

if __name__=="__main__":main()
