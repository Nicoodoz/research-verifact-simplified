from pathlib import Path
from collections import Counter
import csv,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
import common066 as c

SOURCES={
 "031":dict(candidates=ROOT/"outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl",
            corpus=ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl"),
 "020":dict(candidates=ROOT/"outputs/020_lambda2_patient_validation/new10/candidates_001/candidates.jsonl",
            corpus=ROOT/"outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl"),
 "016":dict(candidates=ROOT/"outputs/016_disagreement_triggered_review_validation/stage1/candidates_001/candidates.jsonl",
            corpus=ROOT/"outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/corpus.jsonl"),
 "009":dict(candidates=ROOT/"outputs/009_retrieval_baselines/confirmation_001/candidates/candidates.jsonl",
            corpus=ROOT/"outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl"),
}
ORDER=("031","020","016","009")

def load_candidates(path):
    out={}
    for x in c.lines(path):
        pid=str(x.get("proposition_id") or x.get("id") or "")
        ids=(x.get("candidate_ids") or {}).get("C48") or x.get("C48")
        if pid and isinstance(ids,list) and ids:
            out[pid]=ids
    return out

def load_sidset(path):
    out=set()
    for x in c.lines(path):
        sid=str(x.get("subject_id") or x.get("sid") or "")
        if sid: out.add(sid)
    return out

def main():
    if any(c.OUT.iterdir()): raise RuntimeError("066 output not empty")
    pred=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")))
    cases={x["id"]:x for x in c.lines(ROOT/"outputs/053_thinking_prior_validation/evaluation_cases.jsonl")}
    errors=[r for r in pred if r["TS_PriorG"]!=r["GT"]]
    c.require(len(errors)==39,"expected 39 baseline errors")
    cmap={name:load_candidates(v["candidates"]) for name,v in SOURCES.items()}
    sidset={name:load_sidset(v["corpus"]) for name,v in SOURCES.items()}
    rows=[];jobs=[]

    for r in errors:
        pid=r["id"];sid=str(r["sid"]);z=cases[pid]
        source=None;c48=[]
        for name in ORDER:
            if pid in cmap[name]:
                source=name;c48=cmap[name][pid];break
        if source is None:
            source=next((name for name in ORDER if sid in sidset[name]),None)
        c.require(source is not None,"no frozen corpus for "+pid)
        rows.append(dict(
            id=pid,sid=sid,author=r["author"],GT=r["GT"],claim=z["claim"],
            baseline_pred=r["TS_PriorG"],baseline_reference=z["reference"],
            corpus_source=source,c48_pids=c48,
            c48_reconstructable=bool(c48)))
        h=c.stable("",pid)[:24]
        jobs.append(dict(request_id="066_plan_"+h,stage="stage1",kind="planner",
                         model_key="qwen",id=pid,body=c.planner_body(z["claim"],r["GT"])))
    c.require(len(rows)==39,"row count")
    c.jsonl(c.OUT/"error_cases.jsonl",rows)
    c.jsonl(c.OUT/"stage1_jobs.jsonl",sorted(jobs,key=lambda x:x["request_id"]))

    deps=[
        ROOT/"outputs/053_thinking_prior_validation/predictions.csv",
        ROOT/"outputs/053_thinking_prior_validation/evaluation_cases.jsonl",
        ROOT/"outputs/053_thinking_prior_validation/main_jobs.jsonl",
        ROOT/"tasks/066_oracle_headroom/protocol.md",
        ROOT/"tasks/066_oracle_headroom/protocol_amendment_001.md",
        ROOT/"tasks/066_oracle_headroom/common066.py",
        Path(__file__),
    ]
    for v in SOURCES.values():
        deps.extend([v["candidates"],v["corpus"]])
    freeze=dict(
        created_utc=c.now(),
        git_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        baseline_errors=39,
        by_gt=dict(Counter(x["GT"] for x in rows)),
        c48_reconstructable=sum(x["c48_reconstructable"] for x in rows),
        source_counts=dict(Counter(x["corpus_source"] for x in rows)),
        stage1_jobs=len(jobs),cap_cny=c.CAP,
        oracle_GT_enters_planner=True,
        GT_not_in_final_judge=True,
        reserved_used=False,
        source_sha256={str(q.relative_to(ROOT)):c.sha(q) for q in deps})
    c.put(c.OUT/"freeze.json",freeze)
    print("066 PREPARED",freeze,flush=True)

if __name__=="__main__": main()
