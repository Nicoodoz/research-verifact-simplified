"""Read only claim/C48/EHR sources; never imports or opens GT or predictions."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = {
    "031": ("outputs/031_training_expansion_confirmation/materials_001/inputs.jsonl",
            "outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl",
            "outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl"),
    "020": ("outputs/020_lambda2_patient_validation/new10/preparation_002/inputs.jsonl",
            "outputs/020_lambda2_patient_validation/new10/candidates_001/candidates.jsonl",
            "outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl"),
    "016": ("outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/inputs.jsonl",
            "outputs/016_disagreement_triggered_review_validation/stage1/candidates_001/candidates.jsonl",
            "outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/corpus.jsonl"),
    "009": ("outputs/009_retrieval_baselines/confirmation_001/preparation/inputs.jsonl",
            "outputs/009_retrieval_baselines/confirmation_001/candidates/candidates.jsonl",
            "outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl"),
}


def lines(relative):
    return [json.loads(s) for s in (ROOT / relative).read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def main():
    target = lines("outputs/078_component_ablation/primary_blind.jsonl")
    target_patients = {str(x["sid"]) for x in target}
    print("078", len(target), "patients", len(target_patients), sorted(target_patients))
    all_candidates = {}
    all_sids = {}
    for source, (input_path, candidate_path, corpus_path) in SOURCE.items():
        inputs = lines(input_path)
        candidates = lines(candidate_path)
        corpus = lines(corpus_path)
        by_input = {str(x.get("proposition_id") or x.get("id")): x for x in inputs}
        eligible = {}
        for row in candidates:
            pid = str(row.get("proposition_id") or row.get("id"))
            ids = (row.get("candidate_ids") or {}).get("C48") or row.get("C48")
            item = by_input.get(pid)
            if ids and item and str(item.get("subject_id") or item.get("sid")) in target_patients:
                eligible[pid] = (item, ids)
                all_candidates.setdefault(pid, source)
                all_sids.setdefault(pid, str(item.get("subject_id") or item.get("sid")))
        by_patient = Counter(str(x[0].get("subject_id") or x[0].get("sid")) for x in eligible.values())
        print(source, "inputs", len(inputs), "candidate_rows", len(candidates), "corpus", len(corpus),
              "eligible", len(eligible), "patients", len(by_patient), "minmax", (min(by_patient.values()), max(by_patient.values())) if by_patient else None)
        print(" per_patient", sorted(by_patient.items()))
    print("union_eligible", len(all_candidates), "patients", len(set(all_sids.values())))
    references = {}
    for source_path in (
        "outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl",
        "outputs/031_training_expansion_confirmation/materials_001/cached_c48.jsonl",
        "outputs/052_first_tier_validation/sample_blind.jsonl",
        "outputs/053_thinking_prior_validation/sample_blind.jsonl",
        "outputs/078_component_ablation/primary_blind.jsonl",
    ):
        rows = lines(source_path)
        for row in rows:
            pid = str(row.get("proposition_id") or row.get("id"))
            ref = row.get("reference")
            if pid in all_candidates and ref:
                references.setdefault(pid, (source_path, ref))
        print("reference_source", source_path, "rows", len(rows),
              "covered_eligible_after_merge", len(references))
    cover = Counter(all_sids[pid] for pid in all_candidates if pid in references)
    print("eligible_with_reference", len(references), "patient_minmax", (min(cover.values()), max(cover.values())))
    primary_id = {x["id"] for x in target}
    print("eligible_not_primary", len(set(all_candidates)-primary_id), "eligible_new_with_reference", len((set(all_candidates)-primary_id) & set(references)))
    by_new = Counter(all_sids[pid] for pid in (set(all_candidates)-primary_id) & set(references))
    print("new_per_patient", sorted((sid, by_new[sid]) for sid in target_patients))


if __name__ == "__main__":
    main()
