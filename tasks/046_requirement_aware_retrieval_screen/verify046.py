"""Offline executor verification for 046. Not an independent scientific audit."""
from pathlib import Path
import json,hashlib,re
from collections import Counter
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/046_requirement_aware_retrieval_screen"
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"tasks/046_requirement_aware_retrieval_screen"))
import run046
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    with Path(p).open("w",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")

def main():
    checks={};freeze=read(OUT/"freeze.json")
    for rel,h in freeze["sources"].items():assert sha(ROOT/rel)==h
    assert sha(ROOT/"tasks/046_requirement_aware_retrieval_screen/protocol.md")==freeze["protocol_sha"]
    checks["frozen_sources_and_protocol"]=True
    cohort=lines(OUT/"cohort.jsonl");assert len(cohort)==16
    assert Counter(x["type"] for x in cohort)==Counter({"retrieval_sensitive":6,"judge_error_control":2,"protection":8})
    assert max(Counter(x["sid"] for x in cohort).values())<=3
    groups=read(ROOT/"outputs/003_error_analysis/patient_groups.json")["groups"]
    assert {x["sid"] for x in cohort}<=set(map(str,groups["development"]))
    assert not ({x["sid"] for x in cohort}&set(map(str,groups["reserved_test"])))
    checks["cohort"]=dict(n=16,types=dict(Counter(x["type"] for x in cohort)),patients=len({x["sid"] for x in cohort}),reserved_overlap=0)
    attempts,term=run046.state();assert len(attempts)==118 and len(term)==118
    assert all(a["http_status"]==200 for a in attempts)
    status=Counter(v["parsed"].get("status") for v in term.values())
    assert status==Counter({"valid":117,"invalid":1})
    invalid=[(k,v["job"]["kind"]) for k,v in term.items() if v["parsed"].get("status")=="invalid"]
    assert invalid==[("046_R1_01c72aa5d4072e562d397750","selector")]
    cost=sum(a["cost"] for a in attempts);assert cost<8
    checks["api"]=dict(attempts=118,http200=118,parser_status=dict(status),invalid=invalid,cost_cny=cost,cap_cny=8,
      by_stage=dict(Counter(a["stage"] for a in attempts)),by_model=dict(Counter(a["model_key"] for a in attempts)))
    for fn in ("stage1_jobs.jsonl","stage2_jobs.jsonl","stage3_jobs.jsonl"):
        for j in lines(OUT/fn):
            payload=json.loads(j["body"]["messages"][1]["content"])
            assert "GT" not in payload and "gold_label" not in payload and "human_gt" not in payload
    checks["GT_absent_from_API_payloads"]=True

    mapping=lines(OUT/"final_mapping.jsonl");assert len(mapping)==16*6
    for m in mapping:
        assert m["added_chars"]<=1500 and len(m["selected_pids"])<=3
        if not m["reference_changed"]:assert m["request_id"] is None
    checks["append_only_budget_mapping"]=dict(logical=len(mapping),changed=sum(m["reference_changed"] for m in mapping),
      unique_final_jobs=len(lines(OUT/"stage3_jobs.jsonl")))
    ana=read(OUT/"analysis_summary.json");routes={x["route"]:x for x in ana["routes"]}
    expected={"R1":(2,1),"R2":(2,1),"R3":(2,0),"R4":(1,0),"R5":(2,1),"R6":(1,1)}
    for r,(res,harm) in expected.items():
        assert routes[r]["rescued"]==res and routes[r]["harmed"]==harm
    assert sum(x["changed"] for x in ana["repeats"])==0
    checks["route_recount"]={r:dict(rescued=routes[r]["rescued"],harmed=routes[r]["harmed"],net=routes[r]["net"],
                                           changed_reference=routes[r]["changed_reference"]) for r in expected}
    checks["baseline_repeat_changes"]=0
    assert ana["factor"]["R1_R3_label_differences"]==1 and ana["factor"]["R1_R5_label_differences"]==0
    checks["factor_R1_R3_R5"]=ana["factor"]
    # Local mechanism facts used in the report.
    co={x["id"]:x for x in cohort}
    assert "primary pulmonary process" in co["a20e9521-bb29-69e6-4018-ab88db40b81f"]["base_reference"].lower()
    ns=co["053fe90a-c0e9-2926-1c4c-a69dce45bbe6"]["base_reference"].lower()
    assert "nsurg" in ns and "neurosurgery" in ns
    harm=[x for x in ana["transitions"] if x["id"]=="c8f9016e-84f3-52a8-a830-dc03da36ea5a"]
    assert {x["route"] for x in harm}=={"R1","R2","R5","R6"}
    checks["mechanism_backcheck"]=dict(two_R1_R3_rescue_key_phrases_already_in_E0=True,
      short_window_avoided_chemotherapy_protection_harm=True)

    result=dict(status="pass",checked_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      independent_audit=False,checks=checks,
      interpretation="046 first-batch development diagnostic screen only. Cohort is intentionally enriched for historical retrieval-sensitive cases; route counts are not population accuracy estimates.")
    put(OUT/"verification_001.json",result);print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
