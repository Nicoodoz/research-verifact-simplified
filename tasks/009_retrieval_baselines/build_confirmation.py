"""Build confirmed A/B/C queries, fresh shared reranking and cached Judge bodies."""
from collections import Counter
from pathlib import Path
import argparse
import numpy as np
import study009 as s
from io009 import stage,rerank_scores


def candidates():
    prep=s.OUT/"confirmation_001/preparation"
    s.check(prep)
    values,_=stage("confirm_embed")
    vectors={}
    failures=[]
    for rid,v in values.items():
        try:
            assert v["status"]=="received" and v["native"]["model"]==s.EMBED_MODEL
            rows=v["native"]["data"]
            assert sorted(x["index"] for x in rows)==list(range(len(v["job"]["text_ids"])))
            batch={}
            for x in rows:
                key=v["job"]["text_ids"][x["index"]]
                array=np.asarray(x["embedding"],dtype=np.float64)
                assert array.shape==(1024,) and np.isfinite(array).all() and np.linalg.norm(array)>0
                batch[key]=array
            assert not set(batch)&set(vectors)
            vectors.update(batch)
        except (AssertionError,ValueError,KeyError,TypeError) as e:
            failures.append(dict(request_id=rid,error=str(e),affected_text_ids=v["job"]["text_ids"]))
    inputs=s.pilot.jsonl(prep/"inputs.jsonl")
    corpus=s.pilot.jsonl(prep/"corpus.jsonl")
    missing_patients={p["subject_id"] for p in corpus if p["embedding_id"] not in vectors}
    passages={p["passage_id"]:p for p in corpus}
    indices={}
    for sid in {p["subject_id"] for p in corpus}-missing_patients:
        pp=[p for p in corpus if p["subject_id"]==sid]
        indices[sid]=s.core.HybridIndex(pp,[vectors[p["embedding_id"]] for p in pp])
    records,jobs=[],[]
    for item in inputs:
        if item["subject_id"] in missing_patients or item["claim_embedding_id"] not in vectors:
            records.append(dict(proposition_id=item["proposition_id"],case_id=item["case_id"],status="blocked_incomplete_embedding",candidate_ids={}))
            continue
        empty_index=item["subject_id"] not in indices
        ranks=dict(bm25=[],dense=[],hybrid=[]) if empty_index else indices[item["subject_id"]].retrieve(item["text"],vectors[item["claim_embedding_id"]])
        pools={a+"48":s.candidates(ranks,a) for a in ("A","B","C")}
        union=sorted({key for pool in pools.values() for key in pool})
        docs=[passages[key]["search_text"] for key in union]
        assert all(len((item["text"]+doc).encode("utf-8"))<8192 for doc in docs)
        if union:
            jobs.append(dict(request_id="confirm_rerank:"+item["proposition_id"],kind="rerank",proposition_id=item["proposition_id"],passage_ids=union,
                body=dict(model=s.RERANK_MODEL,query=item["text"],documents=docs,top_n=len(union),return_documents=False,max_chunks_per_doc=1)))
        records.append(dict(proposition_id=item["proposition_id"],case_id=item["case_id"],status="ready_empty_index" if empty_index else "ready",rankings=ranks,candidate_ids=pools))
    jobs.sort(key=lambda j:s.pilot.digest_text("009/confirm-rerank/v1:"+j["request_id"]))
    out=s.OUT/"confirmation_001/candidates"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/"candidates.jsonl",records)
    s.pilot.write_jsonl(out/"jobs.jsonl",jobs)
    s.pilot.write_json(out/"embedding_failures.json",failures)
    ids=sorted(vectors)
    np.save(out/"vectors.npy",np.asarray([vectors[key] for key in ids]),allow_pickle=False)
    s.pilot.write_json(out/"embedding_ids.json",ids)
    summary=dict(claims=len(records),ready=sum(r["status"]=="ready" for r in records),rerank_requests=len(jobs),
        total_pairs=sum(len(j["passage_ids"]) for j in jobs),embedding_failures=len(failures),incomplete_index_patients=sorted(missing_patients))
    s.pilot.write_json(out/"summary.json",summary)
    s.seal(out,[prep/"manifest.json",s.OUT/"live/confirm_embed/state.json"],[Path(__file__),s.TASK/"study009.py",s.TASK/"io009.py"])
    print(s.pilot.canonical(summary))


