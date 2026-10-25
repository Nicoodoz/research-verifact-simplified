"""Analyze 039 full-EHR attribution. No API calls."""
import json
from collections import Counter,defaultdict
import common039 as c
import execute039 as ex

PLAN=c.OUT/"planning_001"
SEARCH=c.OUT/"search_001"
OUT=c.OUT/"analysis_001"
R038=c.ROOT/"outputs/038_evidence_explanation_audit"

def truth(v):return str(v).lower()=="true"

def main():
    c.require(not OUT.exists(),"analysis exists");OUT.mkdir(parents=True)
    cohort=c.csvread(PLAN/"cohort_key.csv")
    base={r["id"]:r for r in c.csvread(R038/"analysis_001/evidence_cases.csv")}
    jobs=c.jsonl(SEARCH/"audit_jobs.jsonl");attempts,terminal=ex.state()
    c.require(all(j["request_id"] in terminal for j in jobs),"audit incomplete")
    rows=[]
    for r in cohort:
        pid=r["id"];j=next(x for x in jobs if x["proposition_id"]==pid);p=terminal[j["request_id"]]["parsed"];b=base[pid]
        c48_strict=truth(b["qwen_trace_supported"])
        rels=[x["relation"] for x in p.get("requirements",[])] if p["status"]=="valid" else []
        any_relation=any(x in ("supported","contradicted") for x in rels)
        if c48_strict:cat="A_C48_sufficient"
        elif p["status"]!="valid":cat="U_invalid_audit"
        elif p["strict_supported"] and p["used_external"]:cat="B_fullEHR_search_sufficient"
        elif p["strict_supported"]:cat="A_C48_sufficient"
        elif p["audit_label"]=="Not Supported" or any_relation:cat="C_partial_or_conflicting"
        else:cat="D_no_clear_support"
        rows.append(dict(**r,attribution=cat,c48_qwen_strict=c48_strict,
          expanded_status=p["status"],expanded_label=p.get("audit_label"),expanded_coverage=p.get("coverage"),
          expanded_strict=p.get("strict_supported"),used_c48=p.get("used_c48"),used_external=p.get("used_external"),
          citations_valid=p.get("citations_valid"),summary=p.get("summary")))
    c.csvwrite(OUT/"attribution_cases.csv",rows)
    groups=[]
    for name,rr in [("all",rows),("flip_all",[x for x in rows if x["audit_group"]=="U0_to_U2_S"])]:
        groups.append(summary(name,rr))
    for ft in ("R","H","W"):
        groups.append(summary("flip_"+ft,[x for x in rows if x["flip_type"]==ft]))
    for ag in ("control_Supported","control_Not_Supported","control_Not_Addressed"):
        groups.append(summary(ag,[x for x in rows if x["audit_group"]==ag]))
    c.csvwrite(OUT/"attribution_summary.csv",groups)

    rrows=[x for x in rows if x["flip_type"]=="R"]
    counts=Counter(x["attribution"] for x in rrows)
    support=sum(counts[k] for k in ("A_C48_sufficient","B_fullEHR_search_sufficient"))
    main=dict(R_n=len(rrows),R_counts=dict(counts),R_evidence_supported=support,
      R_evidence_supported_rate=support/len(rrows),R_C48_sufficient=counts["A_C48_sufficient"],
      R_fullEHR_search_rescue=counts["B_fullEHR_search_sufficient"],
      R_partial_or_conflicting=counts["C_partial_or_conflicting"],
      R_no_clear_support=counts["D_no_clear_support"],R_invalid=counts["U_invalid_audit"])
    c.put(OUT/"key_results.json",main)
    # Compact evidence trace export for A/B cases; quotes remain tied to original receipts.
    traces=[]
    for r in rows:
        if r["attribution"] not in ("A_C48_sufficient","B_fullEHR_search_sufficient"):continue
        pid=r["id"];j=next(x for x in jobs if x["proposition_id"]==pid);p=terminal[j["request_id"]]["parsed"]
        traces.append(dict(id=pid,flip_type=r["flip_type"],GT=r["GT"],attribution=r["attribution"],
                           audit_label=p.get("audit_label"),requirements=p.get("requirements"),summary=p.get("summary")))
    with (OUT/"supported_traces.jsonl").open("x",encoding="utf-8",newline="\n") as f:
        for x in traces:f.write(json.dumps(x,ensure_ascii=False)+"\n")

    used=sum(a["charge_cny"] for a in attempts)
    c.put(OUT/"cost.json",dict(attempts=len(attempts),terminal=len(terminal),used_cny=used,cap_cny=c.CAP))
    print(json.dumps(main,ensure_ascii=False,indent=2))

def summary(name,rr):
    c.require(rr,"empty "+name);ct=Counter(x["attribution"] for x in rr);n=len(rr)
    return dict(group=name,n=n,**{k:ct[k] for k in (
      "A_C48_sufficient","B_fullEHR_search_sufficient","C_partial_or_conflicting","D_no_clear_support","U_invalid_audit")},
      evidence_supported=ct["A_C48_sufficient"]+ct["B_fullEHR_search_sufficient"],
      evidence_supported_rate=(ct["A_C48_sufficient"]+ct["B_fullEHR_search_sufficient"])/n)

if __name__=="__main__":main()
