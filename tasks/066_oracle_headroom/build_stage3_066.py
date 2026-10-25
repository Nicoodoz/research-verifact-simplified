from pathlib import Path
from collections import defaultdict
import sys,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
import common066 as c
import run066

CORPUS_PATH={
 "031":ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl",
 "020":ROOT/"outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl",
 "016":ROOT/"outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/corpus.jsonl",
 "009":ROOT/"outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl",
}

def main():
    if (c.OUT/"stage3_jobs.jsonl").exists():raise RuntimeError("stage3 already built")
    cases={x["id"]:x for x in c.lines(c.OUT/"error_cases.jsonl")}
    ctx={x["id"]:x for x in c.lines(c.OUT/"search_contexts.jsonl")}
    attempts,term=run066.state()
    corpora={name:c.lines(path) for name,path in CORPUS_PATH.items()}
    bysid={}
    for name,rows in corpora.items():
        g=defaultdict(dict)
        for x in rows:g[str(x.get("subject_id") or x.get("sid"))][x["passage_id"]]=x
        bysid[name]=g
    jobs=[];mapping=[]

    for pid,x in cases.items():
        h=c.stable("",pid)[:24];crid="066_comp_"+h
        c.require(crid in term,"missing composer "+pid)
        cp=term[crid]["parsed"];status=cp.get("status")
        selected=[];kept=[];reference=None;chars=0;jrid=None
        if status=="valid" and cp.get("selected"):
            lookup=ctx[pid]["candidate_short_to_pid"]
            selected=[lookup[s] for s in cp["selected"] if s in lookup]
            corpus=bysid[x["corpus_source"]][str(x["sid"])]
            reference,kept,chars=c.build_reference(selected,corpus,max_chars=8000,max_items=8)
            jrid="066_judge_"+h
            jobs.append(dict(request_id=jrid,stage="stage3",kind="judge",
                             model_key="deepseek",id=pid,body=c.score_body(x["claim"],reference)))
        c48=set(x.get("c48_pids",[]))
        mapping.append(dict(
            id=pid,composer_request_id=crid,composer_status=status,
            composer_decisive=cp.get("decisive",False),composer_unresolved=cp.get("unresolved",[]),
            selected_pids=selected,kept_pids=kept,reference=reference,reference_chars=chars,
            c48_reconstructable=x.get("c48_reconstructable",False),
            kept_all_in_c48=bool(kept) and bool(c48) and all(z in c48 for z in kept),
            kept_external_n=sum(z not in c48 for z in kept) if c48 else None,
            judge_request_id=jrid))

    c.jsonl(c.OUT/"final_mapping.jsonl",mapping)
    c.jsonl(c.OUT/"stage3_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.CAP+1e-9,"stage3 conservative bound exceeds cap")
    c.put(c.OUT/"stage3_freeze.json",dict(
        created_utc=c.now(),composer_valid=sum(x["composer_status"]=="valid" for x in mapping),
        decisive=sum(bool(x["composer_decisive"]) for x in mapping),
        judge_jobs=len(jobs),empty_selection=sum(not x["kept_pids"] for x in mapping),
        current_used_cny=used,stage3_bound_cny=bound,total_bound_cny=used+bound,
        code_sha256=c.sha(Path(__file__))))
    print("066 STAGE3 BUILT",len(jobs),"used",round(used,4),"bound",round(bound,4),flush=True)

if __name__=="__main__":main()
