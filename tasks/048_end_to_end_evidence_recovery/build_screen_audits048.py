"""Build K/G evidence-audit jobs after shared claim-only query planning."""
from pathlib import Path
from collections import Counter
import json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c
import run048
sys.path.insert(0,str(ROOT/"tasks/031_training_expansion_confirmation"))
import api031 as a031

def norm(s):return re.sub(r"\s+"," ",s).strip()

def main():
    if (c.OUT/"screen_stage2_jobs.jsonl").exists():raise RuntimeError("screen stage2 already built")
    cases=c.lines(c.OUT/"screen_cases.jsonl")
    attempts,terminal=run048.state()
    corpus_rows=c.lines(c.R031/"materials_001/corpus.jsonl")
    corpus={x["passage_id"]:x for x in corpus_rows}
    subjects={x["sid"] for x in cases}
    subcorpus={sid:[p for p in corpus_rows if str(p["subject_id"])==str(sid)] for sid in subjects}

    embedding_ids=c.read(c.R031/"materials_001/embedding_ids.json")
    arr=np.load(c.R031/"materials_001/vectors.npy",allow_pickle=False)
    c.require(len(embedding_ids)==len(arr),"vector id length mismatch")
    vectors={k:arr[i] for i,k in enumerate(embedding_ids)}
    _,term031,_=a031.state()
    for job in c.lines(c.R031/"materials_001/embedding_jobs.jsonl"):
        rr=term031.get(job["request_id"])
        c.require(rr is not None and rr["parsed"]["status"]=="success","031 embedding receipt missing/invalid")
        native=json.loads(rr["transport"]["body_text"])
        for z in native["data"]:
            vectors[job["text_ids"][z["index"]]]=np.asarray(z["embedding"],float)
    indices={}
    for sid,pp in subcorpus.items():
        c.require(pp,"empty patient corpus")
        c.require(all(p["embedding_id"] in vectors for p in pp),"missing corpus vector")
        indices[sid]=c.pc.HybridIndex(pp,[vectors[p["embedding_id"]] for p in pp])

    contexts=[];jobs=[]
    for x in cases:
        pid=x["id"];h=c.stable("",pid)[:24]
        qrid="048_Q_"+h
        c.require(qrid in terminal,"missing query result")
        qp=terminal[qrid]["parsed"]
        queries=qp.get("queries") if qp.get("status")=="valid" else []
        requirements=qp.get("requirements") if qp.get("status")=="valid" else []
        idx=indices[x["sid"]]
        c.require(x["claim_embedding_id"] in vectors,"missing claim vector")
        full=idx.retrieve(x["claim"],vectors[x["claim_embedding_id"]],limit=len(idx.passages))
        rankings=[[z[0] for z in full["dense"]],[z[0] for z in full["bm25"]]]
        for q in queries:rankings.append([z[0] for z in idx.bm25(q)])
        fused=Counter()
        for ranking in rankings:
            for rank,pid2 in enumerate(ranking,1):fused[pid2]+=1/(60+rank)
        base_text={norm(corpus[p]["text"]) for p in x["base_ids"] if p in corpus}
        gpool=[p for p in sorted(fused,key=lambda z:(-fused[z],z))
          if p not in set(x["base_ids"]) and norm(corpus[p]["text"]) not in base_text][:32]
        kpool=[p for p in x["d48_extra_ids"] if p in corpus]
        kj=c.build_audit_job("048_Kaudit_"+h,x["claim"],x["base_reference"],kpool,corpus)
        gj=c.build_audit_job("048_Gaudit_"+h,x["claim"],x["base_reference"],gpool,corpus)
        kj.update(stage="screen_stage2",condition="K",id=pid)
        gj.update(stage="screen_stage2",condition="G",id=pid)
        jobs.extend([kj,gj])
        contexts.append(dict(id=pid,sid=x["sid"],query_request_id=qrid,query_status=qp.get("status"),
          requirements=requirements,queries=queries,K_candidate_pids=kpool,G_candidate_pids=gpool,
          K_n=len(kpool),G_n=len(gpool),corpus_n=len(idx.passages)))

    c.jsonl(c.OUT/"screen_search_contexts.jsonl",contexts)
    c.jsonl(c.OUT/"screen_stage2_jobs.jsonl",sorted(jobs,key=lambda z:z["request_id"]))
    used=sum(a["cost"] for a in attempts);bound=sum(c.bound(j) for j in jobs)
    c.require(used+bound<=c.SCREEN_CAP+1e-9,"screen stage2 conservative bound exceeds cap")
    c.put(c.OUT/"screen_stage2_freeze.json",dict(created_utc=c.now(),claims=len(cases),
      jobs=len(jobs),query_valid=sum(x["query_status"]=="valid" for x in contexts),
      K_candidate_mean=float(np.mean([x["K_n"] for x in contexts])),
      G_candidate_mean=float(np.mean([x["G_n"] for x in contexts])),
      max_external_G=32,current_used_cny=used,stage2_bound_cny=bound,total_bound_cny=used+bound))
    print("048 AUDITS BUILT",len(jobs),"used",round(used,4),"bound",round(bound,4),
          "query_valid",sum(x["query_status"]=="valid" for x in contexts),flush=True)

if __name__=="__main__":main()
