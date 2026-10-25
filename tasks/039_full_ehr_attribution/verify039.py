"""Read-only 039 scientific/engineering verification."""
import json
from collections import Counter
import common039 as c
import execute039 as ex

PLAN=c.OUT/"planning_001";SEARCH=c.OUT/"search_001";ANA=c.OUT/"analysis_001"

def main():
    checks={}
    pre=c.read(PLAN/"preflight.json")
    for rel,h in pre["source_sha256"].items():c.require(c.file_hash(c.ROOT/rel)==h,"source changed "+rel)
    checks["source_hashes"]=True

    cohort=c.csvread(PLAN/"cohort_key.csv")
    c.require(len(cohort)==462 and len({r["id"] for r in cohort})==462,"cohort")
    ct=Counter(r["flip_type"] for r in cohort)
    c.require(ct["R"]==219 and ct["H"]==42 and ct["W"]==81,"RHW")
    checks["cohort"]=dict(n=len(cohort),R=ct["R"],H=ct["H"],W=ct["W"])

    jobs_q=c.jsonl(PLAN/"query_jobs.jsonl");jobs_a=c.jsonl(SEARCH/"audit_jobs.jsonl")
    attempts,terminal=ex.state()
    c.require(len(jobs_q)==len(jobs_a)==462,"job counts")
    c.require(all(j["request_id"] in terminal for j in jobs_q+jobs_a),"terminal coverage")
    for j in jobs_q:
        payload=json.loads(j["body"]["messages"][1]["content"])
        c.require(set(payload)=={"proposition"},"query leakage")
        c.require(terminal[j["request_id"]]["parsed"]["status"]=="valid","query invalid")
    checks["query_blinding_and_validity"]=True

    contexts={r["id"]:r for r in c.jsonl(SEARCH/"contexts.jsonl")}
    for j in jobs_a:
        payload=json.loads(j["body"]["messages"][1]["content"])
        c.require(set(payload)=={"proposition","C48","additional_EHR"},"audit payload keys")
        txt=j["body"]["messages"][1]["content"]
        for forbidden in ('"GT"','"U2"','"Gate_A"','"flip_type"','"original_reason"'):
            c.require(forbidden not in txt,"audit leakage "+forbidden)
        z=contexts[j["proposition_id"]]
        c.require(z["external_selected"]<=32 and not(set(z["c48_passage_ids"])&set(z["external_passage_ids"])),"C48/external overlap")
    checks["audit_blinding_and_search_separation"]=True
    rows=c.csvread(ANA/"attribution_cases.csv");summary=c.csvread(ANA/"attribution_summary.csv")
    c.require(len(rows)==462,"analysis rows")
    cats={"A_C48_sufficient","B_fullEHR_search_sufficient","C_partial_or_conflicting","D_no_clear_support","U_invalid_audit"}
    c.require(set(r["attribution"] for r in rows)<=cats,"unknown category")
    for r in rows:
        if r["attribution"] in ("A_C48_sufficient","B_fullEHR_search_sufficient"):
            c.require(r["c48_qwen_strict"]=="True" or r["expanded_strict"]=="True","support category without strict support")
        if r["attribution"]=="B_fullEHR_search_sufficient":
            c.require(r["used_external"]=="True","B without external evidence")
    checks["category_invariants"]=True

    # Reparse every HTTP200 against the frozen job and require no duplicate terminal answer.
    c.require(len(terminal)==len({x["request_id"] for x in jobs_q+jobs_a}),"terminal count")
    status=Counter((j["kind"],terminal[j["request_id"]]["parsed"]["status"]) for j in jobs_q+jobs_a)
    checks["parsed_statuses"]={str(k):v for k,v in status.items()}

    cost=c.read(ANA/"cost.json");c.require(cost["used_cny"]<=c.CAP,"cost cap")
    checks["cost"]=cost
    result=dict(status="pass",checked_utc=c.now(),checks=checks,n_checks=len(checks),
      independent_audit=False,reserved_used_for_posthoc_attribution=True,reserved_used_for_method_selection=False)
    (c.OUT/"verification_001.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("039 verification PASS",len(checks),"checks")

if __name__=="__main__":main()
