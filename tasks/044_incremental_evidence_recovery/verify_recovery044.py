"""Offline recovery verification for 044. Not an independent scientific audit."""
from pathlib import Path
import json,hashlib
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/044_incremental_evidence_recovery"
RES=OUT/"results_recovery_001"

def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")

def main():
    checks={}
    ef=read(OUT/"eval_score/freeze.json");mf=read(OUT/"model/freeze.json");pf=read(OUT/"planning_001/freeze.json")
    assert sha(OUT/"eval_score/jobs.jsonl")==ef["jobs_sha"]
    assert sha(OUT/"eval_score/mapping.jsonl")==ef["mapping_sha"]
    assert sha(OUT/"model/final.json")==mf["model_sha"]
    assert sha(OUT/"model/eval_choices.jsonl")==mf["choices_sha"]
    assert sha(OUT/"eval_score/jobs.jsonl")==mf["jobs_sha"]
    checks["frozen_model_choices_and_eval_jobs_intact"]=True

    source_expected=dict(pf.get("code_at_freeze",{}));source_expected.update(mf["source_code"])
    source_drift={}
    for rel,h in source_expected.items():
        p=ROOT/rel
        source_drift[rel]=dict(expected=h,current=sha(p) if p.exists() else None,match=p.exists() and sha(p)==h)
    drift=[k for k,v in source_drift.items() if not v["match"]]
    checks["current_source_drift"]=drift
    changed_inputs=[]
    for rel,h in pf.get("sources",{}).items():
        p=ROOT/rel
        if not p.exists() or sha(p)!=h:changed_inputs.append(rel)
    assert not changed_inputs
    checks["frozen_source_inputs_unchanged"]=True

    groups=read(ROOT/"outputs/003_error_analysis/patient_groups.json")["groups"]
    dev=set(map(str,groups["development"]));res=set(map(str,groups["reserved_test"]))
    train=set(map(str,pf["train_patients"]));ev=set(map(str,pf["eval_patients"]))
    assert train.isdisjoint(ev) and (train|ev)<=dev and not ((train|ev)&res)
    checks["patient_isolation"]=dict(train=len(train),evaluation=len(ev),reserved_overlap=0)
    cov=read(RES/"coverage.json");summary=read(RES/"summary.json")
    assert cov["planned_claims"]==696 and cov["common_valid_claims"]==687
    assert cov["unknown_request_count"]==8 and cov["parser_status"].get("invalid_core_fields")==1
    choices=lines(OUT/"model/eval_choices.jsonl");cc=Counter(x["choice"] for x in choices)
    assert cc==Counter({"base":693,"time":3})
    checks["evaluation_coverage"]=dict(planned=696,common_valid=687,unknown_no_receipt=8,invalid_core=1,choices=dict(cc))

    p={(x["baseline"],x["candidate"],x["label"]):x for x in summary["paired"]}
    for lab in ("Score","U0","U2"):
        x=p[("base","learned",lab)]
        assert x["rescued"]==1 and x["harmed"]==0 and x["net_correct"]==1 and x["false_S_delta"]==0
    assert p[("base","rank","Score")]["net_correct"]==-1
    assert p[("base","rank","U2")]["net_correct"]==-6
    checks["paired_recount"]=dict(learned_net={lab:p[("base","learned",lab)]["net_correct"] for lab in ("Score","U0","U2")},
      rank_score_net=-1,rank_U2_net=-6)

    aud=read(OUT/"eval_audit_recovery_001/summary.json")
    assert aud["jobs"]==6 and aud["valid"]==6
    aid="c5a88f4d-8474-f70b-50bf-8e79480bd7ce"
    ar={(x["id"],x["condition"]):x for x in aud["results"]}
    assert not ar[(aid,"base")]["joint_pass"] and ar[(aid,"learned")]["joint_pass"]
    checks["changed_claim_reason_audit"]=dict(valid=6,joint_pass=aud["joint_pass"],
      rescue_base_joint=False,rescue_learned_joint=True)
    unknown_reserve=0.
    for rid in cov["unknown_request_ids"]:
        prefix=hashlib.sha256(json.dumps(rid,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:24]
        p=OUT/"attempts"/f"{prefix}_01"/"request.json"
        if p.exists():unknown_reserve+=float(read(p)["reservation_cny"])
    train_cumulative=float(read(OUT/"train_audit/execution_001.json")["used_cny"])
    eval_received=float(summary["eval_score_received_cost_cny"])
    audit_cost=float(aud["cost_cny"])
    total=train_cumulative+eval_received+unknown_reserve+audit_cost
    assert total<80
    checks["cost"]=dict(train_through_audit_cny=train_cumulative,eval_score_received_cny=eval_received,
      unknown_reservation_cny=unknown_reserve,eval_reason_audit_cny=audit_cost,total_used_or_reserved_cny=total,cap_cny=80)

    status="pass_with_provenance_warning" if drift else "pass"
    result=dict(status=status,checked_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      independent_audit=False,checks=checks,
      interpretation="Frozen model/choices/jobs and numerical replay verified. Current source differs from source hashes captured at model freeze; do not claim full source-level reproducibility until restored.")
    put(OUT/"verification_recovery_001.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
