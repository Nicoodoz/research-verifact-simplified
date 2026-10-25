"""Build fixed A/B/C mechanism inputs and DeepSeek jobs."""
import re
from collections import Counter
import common043 as c

R036=c.ROOT/"outputs/036_final_validation"
R039=c.ROOT/"outputs/039_full_ehr_attribution"
PLAN=c.OUT/"planning_001"

def cited_external_ids(trace):
    out=[]
    for row in trace["requirements"]:
        for e in row.get("evidence",[]):
            if e.get("source")=="EHR" and str(e.get("id","")).startswith("E"):
                if e["id"] not in out:out.append(e["id"])
    return out

def choose_controls(claim,b_entries,lookup,c48_pids):
    cited_pids={x["passage_id"] for x in b_entries}
    pool=[]
    for eid,z in lookup.items():
        if not str(eid).startswith("E"):continue
        if z.get("passage_id") in cited_pids or z.get("passage_id") in c48_pids:continue
        if any(z["text"]==b["text"] for b in b_entries):continue
        pool.append(dict(eid=eid,**z))
    chosen=[]
    for b in b_entries:
        c.require(pool,"control pool exhausted")
        bc=c.category_from_line(b["text"]);bl=max(1,len(b["text"]))
        pool.sort(key=lambda z:(
          0 if c.category_from_line(z["text"])==bc else 1,
          abs(len(z["text"])-bl)/bl,
          c.jaccard(claim,z["text"]),
          c.stable_hash("043/control/v1:",z["passage_id"])))
        pick=pool.pop(0);chosen.append(pick)
    return chosen
def main():
    c.require(not PLAN.exists(),"planning exists")
    att=c.csvread(R039/"analysis_001/attribution_cases.csv")
    ids=[r["id"] for r in att if r["flip_type"]=="R" and r["attribution"]=="B_fullEHR_search_sufficient"]
    c.require(len(ids)==55 and len(set(ids))==55,"55 cohort drift")
    traces={r["id"]:r for r in c.lines(R039/"analysis_001/supported_traces.jsonl")}
    ajobs={r["proposition_id"]:r for r in c.lines(R039/"search_001/audit_jobs.jsonl")}
    mats={r["proposition_id"]:r for r in c.lines(R036/"judge_inputs_001/materials.jsonl")}
    cases=[]
    for pid in ids:
        trace=traces[pid];job=ajobs[pid];lookup=job["evidence_lookup"];claim=mats[pid]["text"];base=mats[pid]["reference"]
        eids=cited_external_ids(trace);c.require(bool(eids),"B case without cited EHR")
        b_entries=[];seen=set()
        for eid in eids:
            z=lookup[eid];key=(z.get("passage_id"),z["text"])
            if key not in seen:b_entries.append(dict(eid=eid,**z));seen.add(key)
        c48_pids={z.get("passage_id") for eid,z in lookup.items() if str(eid).startswith("C")}
        controls=choose_controls(claim,b_entries,lookup,c48_pids)
        bref,bids=c.append_entries(base,[x["text"] for x in b_entries])
        cref,cids=c.append_entries(base,[x["text"] for x in controls])
        cases.append(dict(id=pid,sid=next(r["sid"] for r in att if r["id"]==pid),
          author=next(r["author"] for r in att if r["id"]==pid),claim=claim,
          A_reference=base,B_reference=bref,C_reference=cref,B_added_ids=bids,C_added_ids=cids,
          B_source_eids=[x["eid"] for x in b_entries],B_passage_ids=[x["passage_id"] for x in b_entries],
          C_source_eids=[x["eid"] for x in controls],C_passage_ids=[x["passage_id"] for x in controls],
          B_added_chars=len(bref)-len(base),C_added_chars=len(cref)-len(base)))
    c.require(all(len(x["B_passage_ids"])==len(x["C_passage_ids"]) for x in cases),"control count mismatch")
    repeat=set(x["id"] for x in sorted(cases,key=lambda z:(c.stable_hash("043/repeat/v1:",z["id"]),z["id"]))[:12])
    logical=[];jobs=[]
    for x in cases:
        for cond in ("A","B","C"):
            ref=x[cond+"_reference"]
            for rnd in ([0,1] if x["id"] in repeat else [0]):
                rid=f"043_score_{rnd}_{cond}_{x['id']}"
                body=c.score_body(x["claim"],ref)
                jobs.append(dict(request_id=rid,kind="score",model_key="deepseek",proposition_id=x["id"],condition=cond,round=rnd,body=body))
                logical.append(dict(id=x["id"],sid=x["sid"],author=x["author"],condition=cond,round=rnd,request_id=rid,
                  reference_sha256=c.digest(ref),added_ids=x.get(cond+"_added_ids",[])))
    c.require(len(jobs)==55*3+12*3,"job count")
    bound=sum(c.bound(j) for j in jobs);c.require(bound<c.CAP,"score bound exceeds cap")
    PLAN.mkdir(parents=True)
    c.jsonl(PLAN/"cases.jsonl",cases);c.jsonl(PLAN/"score_logical.jsonl",logical);c.jsonl(PLAN/"score_jobs.jsonl",jobs)
    sources=[R039/"analysis_001/attribution_cases.csv",R039/"analysis_001/supported_traces.jsonl",R039/"search_001/audit_jobs.jsonl",
             R036/"judge_inputs_001/materials.jsonl",c.TASK/"protocol.md",c.TASK/"common043.py",c.TASK/"prepare043.py"]
    c.put(PLAN/"freeze.json",dict(created_utc=c.now(),cohort_n=55,repeat_n=12,score_jobs=len(jobs),
      score_conservative_bound_cny=bound,cohort_is_reserved_posthoc=True,API_input_excludes_GT=True,
      B_added_passages=sum(len(x["B_passage_ids"]) for x in cases),
      B_added_chars_mean=sum(x["B_added_chars"] for x in cases)/55,
      C_added_chars_mean=sum(x["C_added_chars"] for x in cases)/55,
      source_sha256={str(p.relative_to(c.ROOT)).replace("\\","/"):c.sha(p) for p in sources}))
    print("043 frozen",len(cases),"cases",len(jobs),"score jobs","bound",round(bound,3),
          "B passages",sum(len(x["B_passage_ids"]) for x in cases),flush=True)

if __name__=="__main__":main()
