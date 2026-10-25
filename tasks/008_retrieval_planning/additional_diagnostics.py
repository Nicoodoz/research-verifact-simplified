"""Offline literal-equivalence, candidate-gate and corpus-availability diagnostics."""
from collections import defaultdict,Counter
from pathlib import Path
import statistics
import common as c
from build_stages import seal


def summarize():
    corpus=c.pilot.jsonl(c.OUT/"preparation_001/corpus.jsonl")
    passages={p["passage_id"]:p for p in corpus}
    inputs=c.pilot.jsonl(c.OUT/"preparation_001/inputs.jsonl")
    candidates={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"candidates_001/candidates.jsonl")}
    judge=c.pilot.jsonl(c.OUT/"judge_preparation_001/inputs.jsonl")
    transitions=c.pilot.read_csv(c.OUT/"run_001/analysis/transitions.csv")[1]
    notes=c.pilot.subset_csv(c.RAW/"reference_ehr/ehr_noteevents.csv.gz","SUBJECT_ID",set(c.PATIENTS))
    availability=[]
    for sid in c.PATIENTS:
        a=next(x["admission"] for x in inputs if x["subject_id"]==sid)
        within=[n for n in notes if c.pilot.integer_id(n["SUBJECT_ID"])==sid and a["ADMITTIME"][:10]<=n["CHARTDATE"][:10]<=a["DISCHTIME"][:10]]
        non_discharge=[n for n in within if n["CATEGORY"].strip().lower()!="discharge summary"]
        availability.append(dict(subject_id=sid,admit=a["ADMITTIME"],discharge=a["DISCHTIME"],
            all_in_scope_notes=len(within),non_discharge_notes=len(non_discharge),
            first_non_discharge_date=min(n["CHARTDATE"] for n in non_discharge),last_non_discharge_date=max(n["CHARTDATE"] for n in non_discharge),
            by_date_category=dict(Counter(n["CHARTDATE"][:10]+" | "+n["CATEGORY"] for n in within)),
            content_reading="Metadata only; later source events cannot be assumed documented"))
    def equivalent(key):
        p=passages[key]
        return p["date"],p["category"],p["text"]
    literal=[]
    for x in judge:
        original={equivalent(key) for key in x["retrieval"]["direct"]["selected_ids"]}
        original_pool={equivalent(key) for key in candidates[x["proposition_id"]]["candidate_ids"]["direct"]}
        for arm in c.METHODS:
            selected={equivalent(key) for key in x["retrieval"][arm]["selected_ids"]}
            ids=x["retrieval"][arm]["selected_ids"]
            literal.append(dict(case_id=x["case_id"],proposition_id=x["proposition_id"],method=arm,
                new_literal_blocks=len(selected-original),lost_literal_blocks=len(original-selected),
                new_literal_blocks_outside_direct_pool=len(selected-original_pool),
                selected_lt40_characters=sum(len(passages[key]["text"])<40 for key in ids),
                selected_characters=sum(len(passages[key]["text"]) for key in ids)))
    summary=dict(literal_equivalence="Same patient/date/category/exact text, matching selector dedup rule; not semantic or clinical equivalence",
        by_method={a:dict(cases_with_new_literal_evidence=sum(x["new_literal_blocks"]>0 for x in literal if x["method"]==a),
            cases_with_new_literal_evidence_outside_direct_pool=sum(x["new_literal_blocks_outside_direct_pool"]>0 for x in literal if x["method"]==a),
            mean_new_literal_blocks=statistics.mean(x["new_literal_blocks"] for x in literal if x["method"]==a),
            tiny_selected_blocks=sum(x["selected_lt40_characters"] for x in literal if x["method"]==a)) for a in c.METHODS},
        patient_correct_count_delta={author:{sid:sum((r["planner"]==r["human_gt"])-(r["direct"]==r["human_gt"]) for r in transitions if r["author_type"]==author and r["subject_id"]==sid) for sid in c.PATIENTS} for author in ("llm","human")},
        direct_zero_bm25_cases=[x["case_id"] for x in candidates.values() if not x["query_rankings"][0]["bm25"]],
        no_gold_evidence_recall_claim=True)
    anchors=c.read_json(c.OUT/"run_001/review_001/semantic_003/evidence_anchors.json")
    chosen={("P036","725366",9584),("P058","688853",632),("P076","497323",1267),("P080","498057",634),("P081","497323",635),("P128","653655",5774)}
    gates=[]
    for x in anchors:
        if x["kind"]!="ehr" or (x["case_id"],x["note_id"],x["passage_start"]) not in chosen:
            continue
        row={k:x[k] for k in ("case_id","note_id","passage_start","quote","direct_query_ranks","candidate_literal_equivalent_membership","selected_literal_equivalent_membership","selection_disposition")}
        row["offline_dense_only_top48_would_include_this_exact_passage"]=x["direct_query_ranks"]["dense"] is not None and x["direct_query_ranks"]["dense"]<=48
        row["not_an_alternative_Judge_experiment"]=True
        gates.append(row)
    out=c.OUT/"run_001/diagnostics_001"
    out.mkdir(parents=True,exist_ok=False)
    c.pilot.write_json(out/"summary.json",summary)
    c.pilot.write_json(out/"corpus_availability.json",availability)
    c.pilot.write_jsonl(out/"literal_evidence_changes.jsonl",literal)
    c.pilot.write_json(out/"case_candidate_gates.json",gates)
    seal(out,[c.OUT/"run_001/analysis/manifest.json",c.OUT/"run_001/review_001/semantic_003/manifest.json"],code_files=[Path(__file__)])
    print(c.pilot.canonical(summary))
    print(c.pilot.canonical([dict(subject_id=x["subject_id"],last_note=x["last_non_discharge_date"],discharge=x["discharge"]) for x in availability]))


if __name__=="__main__":
    summarize()
