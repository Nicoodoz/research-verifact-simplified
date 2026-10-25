"""First-pass 008 loss map and new-patient metadata budget counts; offline only."""
from collections import Counter,defaultdict
import study009 as s


def inspect():
    for name in ("preparation_001","plans_001","candidates_001","judge_preparation_001","run_001/analysis","run_001/review_001/semantic_003"):
        s.prior.check_files(s.PRIOR/name)
    inputs={x["proposition_id"]:x for x in s.pilot.jsonl(s.PRIOR/"preparation_001/inputs.jsonl")}
    corpus=s.pilot.jsonl(s.PRIOR/"preparation_001/corpus.jsonl")
    passages={x["passage_id"]:x for x in corpus}
    ranked={x["proposition_id"]:x for x in s.pilot.jsonl(s.PRIOR/"candidates_001/candidates.jsonl")}
    packed={x["proposition_id"]:x for x in s.pilot.jsonl(s.PRIOR/"judge_preparation_001/inputs.jsonl")}
    plans=s.pilot.jsonl(s.PRIOR/"plans_001/plans.jsonl")
    relaxed=[]
    new_queries={}
    catalogs={**s.read_json(s.PRIOR/"preparation_001/embedding_catalog.json"),**s.read_json(s.PRIOR/"plans_001/embedding_catalog.json")}
    for x in plans:
        try:
            plan=s.relaxed_plan(x["output_text"],inputs[x["proposition_id"]])
            error=None
        except (ValueError,TypeError,KeyError) as exc:
            plan=dict(queries=[])
            error=str(exc)
        relaxed.append(dict(proposition_id=x["proposition_id"],case_id=x["case_id"],old_status=x["status"],
            status="fallback_direct" if error else "validated",error=error,queries=plan["queries"]))
        for text in plan["queries"]:
            hid=s.pilot.digest_text(text)
            if hid not in catalogs:
                new_queries[hid]=text
    losses=[]
    proposed=[]
    for pid,item in ranked.items():
        r=item["query_rankings"][0]
        pools={a:s.candidates(r,a) for a in ("A","B","C")}
        assert pools["A"]==item["candidate_ids"]["direct"]
        proposed.append(dict(proposition_id=pid,case_id=item["case_id"],candidate_ids=pools,
            dense48_lost_by_A=len(set(pools["B"])-set(pools["A"])),route_top24_preserved_by_C=all(set([p for p,_ in r[k]][:24])<=set(pools["C"]) for k in ("dense","bm25"))))
        for method in ("direct","simple","planner"):
            selected=packed[pid]["retrieval"][method]
            loss=Counter(x["reason"] for x in selected["selection_skips"])
            losses.append(dict(proposition_id=pid,case_id=item["case_id"],method=method,skip_counts=dict(loss),
                selected=len(selected["selected_ids"]),tiny_selected=sum(len(passages[k]["text"])<40 for k in selected["selected_ids"]),
                dense48_lost_before_rerank=len(set(pools["B"])-set(item["candidate_ids"][method])),
                original_A_candidates_lost=len(set(pools["A"])-set(item["candidate_ids"][method]))))
    anchor_rows=[]
    for anchor in s.read_json(s.PRIOR/"run_001/review_001/semantic_003/evidence_anchors.json"):
        if anchor["kind"]!="ehr":
            continue
        cid=anchor["case_id"]
        pid=next(x for x,r in inputs.items() if r["case_id"]==cid)
        p=passages[anchor["passage_id"]]
        equivalents={x["passage_id"] for x in corpus if x["subject_id"]==p["subject_id"] and (x["date"],x["category"],x["text"])==(p["date"],p["category"],p["text"])}
        r=ranked[pid]["query_rankings"][0]
        row=dict(case_id=cid,proposition_id=pid,note_id=p["note_id"],start=p["start"],quote=anchor["quote"],passage_id=p["passage_id"],
            proposed_candidate_membership={a:bool(equivalents&set(s.candidates(r,a))) for a in ("A","B","C")},
            original_rank_positions=anchor["direct_query_ranks"],original_candidate_membership=anchor["candidate_literal_equivalent_membership"],
            original_selected_membership=anchor["selected_literal_equivalent_membership"],original_selection_disposition=anchor["selection_disposition"],
            actual_008_reranker_saw_passage=bool(equivalents&set(packed[pid]["scores"])),not_gold_recall=True)
        anchor_rows.append(row)
    new_patients=s.patient_order()[18:24]
    master=s.ROOT/"outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
    rows=s.pilot.subset_csv(master,"subject_id",set(new_patients))
    valid=[x for x in rows if x["proposition_type"]=="claim" and x["invalid"]=="False"]
    new_scope=dict(patient_ids=new_patients,next_hash_positions="19-24",claims=len(valid),
        by_author={a:dict(Counter(x["human_gt"] for x in valid if x["author_type"]==a)) for a in ("llm","human")},
        by_patient={sid:dict(Counter(x["author_type"] for x in valid if x["subject_id"]==sid)) for sid in new_patients},
        remaining_development_patients=16,clinical_text_or_new_results_read=False)
    out=s.OUT/"inspection_001"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/"losses.jsonl",losses)
    s.pilot.write_jsonl(out/"proposed_candidates.jsonl",proposed)
    s.pilot.write_jsonl(out/"anchor_loss_paths.jsonl",anchor_rows)
    s.pilot.write_jsonl(out/"relaxed_plans.jsonl",relaxed)
    s.pilot.write_json(out/"uncached_plan_query_texts.json",new_queries)
    s.pilot.write_json(out/"confirmation_metadata.json",new_scope)
    summary=dict(old_claims=len(inputs),raw_plan_whitespace_validation=dict(Counter(x["status"] for x in relaxed)),
        newly_usable_plans=sum(x["old_status"]=="fallback_direct" and x["status"]=="validated" for x in relaxed),uncached_plan_queries=len(new_queries),
        mean_dense48_lost_by_A=sum(x["dense48_lost_by_A"] for x in proposed)/len(proposed),
        all_C_preserves_each_route_top24=all(x["route_top24_preserved_by_C"] for x in proposed),
        original_skip_reasons={a:dict(sum((Counter(x["skip_counts"]) for x in losses if x["method"]==a),Counter())) for a in ("direct","simple","planner")},
        confirm_metadata=new_scope,api_calls=0)
    s.pilot.write_json(out/"summary.json",summary)
    s.seal(out,[s.PRIOR/"preparation_001/manifest.json",s.PRIOR/"candidates_001/manifest.json",s.PRIOR/"judge_preparation_001/manifest.json",master,
        s.ROOT/"outputs/003_error_analysis/patient_groups.json"],[s.TASK/"study009.py",s.TASK/"inspect_existing.py"])
    print(s.pilot.canonical(summary))


if __name__=="__main__":
    inspect()
