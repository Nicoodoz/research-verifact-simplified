"""Freeze 039 cohort and claim-only query expansion jobs."""
import json
import common039 as c

R036=c.ROOT/"outputs/036_final_validation"
R038=c.ROOT/"outputs/038_evidence_explanation_audit"
OUT=c.OUT/"planning_001"

def main():
    c.require(not OUT.exists(),"planning exists");OUT.mkdir(parents=True)
    cohort=c.csvread(R038/"planning_001/blind_cohort.csv")
    key={r["id"]:r for r in c.csvread(R038/"planning_001/evaluation_key.csv")}
    c.require(len(cohort)==462 and sum(r["audit_group"]=="U0_to_U2_S" for r in cohort)==342,"cohort identity")
    inputs={r["proposition_id"]:r for r in c.jsonl(R036/"materials_001/inputs.jsonl")}
    materials={r["proposition_id"]:r for r in c.jsonl(R036/"judge_inputs_001/materials.jsonl")}
    rows=[];jobs=[]
    for r in cohort:
        pid=r["id"]; inp=inputs[pid]; k=key[pid]; mat=materials[pid]
        rows.append(dict(id=pid,sid=r["sid"],author=r["author"],audit_group=r["audit_group"],
                         GT=k["GT"],flip_type=k["flip_type"],claim=inp["text"],
                         c48_sha256=mat["reference_sha256"]))
        jobs.append(dict(request_id="039_query_"+pid,kind="query",model_key=c.MODEL_KEY,
                         proposition_id=pid,body=c.query_body(inp["text"])))
    c.csvwrite(OUT/"cohort_key.csv",rows)
    with (OUT/"query_jobs.jsonl").open("x",encoding="utf-8",newline="\n") as f:
        for j in jobs:f.write(json.dumps(j,ensure_ascii=False,sort_keys=True)+"\n")
    estimate=sum(c.bound(j) for j in jobs)
    sources=[
      R038/"planning_001/blind_cohort.csv",R038/"planning_001/evaluation_key.csv",
      R036/"materials_001/inputs.jsonl",R036/"materials_001/corpus.jsonl",
      R036/"judge_inputs_001/materials.jsonl",R036/"materials_001/manifest.json",
      R036/"retrieval_001/candidates.jsonl",
    ]
    c.put(OUT/"preflight.json",dict(created_utc=c.now(),n=len(rows),query_jobs=len(jobs),
      conservative_query_reservation_cny=estimate,cap_cny=c.CAP,
      source_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in sources},
      query_input_whitelist=["proposition"],note="GT/method/reason/EHR are not sent to query expansion."))
    print("039 query jobs",len(jobs),"bound CNY",round(estimate,3))

if __name__=="__main__":main()
