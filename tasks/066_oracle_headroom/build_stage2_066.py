from pathlib import Path
from collections import Counter,defaultdict
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
import common066 as c
import run066
sys.path.insert(0,str(ROOT/"tasks/008_retrieval_planning"))
import planning_core as pc

CORPUS_PATH={
 "031":ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl",
 "020":ROOT/"outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl",
 "016":ROOT/"outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/corpus.jsonl",
 "009":ROOT/"outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl",
}

def main():
    if (c.OUT/"stage2_jobs.jsonl").exists(): raise RuntimeError("stage2 already built")
    cases=c.lines(c.OUT/"error_cases.jsonl")
    attempts,term=run066.state()
    corpora={name:c.lines(path) for name,path in CORPUS_PATH.items()}
    bysid={}
    for name,rows in corpora.items():
        g=defaultdict(list)
        for x in rows:g[str(x.get("subject_id") or x.get("sid"))].append(x)
        bysid[name]=g
    jobs=[];contexts=[]

    for x in cases:
        pid=x["id"];h=c.stable("",pid)[:24];rid="066_plan_"+h
        c.require(rid in term,"missing planner "+pid)
        plan=term[rid]["parsed"];c.require(plan.get("status")=="valid","invalid planner "+pid)
        src=x["corpus_source"];rows=bysid[src][str(x["sid"])]
        c.require(rows,"empty patient corpus "+pid)
        idx=pc.HybridIndex(rows,np.ones((len(rows),1),float))
        queries=[x["claim"]]+list(plan["requirements"])+list(plan["queries"])
        rankings=[]
        for q in queries:
            rr=[z[0] for z in idx.bm25(q)]
            if rr:rankings.append(rr)
        c.require(rankings,"no lexical ranking "+pid)
        top=pc.candidate_pool(rankings,cap=32,reserve_direct=8)
        chosen=list(top)
        for z in x.get("c48_pids",[]):
            if z not in chosen and any(p["passage_id"]==z for p in rows):
                chosen.append(z)
            if len(chosen)>=48:break
        pmap={p["passage_id"]:p for p in rows}
        chosen=[z for z in chosen if z in pmap][:48]
        short={f"C{i+1:02d}":z for i,z in enumerate(chosen)}
        rendered=[c.candidate_line(s,pmap[z]) for s,z in short.items()]
        body=c.composer_body(x["claim"],x["GT"],plan["requirements"],rendered)
        jobs.append(dict(request_id="066_comp_"+h,stage="stage2",kind="composer",
                         model_key="qwen",id=pid,body=body,candidate_lookup=short))

        contexts.append(dict(
            id=pid,sid=x["sid"],source=src,corpus_n=len(rows),
            requirements=plan["requirements"],queries=plan["queries"],
            candidate_short_to_pid=short,candidate_pids=chosen,
            c48_pids=x.get("c48_pids",[]),
            c48_reconstructable=x.get("c48_reconstructable",False)))
    c.jsonl(c.OUT/"search_contexts.jsonl",contexts)
    c.jsonl(c.OUT/"stage2_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.CAP+1e-9,"stage2 conservative bound exceeds cap")
    c.put(c.OUT/"stage2_freeze.json",dict(
        created_utc=c.now(),jobs=len(jobs),planner_valid=len(contexts),
        mean_corpus=float(np.mean([x["corpus_n"] for x in contexts])),
        mean_candidates=float(np.mean([len(x["candidate_pids"]) for x in contexts])),
        current_used_cny=used,stage2_bound_cny=bound,total_bound_cny=used+bound,
        code_sha256=c.sha(Path(__file__))))
    print("066 STAGE2 BUILT",len(jobs),"used",round(used,4),"bound",round(bound,4),flush=True)

if __name__=="__main__":main()
