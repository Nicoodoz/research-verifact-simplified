"""Analyze completed 038 blind evidence and reason audits; no API calls."""
import json, re
from collections import Counter, defaultdict
from pathlib import Path
import common038 as c
import execute038 as ex

PLAN=c.OUT/"planning_001"
OUT=c.OUT/"analysis_001"

def main():
    c.require(not OUT.exists(),"analysis_001 exists")
    jobs=c.jsonl(PLAN/"jobs.jsonl"); attempts,terminal=ex.state()
    c.require(len(terminal)==len(jobs),f"incomplete terminal {len(terminal)}/{len(jobs)}")
    OUT.mkdir(parents=True)
    key={r["id"]:r for r in c.csvread(PLAN/"evaluation_key.csv")}
    fullkey={r["id"]:r for r in c.csvread(c.ROOT/"outputs/036_final_validation/analysis_001/R0/predictions.csv")}
    jobmap={j["request_id"]:j for j in jobs}

    ev=defaultdict(dict); reason={}
    normalized=[]
    for rid,t in terminal.items():
        j=t["job"]; p=t["parsed"]
        normalized.append(dict(request_id=rid,proposition_id=j["proposition_id"],kind=j["kind"],
                               model_key=j["model_key"],status=p["status"],
                               audit_label=p.get("audit_label"),coverage=p.get("coverage"),
                               trace_supported=p.get("trace_supported"),citation_valid=p.get("citation_valid"),
                               alignment=p.get("alignment"),note=p.get("note"),
                               receipt=t["receipt"]))
        if j["kind"]=="evidence": ev[j["proposition_id"]][j["model_key"]]=p
        else: reason[j["proposition_id"]]=p
    c.csvwrite(OUT/"normalized.csv",normalized)
    cases=[]
    for pid,k in key.items():
        q=ev[pid]["qwen"]; d=ev[pid]["deepseek"]
        labels=(q["audit_label"],d["audit_label"])
        if labels[0]==labels[1]: agreement=labels[0]
        elif "Uncertain" in labels: agreement="disagree_or_uncertain"
        else: agreement="disagree"
        both_trace=bool(q["trace_supported"] and d["trace_supported"])
        any_trace=bool(q["trace_supported"] or d["trace_supported"])
        both_nonS=all(x in ("Not Supported","Not Addressed") for x in labels)
        cases.append(dict(**k,qwen_status=q["status"],deepseek_status=d["status"],
                          qwen_label=labels[0],deepseek_label=labels[1],
                          qwen_trace_supported=q["trace_supported"],deepseek_trace_supported=d["trace_supported"],
                          both_trace_supported=both_trace,any_trace_supported=any_trace,
                          both_nonS=both_nonS,model_agreement=agreement,
                          qwen_citation_valid=q["citation_valid"],deepseek_citation_valid=d["citation_valid"],
                          qwen_summary=q.get("summary"),deepseek_summary=d.get("summary")))
    c.csvwrite(OUT/"evidence_cases.csv",cases)

    summaries=[]
    for group in sorted({r["audit_group"] for r in cases}):
        rr=[r for r in cases if r["audit_group"]==group]
        summaries.append(summarize(group,rr))
    for ft in ("R","H","W"):
        rr=[r for r in cases if r["flip_type"]==ft]
        summaries.append(summarize("flip_"+ft,rr))
    c.csvwrite(OUT/"evidence_summary.csv",summaries)
    reason_rows=[]
    for pid,p in reason.items():
        k=key.get(pid); f=fullkey[pid]
        reason_rows.append(dict(id=pid,sid=f["sid"],author=f["author"],GT=f["GT"],
                                flip_type=k["flip_type"] if k else "nonflip_score_verdict_mismatch",
                                alignment=p["alignment"],note=p.get("note")))
    c.csvwrite(OUT/"reason_alignment.csv",reason_rows)
    rc=Counter(r["alignment"] for r in reason_rows)

    r_cases=[r for r in cases if r["flip_type"]=="R"]
    h_cases=[r for r in cases if r["flip_type"]=="H"]
    w_cases=[r for r in cases if r["flip_type"]=="W"]
    key_result=dict(
        R_n=len(r_cases),
        R_qwen_valid=sum(r["qwen_status"]=="valid" for r in r_cases),
        R_deepseek_valid=sum(r["deepseek_status"]=="valid" for r in r_cases),
        R_qwen_S=sum(r["qwen_label"]=="Supported" for r in r_cases),
        R_deepseek_S=sum(r["deepseek_label"]=="Supported" for r in r_cases),
        R_qwen_trace_supported=sum(r["qwen_trace_supported"] for r in r_cases),
        R_deepseek_trace_supported=sum(r["deepseek_trace_supported"] for r in r_cases),
        R_both_trace_supported=sum(r["both_trace_supported"] for r in r_cases),
        R_any_trace_supported=sum(r["any_trace_supported"] for r in r_cases),
        R_both_nonS=sum(r["both_nonS"] for r in r_cases),
        H_n=len(h_cases),H_both_trace_supported=sum(r["both_trace_supported"] for r in h_cases),
        W_n=len(w_cases),W_both_trace_supported=sum(r["both_trace_supported"] for r in w_cases),
        reason_alignment_counts=dict(rc),
        evidence_exact_model_agreement=sum(r["qwen_label"]==r["deepseek_label"] for r in cases),
        evidence_cases=len(cases),
    )
    c.put(OUT/"key_results.json",key_result)
    # Save the cases most relevant to the paper claim; include claim/reason but not the full C48 text.
    source_jobs={j["proposition_id"]:j for j in c.jsonl(c.ROOT/"outputs/036_final_validation/judge_inputs_001/jobs.jsonl")
                 if j.get("round")=="R0" and j.get("role")=="score"}
    source_norm={r["proposition_id"]:r for r in c.jsonl(c.ROOT/"outputs/036_final_validation/predictions_blind_001/normalized.jsonl")
                 if r.get("round")=="R0" and r.get("role")=="score"}
    critical=[]
    for row in cases:
        if row["flip_type"]=="R" and not row["both_trace_supported"]:
            payload=json.loads(source_jobs[row["id"]]["body"]["messages"][1]["content"])
            p=source_norm[row["id"]]["parsed"]["parsed"]
            critical.append(dict(id=row["id"],sid=row["sid"],author=row["author"],GT=row["GT"],
                                 original_verdict=p["verdict"],original_reason=p.get("reason"),
                                 claim=payload["proposition"],qwen_label=row["qwen_label"],
                                 deepseek_label=row["deepseek_label"],
                                 qwen_summary=row["qwen_summary"],deepseek_summary=row["deepseek_summary"]))
    with (OUT/"R_not_both_trace_supported.jsonl").open("x",encoding="utf-8",newline="\n") as f:
        for r in critical:f.write(json.dumps(r,ensure_ascii=False)+"\n")

    costs=sum(a["charge_cny"] for a in attempts)
    c.put(OUT/"cost.json",dict(attempts=len(attempts),terminal=len(terminal),used_cny=costs,cap_cny=c.CAP))
    print(json.dumps(key_result,ensure_ascii=False,indent=2))
def summarize(group,rr):
    n=len(rr); c.require(n>0,"empty group "+group)
    return dict(group=group,n=n,
        qwen_valid=sum(r["qwen_status"]=="valid" for r in rr),
        deepseek_valid=sum(r["deepseek_status"]=="valid" for r in rr),
        qwen_S=sum(r["qwen_label"]=="Supported" for r in rr),
        deepseek_S=sum(r["deepseek_label"]=="Supported" for r in rr),
        qwen_trace_supported=sum(r["qwen_trace_supported"] for r in rr),
        deepseek_trace_supported=sum(r["deepseek_trace_supported"] for r in rr),
        both_trace_supported=sum(r["both_trace_supported"] for r in rr),
        any_trace_supported=sum(r["any_trace_supported"] for r in rr),
        both_nonS=sum(r["both_nonS"] for r in rr),
        exact_label_agreement=sum(r["qwen_label"]==r["deepseek_label"] for r in rr))

if __name__=="__main__":
    main()
