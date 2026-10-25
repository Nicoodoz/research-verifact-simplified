"""Post-hoc class coverage: include every changed original-NS claim, both gains/losses."""
import study009 as s

if __name__=="__main__":
    folder=s.OUT/"confirmation_001"
    original=s.pilot.jsonl(folder/"review_001/packets.jsonl")
    ids={p["row"]["proposition_id"] for p in original}
    rows=s.pilot.read_csv(folder/"analysis_001/transitions.csv")[1]
    extra=[r for r in rows if r["human_gt"]=="Not Supported" and (r["A48"]!=r["B48"] or r["A48"]!=r["C48"]) and r["proposition_id"] not in ids]
    inputs={r["proposition_id"]:r for r in s.pilot.jsonl(folder/"judge_preparation/inputs.jsonl")}
    outputs={r["request_id"]:r for r in s.pilot.jsonl(folder/"analysis_001/normalized_responses.jsonl")}
    corpus={r["passage_id"]:r for r in s.pilot.jsonl(folder/"preparation/corpus.jsonl")}
    for r in extra:
        item=inputs[r["proposition_id"]]
        keys={k for a in ("A48","B48","C48") for k in item["retrieval"][a]["selected_ids"]}
        original.append(dict(row=r,input=item,reasons=["posthoc_all_original_NS_label_changes_for_class_coverage"],
            outputs={a:outputs[item["retrieval"][a]["request_id"]] for a in ("A48","B48","C48")},passages={k:corpus[k] for k in sorted(keys)}))
    original.sort(key=lambda p:p["row"]["case_id"])
    out=folder/"review_002"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/"packets.jsonl",original)
    s.pilot.write_json(out/"selection.json",dict(initial_cases=27,additional_case_ids=[r["case_id"] for r in extra],total_cases=len(original),
        posthoc=True,reason="Initial fixed-hash sample contained no original-NS claims. Add all such changed cases, not only improvements; no new predictions or primary-metric changes.",api_calls=0))
    s.seal(out,[folder/"review_001/manifest.json",folder/"analysis_001/manifest.json"],[s.TASK/"extend_review009.py"])
    print(s.pilot.canonical(s.read_json(out/"selection.json")))
