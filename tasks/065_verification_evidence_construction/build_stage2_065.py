from pathlib import Path
from collections import Counter
import json,re,sys,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/065_verification_evidence_construction"))
import common065 as c
import run065
sys.path.insert(0,str(ROOT/"tasks/031_training_expansion_confirmation"))
import api031 as a031

def main():
    if (c.OUT/"stage2_jobs.jsonl").exists():raise RuntimeError("stage2 exists")
    cases=c.lines(c.OUT/"screen_cases_blind.jsonl")
    attempts,term=run065.state()
    corpus_rows=c.lines(c.R031/"materials_001/corpus.jsonl")
    corpus={x["passage_id"]:x for x in corpus_rows}
    subjects={x["sid"] for x in cases}
    subcorpus={sid:[p for p in corpus_rows if str(p["subject_id"])==str(sid)] for sid in subjects}
    embedding_ids=c.read(c.R031/"materials_001/embedding_ids.json")
    arr=np.load(c.R031/"materials_001/vectors.npy",allow_pickle=False)
    c.require(len(embedding_ids)==len(arr),"vector length")
    vectors={k:arr[i] for i,k in enumerate(embedding_ids)}
    _,term031,_=a031.state()
    for job in c.lines(c.R031/"materials_001/embedding_jobs.jsonl"):
        rr=term031.get(job["request_id"])
        c.require(rr is not None and rr["parsed"]["status"]=="success","embedding receipt")
        native=json.loads(rr["transport"]["body_text"])
        for z in native["data"]:
            vectors[job["text_ids"][z["index"]]]=np.asarray(z["embedding"],float)
    indices={}
    for sid,pp in subcorpus.items():
        c.require(pp and all(p["embedding_id"] in vectors for p in pp),"patient vectors")
        indices[sid]=c.pc.HybridIndex(pp,[vectors[p["embedding_id"]] for p in pp])
    contexts=[];jobs=[]
    for x in cases:
        pid=x["id"];h=c.stable("",pid)[:24];prid="065_plan_"+h
        c.require(prid in term,"missing planner "+pid)
        pp=term[prid]["parsed"];c.require(pp.get("status")=="valid","invalid planner "+pid)
        req=list(pp["requirements"]);queries=list(pp["queries"])
        idx=indices[x["sid"]];c.require(x["claim_embedding_id"] in vectors,"missing claim vector")
        full=idx.retrieve(x["claim"],vectors[x["claim_embedding_id"]],limit=len(idx.passages))
        rankings=[[z[0] for z in full["dense"]],[z[0] for z in full["bm25"]]]
        for q in queries+req:rankings.append([z[0] for z in idx.bm25(str(q))])
        fused=Counter()
        for ranking in rankings:
            for rank,pid2 in enumerate(ranking,1):fused[pid2]+=1/(60+rank)
        c48ids=list(x["c48_candidate_ids"])
        c48set=set(c48ids);c48text={c.norm(corpus[p]["text"]) for p in c48ids}
        external=[p for p in sorted(fused,key=lambda z:(-fused[z],z))
                  if p not in c48set and c.norm(corpus[p]["text"]) not in c48text][:24]
        b_lookup={f"C{i+1:02d}":p for i,p in enumerate(c48ids)}
        c_lookup=dict(b_lookup)
        c_lookup.update({f"E{i+1:02d}":p for i,p in enumerate(external)})
        b_candidates=[c.candidate_line(k,corpus[p]) for k,p in b_lookup.items()]
        c_candidates=[c.candidate_line(k,corpus[p]) for k,p in c_lookup.items()]
        for cond,lookup,cands in (("B",b_lookup,b_candidates),("C",c_lookup,c_candidates)):
            rid=f"065_comp{cond}_"+h
            jobs.append(dict(request_id=rid,stage="stage2",kind="composer",
                model_key="qwen",condition=cond,id=pid,candidate_lookup=lookup,
                body=c.composer_body(x["claim"],req,cands)))
        contexts.append(dict(id=pid,sid=x["sid"],requirements=req,queries=queries,
            c48_n=len(c48ids),external_n=len(external),external_pids=external,
            corpus_n=len(idx.passages)))
    c.jsonl(c.OUT/"search_contexts.jsonl",contexts)
    c.jsonl(c.OUT/"stage2_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.CAP+1e-9,"stage2 conservative cap")
    c.put(c.OUT/"stage2_freeze.json",dict(created_utc=c.now(),jobs=len(jobs),
        current_used_cny=used,stage2_bound_cny=bound,total_bound_cny=used+bound,
        external_mean=float(np.mean([x["external_n"] for x in contexts])),
        planner_valid=len(contexts),GT_used=False))
    print("065 STAGE2 BUILT",len(jobs),"used",round(used,4),"bound",round(bound,4),flush=True)

if __name__=="__main__":main()
