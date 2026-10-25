"""Aggregate descriptive counts, without adding another metric implementation."""
from collections import Counter
import json
import statistics
import prepare as p
from retrieval import ARMS

run=p.OUT/"run_001"
rows=p.pilot.read_csv(run/"analysis/transitions.csv")[1]
diag=p.pilot.read_csv(run/"analysis/retrieval_diagnostics.csv")[1]
inputs={r["proposition_id"]:r for r in p.pilot.jsonl(p.OUT/"preparation_003/inputs.jsonl")}
result={"by_patient_author":[],"evidence_proxies":{},"repeated_baseline":[],"primary_changed_cases":[],"budget_matching_zero_cases":[]}
for sid in sorted({r["subject_id"] for r in rows}):
    for author in ("llm","human"):
        own=[r for r in rows if r["subject_id"]==sid and r["author_type"]==author]
        result["by_patient_author"].append(dict(subject_id=sid,author_type=author,n=len(own),
            correct_counts={a:sum(r[a]==r["human_gt"] for r in own) for a in ARMS}))
for a in ARMS:
    own=[r for r in diag if r["arm"]==a]
    result["evidence_proxies"][a]=dict(mean_reference_chars=statistics.mean(int(r["reference_chars"]) for r in own),
        mean_passages=statistics.mean(int(r["passage_count"]) for r in own),
        mean_passage_id_jaccard_to_claim=statistics.mean(float(r["jaccard_passage_ids_with_claim"]) for r in own),
        passages_without_literal_claim_terms=sum(int(r["passages_without_literal_claim_terms"]) for r in own),
        total_passages=sum(int(r["passage_count"]) for r in own),
        not_clinical_relevance_precision=True)
for row in rows:
    pid=row["proposition_id"]
    if row["claim_repeat"]:
        result["repeated_baseline"].append(dict(case_id=row["case_id"],claim=row["claim"],repeat=row["claim_repeat"],equal=row["claim"]==row["claim_repeat"]))
    if row["claim"]!=row["mixed"]:
        result["primary_changed_cases"].append(dict(case_id=row["case_id"],author_type=row["author_type"],human_gt=row["human_gt"],
            claim=row["claim"],mixed=row["mixed"],same_reference=inputs[pid]["retrieval"]["claim"]["reference_id"]==inputs[pid]["retrieval"]["mixed"]["reference_id"]))
    if inputs[pid]["retrieval"]["claim"]["matched_character_budget"]==0:
        result["budget_matching_zero_cases"].append(row["case_id"])
supp=p.pilot.jsonl(p.OUT/"zero_budget_sensitivity_001/normalized_responses.jsonl")
result["zero_budget_sensitivity"]=[dict(case_id=row["case_id"],human_gt=row["human_gt"],
    verdicts={x["arm"]:x["verdict"] for x in supp if x["proposition_id"]==row["proposition_id"]}) for row in rows if row["case_id"] in result["budget_matching_zero_cases"]]
result["task_total_estimated_cny"]=json.loads((p.OUT/"zero_budget_sensitivity_001/summary.json").read_text(encoding="utf-8"))["task_cumulative_used_or_reserved_cny"]
target=run/"diagnostic_summary.json"
assert not target.exists()
p.pilot.write_json(target,result)
print(p.pilot.canonical(result))
