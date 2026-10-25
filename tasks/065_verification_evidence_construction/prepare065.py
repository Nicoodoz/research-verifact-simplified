from pathlib import Path
from collections import Counter,defaultdict
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/065_verification_evidence_construction"))
import common065 as c

def main():
    if any(c.OUT.iterdir()): raise RuntimeError("065 output not empty")
    cases={x["id"]:x for x in c.lines(c.R044/"planning_001/eval_cases.jsonl")}
    score=c.read(c.R044/"results_recovery_001/score_rows.json")
    base=[x for x in score if x.get("round")==0 and x.get("condition")=="base"
          and x.get("Score") and x.get("scores")]
    by=defaultdict(list)
    for x in base: by[str(x["sid"])].append(x)
    c.require(len(by)==8,"expected 8 eval patients")
    candidates={x["proposition_id"]:x for x in c.lines(c.R031/"retrieval_001/candidates.jsonl")}
    corpus={x["passage_id"]:x for x in c.lines(c.R031/"materials_001/corpus.jsonl")}
    cohort=[]

    for sid in sorted(by):
        rows=by[sid]
        boundary=[x for x in rows if x["Score"]!=x["U2"]]
        stable=[x for x in rows if x["Score"]==x["U2"] and
                max(float(v) for v in x["scores"].values())>=80]
        c.require(boundary and len(stable)>=2,"insufficient cohort strata "+sid)
        boundary.sort(key=lambda x:(c.stable("065/boundary/v1:",x["id"]),x["id"]))
        stable.sort(key=lambda x:(c.stable("065/stable/v1:",x["id"]),x["id"]))
        chosen=[("boundary",boundary[0]),("stable",stable[0]),("stable",stable[1])]
        for typ,r in chosen:
            z=cases[r["id"]]
            c.require(r["id"] in candidates,"missing C48 "+r["id"])
            c48ids=candidates[r["id"]]["candidate_ids"]["C48"]
            c.require(all(pid in corpus for pid in c48ids),"missing corpus passage")
            cohort.append(dict(
                id=r["id"],sid=str(sid),author=z["author"],type=typ,
                claim=z["claim"],base_reference=z["base"],base_ids=z["base_ids"],
                c48_candidate_ids=c48ids,
                historical_raw=r["Score"],historical_U2=r["U2"],
                historical_scores=r["scores"]))
    c.require(len(cohort)==24 and len({x["id"] for x in cohort})==24,"cohort size")

    jobs=[]
    for x in cohort:
        h=c.stable("",x["id"])[:24]
        jobs.append(dict(request_id="065_A_"+h,stage="stage1",kind="judge",
                         model_key="deepseek",condition="A",id=x["id"],
                         body=c.score_body(x["claim"],x["base_reference"])))
        jobs.append(dict(request_id="065_P_"+h,stage="stage1",kind="planner",
                         model_key="qwen",condition="planner",id=x["id"],
                         body=c.query_body(x["claim"])))
    c.jsonl(c.OUT/"cohort_blind.jsonl",cohort)
    c.jsonl(c.OUT/"stage1_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    sources=[
        c.R044/"planning_001/eval_cases.jsonl",
        c.R044/"results_recovery_001/score_rows.json",
        c.R031/"retrieval_001/candidates.jsonl",
        c.R031/"materials_001/corpus.jsonl",
        ROOT/"tasks/065_verification_evidence_construction/protocol.md",
        ROOT/"tasks/065_verification_evidence_construction/common065.py",
        Path(__file__),
    ]
    c.put(c.OUT/"freeze.json",dict(
        created_utc=c.now(),cohort_n=len(cohort),
        patients=sorted(by),types=dict(Counter(x["type"] for x in cohort)),
        stage1_jobs=len(jobs),cap_cny=c.CAP,selection_uses_GT=False,GT_not_in_API=True,
        source_sha256={str(q.relative_to(ROOT)):c.sha(q) for q in sources}))
    print("065 PREPARED",dict(Counter(x["type"] for x in cohort)),
          "patients",len(by),"jobs",len(jobs),flush=True)

if __name__=="__main__": main()
