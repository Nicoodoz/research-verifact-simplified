"""Read-only output-interface diagnostics; never changes accepted queries or predictions."""
from collections import Counter
import json
import re
import common as c
from build_stages import seal


def compact(s):
    return " ".join(s.split())


def diagnose():
    inputs={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"preparation_001/inputs.jsonl")}
    plans=c.pilot.jsonl(c.OUT/"plans_001/plans.jsonl")
    rows=[]
    for x in plans:
        raw=json.loads(x["output_text"])
        item=inputs[x["proposition_id"]]
        source=item["source"]["local"]
        expected={"evidence_needs","source_clues","terminology","queries","uncertainties"}
        clues=[]
        for s in raw.get("source_clues",[]):
            if not isinstance(s,dict):
                clues.append(dict(invalid_type=True))
                continue
            quote=s.get("quote")
            clues.append(dict(keys=sorted(s),exact_schema=set(s)=={"quote","use"},quote=quote,
                exact_literal=isinstance(quote,str) and quote in source,
                whitespace_normalized_literal=isinstance(quote,str) and compact(quote) in compact(source)))
        raw_queries=raw.get("queries",[])
        claim_nums=set(re.findall(r"\d+(?:\.\d+)?",item["text"]))
        source_nums=set(re.findall(r"\d+(?:\.\d+)?",source))
        query_nums=set(re.findall(r"\d+(?:\.\d+)?"," ".join(raw_queries))) if isinstance(raw_queries,list) and all(isinstance(q,str) for q in raw_queries) else set()
        rows.append(dict(case_id=x["case_id"],proposition_id=x["proposition_id"],status=x["status"],error=x["error"],
            top_level_missing=sorted(expected-set(raw)),top_level_extra=sorted(set(raw)-expected),
            needs_count=len(raw.get("evidence_needs",[])),clues=clues,
            has_nonliteral_quote=any(not s.get("exact_literal",False) for s in clues),
            has_quote_difference_beyond_whitespace=any(not s.get("whitespace_normalized_literal",False) for s in clues),
            has_clue_schema_deviation=any(not s.get("exact_schema",False) for s in clues),
            raw_query_count=len(raw_queries),used_query_count=len(x["queries"]),
            raw_queries_source_only_numbers=sorted((query_nums-claim_nums)&source_nums),raw_queries_numbers_in_neither=sorted(query_nums-claim_nums-source_nums)))
    failed=[x for x in rows if x["status"]=="fallback_direct"]
    quote_failed=[x for x in failed if x["error"]=="Unverifiable source quote"]
    summary=dict(all=144,accepted=100,fallback=len(failed),primary_error_counts=dict(Counter(x["error"] for x in failed)),
        quote_validator_failed_cases=len(quote_failed),quote_validator_schema_only=sum(x["has_clue_schema_deviation"] and not x["has_nonliteral_quote"] for x in quote_failed),
        quote_validator_whitespace_only=sum(not x["has_clue_schema_deviation"] and x["has_nonliteral_quote"] and not x["has_quote_difference_beyond_whitespace"] for x in quote_failed),
        quote_validator_other_or_combined=sum(not(x["has_clue_schema_deviation"] and not x["has_nonliteral_quote"]) and not(not x["has_clue_schema_deviation"] and x["has_nonliteral_quote"] and not x["has_quote_difference_beyond_whitespace"]) for x in quote_failed),
        source_number_flags_used_cases=[x["case_id"] for x in rows if x["used_query_count"] and x["raw_queries_source_only_numbers"]],
        novel_number_flags_used_cases=[x["case_id"] for x in rows if x["used_query_count"] and x["raw_queries_numbers_in_neither"]],
        all_raw_have_two_queries=sum(x["raw_query_count"]==2 for x in rows),
        execution_semantic_review_not_medical_ground_truth=True,no_queries_repaired_or_resent=True)
    out=c.OUT/"planner_diagnostics_001"
    out.mkdir(parents=True,exist_ok=False)
    c.pilot.write_jsonl(out/"cases.jsonl",rows)
    c.pilot.write_json(out/"summary.json",summary)
    c.pilot.write_json(out/"early_reading.json",dict(case_ids=["P007","P009","P010"],selection="First returned validation-error examples; read before Judge labels",scope="Full source and planner output only, for parser failure interpretation"))
    seal(out,[c.OUT/"plans_001/manifest.json"],code_files=[c.TASK/"planner_diagnostics.py"])
    print(c.pilot.canonical(summary))


if __name__=="__main__":
    diagnose()
