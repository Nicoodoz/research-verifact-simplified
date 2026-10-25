"""Registered fresh shared rerank after the bridge test failed; same queries/pools."""
import study009 as s

if __name__=="__main__":
    inputs=s.pilot.jsonl(s.OUT/"development_001/preparation/inputs.jsonl")
    passages={x["passage_id"]:x for x in s.pilot.jsonl(s.OUT/"development_001/preparation/corpus.jsonl")}
    jobs=[]
    for item in inputs:
        union=sorted({key for variant in item["variants"].values() for key in variant["candidate_ids"]})
        jobs.append(dict(request_id="dev_refresh:"+item["proposition_id"],kind="rerank",proposition_id=item["proposition_id"],passage_ids=union,
            body=dict(model=s.RERANK_MODEL,query=item["text"],documents=[passages[k]["search_text"] for k in union],
                top_n=len(union),return_documents=False,max_chunks_per_doc=1)))
    jobs.sort(key=lambda j:s.pilot.digest_text("009/devrefresh-order/v1:"+j["request_id"]))
    out=s.OUT/"development_001/rerank_refresh_preparation"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/"jobs.jsonl",jobs)
    summary=dict(requests=len(jobs),pairs=sum(len(j["passage_ids"]) for j in jobs),
        estimated_cny=sum(sum(len(d)+len(j["body"]["query"]) for d in j["body"]["documents"])*.4*.07/1e6 for j in jobs),
        budget_slot="dev_embed",actual_service="rerank",slot_cap_cny=.25,total_cap_cny=40,
        old_scores_not_used_for_new_development_conditions=True,old_responses_preserved=True)
    s.pilot.write_json(out/"summary.json",summary)
    s.seal(out,[s.OUT/"development_001/preparation/manifest.json",s.OUT/"rerank_drift_001/manifest.json",s.OUT/"execution_amendment_001.md"],
        [s.TASK/"study009.py",s.TASK/"prepare_rerank_refresh.py"])
    print(s.pilot.canonical(summary))
