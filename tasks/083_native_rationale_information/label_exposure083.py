"""Summarize label access and historical exposure without adding training patients."""
from __future__ import annotations

import json
from collections import Counter

import inventory083 as base

ROOT, OUT = base.ROOT, base.OUT


def main():
    quality = base.read(OUT / "native_quality.json")
    train = base.lines("outputs/083_native_rationale_information/train_labels.jsonl")
    patients = set(quality["training_patients"])
    all_ref = base.lines("outputs/080_final_decision_adaptation/reference_prior_rows.jsonl")
    reference = [x for x in all_ref if x["sid"] in patients]
    assert len(reference) == 1218
    sample = {x["id"] for x in train}
    source = {x["id"] for x in reference}
    assert sample <= source and len(sample) == 459
    assert all(x["sid"] in patients for x in train)
    assert not patients & set(quality["evaluation_patients"])
    expo = base.read(ROOT / "outputs/082_anchor_configuration_adaptation/exposure_audit.json")
    out = {"source_labels_read": len(reference),
           "source_patients": len(patients),
           "source_GT": dict(Counter(x["GT"] for x in reference)),
           "fitted_independent_labels": len(sample),
           "fitted_GT": dict(Counter(x["GT"] for x in train)),
           "fitted_sources": dict(Counter(x["source"] for x in train)),
           "all_fit_IDs_already_in_source": True,
           "B_F4_share_same_label_per_claim": True,
           "evaluation_patients": len(quality["evaluation_patients"]),
           "evaluation_GT_not_used_in_training": True,
           "example_patients_excluded": quality["example_patients"],
           "full_teaching_candidate_pool_overlap_train14": expo["candidate_pool_overlap_train14"],
           "full_teaching_candidate_pool_overlap_eval22": expo["candidate_pool_overlap_eval22"],
           "new180_prior_blind_exposure_n": len(expo["new_eval_any_historical_blind"]),
           "old352_historically_exposed": True,
           "source_reference_sha256": base.digest((ROOT / "outputs/080_final_decision_adaptation/reference_prior_rows.jsonl").read_bytes()),
           "train_labels_sha256": base.digest((OUT / "train_labels.jsonl").read_bytes()),
           "exposure_source_sha256": base.digest((ROOT / "outputs/082_anchor_configuration_adaptation/exposure_audit.json").read_bytes())}
    base.write("label_exposure_ledger.json", out)
    print(json.dumps({k:out[k] for k in ("source_labels_read","fitted_independent_labels",
                                         "new180_prior_blind_exposure_n","evaluation_patients")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
