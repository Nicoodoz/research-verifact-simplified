"""Read-only verification of 038 audit execution and analysis."""
import json
from collections import Counter
from pathlib import Path
import common038 as c
import execute038 as ex

PLAN=c.OUT/"planning_001"; ANA=c.OUT/"analysis_001"

def main():
    checks={}
    pre=c.read(PLAN/"preflight.json")
    for rel,h in pre["source_sha256"].items():
        c.require(c.file_hash(c.ROOT/rel)==h,"036 source changed: "+rel)
    checks["036_sources_unchanged"]=True

    blind=c.csvread(PLAN/"blind_cohort.csv")
    key=c.csvread(PLAN/"evaluation_key.csv")
    c.require(len(blind)==len(key)==462 and len({r["id"] for r in blind})==462,"blind cohort")
    c.require(sum(r["audit_group"]=="U0_to_U2_S" for r in blind)==342,"flip count")
    groups=Counter(r["audit_group"] for r in blind)
    c.require(groups["control_Supported"]==40 and groups["control_Not_Supported"]==40 and groups["control_Not_Addressed"]==40,"control counts")
    ft=Counter(r["flip_type"] for r in key)
    c.require(ft["R"]==219 and ft["H"]==42 and ft["W"]==81,"RHW counts")
    checks["cohort_and_RHW"]=dict(groups=groups,RHW={k:ft[k] for k in ("R","H","W")})
    jobs=c.jsonl(PLAN/"jobs.jsonl")
    attempts,terminal=ex.state()
    c.require(len(terminal)==len(jobs)==1270,"terminal coverage")
    for j in jobs:
        t=terminal[j["request_id"]]
        c.require(t["job"]==j,"job identity")
        if j["kind"]=="evidence":
            payload=json.loads(j["body"]["messages"][1]["content"])
            c.require(set(payload)=={"proposition","reference"},"blind evidence keys")
            txt=j["body"]["messages"][1]["content"]
            c.require("human_gt" not in txt and '\"GT\"' not in txt and '\"U2\"' not in txt and '\"reason\"' not in txt,"evidence leakage")
    statuses=Counter((j["kind"],j["model_key"],terminal[j["request_id"]]["parsed"]["status"]) for j in jobs)
    c.require(statuses[("reason","qwen","valid")]==346,"reason audit validity")
    c.require(statuses[("evidence","qwen","valid")]==451 and statuses[("evidence","qwen","invalid")]==11,"qwen evidence coverage")
    c.require(statuses[("evidence","deepseek","valid")]==440 and statuses[("evidence","deepseek","invalid")]==22,"deepseek evidence coverage")
    checks["job_coverage_and_blinding"]={str(k):v for k,v in statuses.items()}

    normalized=c.csvread(ANA/"normalized.csv")
    cases=c.csvread(ANA/"evidence_cases.csv")
    reasons=c.csvread(ANA/"reason_alignment.csv")
    c.require(len(normalized)==1270 and len(cases)==462 and len(reasons)==346,"analysis row counts")
    c.require(all(r["qwen_trace_supported"]!="True" or r["qwen_citation_valid"]=="True" for r in cases),"qwen trace quote validation")
    c.require(all(r["deepseek_trace_supported"]!="True" or r["deepseek_citation_valid"]=="True" for r in cases),"deepseek trace quote validation")
    checks["analysis_counts_and_trace_quote_validation"]=True
    # Reparse all raw receipts and compare the critical fields stored in normalized output.
    byrid={r["request_id"]:r for r in normalized}
    max_mismatch=0
    for rid,t in terminal.items():
        p=t["parsed"]; r=byrid[rid]
        for field in ("status","audit_label","coverage","alignment"):
            a=p.get(field); b=r.get(field) or None
            if isinstance(a,bool): b=(str(b).lower()=="true")
            if a!=b: max_mismatch+=1
    c.require(max_mismatch==0,"normalized replay mismatch")
    checks["receipt_reparse_exact"]=True

    cost=c.read(ANA/"cost.json")
    c.require(cost["used_cny"]<=c.CAP and cost["terminal"]==1270,"cost/cap")
    checks["cost_cap"]=cost

    result=dict(status="pass",checked_utc=c.now(),checks=checks,n_checks=len(checks),
                independent_audit=False,API_calls=len(attempts),reserved_used_for_posthoc_audit=True,
                reserved_used_for_method_selection=False)
    (c.OUT/"verification_001.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("038 verification PASS",len(checks),"checks")

if __name__=="__main__":
    main()
