"""Freeze 008 development comparisons and request only previously unscored pairs."""
from collections import Counter
import study009 as s


def prepare():
    inputs=s.pilot.jsonl(s.PRIOR/"preparation_001/inputs.jsonl")
    cohort=s.pilot.read_csv(s.PRIOR/"preparation_001/cohort.csv")[1]
    corpus=s.pilot.jsonl(s.PRIOR/"preparation_001/corpus.jsonl")
    passages={x["passage_id"]:x for x in corpus}
    rankings={x["proposition_id"]:x["query_rankings"][0] for x in s.pilot.jsonl(s.PRIOR/"candidates_001/candidates.jsonl")}
    previous={x["proposition_id"]:x for x in s.pilot.jsonl(s.PRIOR/"judge_preparation_001/inputs.jsonl")}
    old_values,_=s.prior_stages.phase_data("rerank")
    diagnostic=set()
    repeats=set()
    for sid in s.prior.PATIENTS:
        for author in ("llm","human"):
            part=sorted([x for x in inputs if x["subject_id"]==sid and x["author_type"]==author],key=lambda x:s.pilot.digest_text("009/dev-diagnostic/v1:"+x["proposition_id"]))
            diagnostic.update(x["proposition_id"] for x in part[:2])
            repeats.add(part[0]["proposition_id"])
    rows,jobs=[],[]
    for item in inputs:
        pid=item["proposition_id"]
        r=rankings[pid]
        variants={method+"48":dict(candidate_ids=s.candidates(r,method),order="rerank",max_per_note=2) for method in ("A","B","C")}
        if pid in diagnostic:
            variants.update({method+"80":dict(candidate_ids=s.candidates(r,method,80),order="rerank",max_per_note=2) for method in ("A","B")})
            variants["B48_no_rerank"]=dict(candidate_ids=s.candidates(r,"B"),order="dense_cosine",max_per_note=2)
            variants["B48_no_note_cap"]=dict(candidate_ids=s.candidates(r,"B"),order="rerank",max_per_note=16)
        union=sorted({key for v in variants.values() for key in v["candidate_ids"]})
        old=old_values["rerank:"+pid]
        assert old["job"]["body"]["query"]==item["text"] and old["job"]["body"]["model"]==s.RERANK_MODEL
        assert old["job"]["body"]["max_chunks_per_doc"]==1
        old_ids=old["job"]["passage_ids"]
        assert old["job"]["body"]["documents"]==[passages[key]["search_text"] for key in old_ids]
        old_scores={old_ids[x["index"]]:float(x["relevance_score"]) for x in old["native"]["results"]}
        assert old_scores==previous[pid]["scores"]
        needed=[key for key in union if key not in old_scores]
        sentinel=[min(old_scores,key=lambda key:s.pilot.digest_text("009/sentinel/v1:"+key))] if pid in repeats else []
        request_ids=sorted(set(needed+sentinel))
        if request_ids:
            jobs.append(dict(request_id="dev_rerank:"+pid,kind="rerank",proposition_id=pid,passage_ids=request_ids,
                new_passage_ids=needed,sentinel_ids=sentinel,body=dict(model=s.RERANK_MODEL,query=item["text"],documents=[passages[key]["search_text"] for key in request_ids],
                top_n=len(request_ids),return_documents=False,max_chunks_per_doc=1)))
        rows.append(dict(item,rankings=r,variants=variants,cached_scores=old_scores,cached_receipt=old["receipt"]["request_id"],
            new_score_ids=needed,sentinel_ids=sentinel,repeat_baseline=pid in repeats,diagnostic=pid in diagnostic))
    jobs.sort(key=lambda j:s.pilot.digest_text("009/dev-rerank-order/v1:"+j["request_id"]))
    out=s.OUT/"development_001/preparation"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_csv(out/"cohort.csv",cohort)
    s.pilot.write_jsonl(out/"inputs.jsonl",rows)
    s.pilot.write_jsonl(out/"corpus.jsonl",corpus)
    s.pilot.write_jsonl(out/"jobs.jsonl",jobs)
    s.pilot.write_json(out/"judge_prompts.json",s.read_json(s.PRIOR/"preparation_001/judge_prompts.json"))
    summary=dict(claims=144,diagnostic_claims=len(diagnostic),repeat_claims=len(repeats),main_variants=["A48","B48","C48"],
        diagnostic_variants=["A80","B80","B48_no_rerank","B48_no_note_cap"],new_rerank_requests=len(jobs),
        new_pair_scores=sum(len(j["new_passage_ids"]) for j in jobs),sentinel_pairs=sum(len(j["sentinel_ids"]) for j in jobs),
        all_variants_same_index_and_final_ceiling=True,expected_development_judge_cny_upper_estimate=4.5,
        expected_task_cny=28.0,task_cap_cny=40,stage_caps_cny=s.STAGE_CAPS)
    s.pilot.write_json(out/"summary.json",summary)
    s.seal(out,[s.PRIOR/"preparation_001/manifest.json",s.PRIOR/"candidates_001/manifest.json",s.PRIOR/"judge_preparation_001/manifest.json",s.PRIOR/"live/rerank/state.json"],
        [s.TASK/"study009.py",s.TASK/"prepare_development.py"])
    print(s.pilot.canonical(summary))


if __name__=="__main__":
    prepare()