def judge():
    folder=s.OUT/"confirmation_001"
    prep=folder/"preparation"
    s.check(prep)
    s.check(folder/"candidates")
    inputs=s.pilot.jsonl(prep/"inputs.jsonl")
    candidates={x["proposition_id"]:x for x in s.pilot.jsonl(folder/"candidates/candidates.jsonl")}
    passages={x["passage_id"]:x for x in s.pilot.jsonl(prep/"corpus.jsonl")}
    prompts=s.read_json(prep/"judge_prompts.json")
    values,_=stage("confirm_rerank")
    records,assignments,jobs=[],[],{}
    failures=[]
    for item in inputs:
        pid=item["proposition_id"]
        results={}
        try:
            assert candidates[pid]["status"] in {"ready","ready_empty_index"},"Incomplete index/query embedding"
            scores={} if candidates[pid]["status"]=="ready_empty_index" else rerank_scores(values["confirm_rerank:"+pid])
        except (AssertionError,KeyError,TypeError,ValueError) as e:
            scores={}
            failures.append(dict(proposition_id=pid,error=str(e)))
        for name in ("A48","B48","C48"):
            pool=candidates[pid]["candidate_ids"].get(name)
            if pool is None or set(pool)-set(scores):
                results[name]=dict(status="missing_evidence")
                assignments.append(dict(proposition_id=pid,case_id=item["case_id"],method=name,status="missing_evidence",source="009",request_id="",body_sha256=""))
                continue
            r=s.core.select_evidence(pool,scores,passages,item["admission"])
            body=s.prior_stages.judge_body(item,r["reference"],prompts)
            sha=s.pilot.fingerprint(body)
            rid="confirmjud:"+sha
            jobs[rid]=dict(request_id=rid,kind="chat",body=body)
            results[name]=dict(r,status="ready",candidate_ids=pool,score_kind="rerank",max_per_note=2,body_sha256=sha,request_id=rid,source="009")
            assignments.append(dict(proposition_id=pid,case_id=item["case_id"],method=name,status="ready",source="009",request_id=rid,body_sha256=sha))
        records.append(dict(item,scores=scores,rankings=candidates[pid].get("rankings",{}),retrieval=results,diagnostic=False))
    repeats=[]
    repeat_missing=[]
    for sid in s.patient_order()[18:24]:
        for author in ("llm","human"):
            item=min([x for x in records if x["subject_id"]==sid and x["author_type"]==author],key=lambda r:s.pilot.digest_text("009/confirm-repeat/v1:"+r["proposition_id"]))
            base=item["retrieval"]["A48"]
            if base["status"]!="ready":
                repeat_missing.append(item["proposition_id"])
                continue
            rid="confirmrepeat:"+item["proposition_id"]
            body=jobs[base["request_id"]]["body"]
            jobs[rid]=dict(request_id=rid,kind="chat",body=body)
            repeats.append(dict(proposition_id=item["proposition_id"],case_id=item["case_id"],request_id=rid,canonical_request_id=base["request_id"],body_sha256=base["body_sha256"],source="within_009_confirmation_diagnostic_only"))
    jobs=sorted(jobs.values(),key=lambda j:s.pilot.digest_text("009/confirm-judge/v1:"+j["request_id"]))
    out=folder/"judge_preparation"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/"inputs.jsonl",records)
    s.pilot.write_csv(out/"assignments.csv",assignments)
    s.pilot.write_jsonl(out/"jobs.jsonl",jobs)
    s.pilot.write_json(out/"repeats.json",repeats)
    s.pilot.write_json(out/"failures.json",dict(evidence_failures=failures,missing_repeat_ids=repeat_missing))
    summary=dict(claims=len(inputs),logical_conditions=len(assignments),unique_requests=len(jobs),repeat_requests=len(repeats),
        saved_calls=sum(a["status"]=="ready" for a in assignments)+len(repeats)-len(jobs),evidence_failures=len(failures),
        mean_reference_characters={a:sum(len(x["retrieval"][a].get("reference","")) for x in records)/len(records) for a in ("A48","B48","C48")},
        expected_judge_peak_cny=sum((sum(len(m["content"]) for m in j["body"]["messages"])*.4*3+350*9)/1e6 for j in jobs),
        cache_scope="Current confirmation complete request bodies only; no old patient Judge outputs reused")
    s.pilot.write_json(out/"summary.json",summary)
    s.seal(out,[prep/"manifest.json",folder/"candidates/manifest.json",s.OUT/"live/confirm_rerank/state.json",s.OUT/"confirmation_protocol_001.json"],
        [Path(__file__),s.TASK/"io009.py",s.TASK/"study009.py"])
    print(s.pilot.canonical(summary))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=("candidates","judge"))
    a=p.parse_args()
    globals()[a.stage]()
