"""Account for unique doctor labels across old prior, sampling, fitting, and evaluation."""
from __future__ import annotations

import json

import inventory082 as i
import prepare082 as p
import run082 as r

ROOT, OUT = i.ROOT, i.OUT


def main():
    screen = {x["id"] for x in i.lines("outputs/082_anchor_configuration_adaptation/train_labels_accessed.jsonl")}
    old114 = {x["id"] for x in i.lines(i.OLD_TRAIN)}
    reference = {x["id"] for x in i.lines("outputs/080_final_decision_adaptation/reference_prior_rows.jsonl")}
    folds = r.read(OUT / "fold_prior_baselines.json")["folds"]
    original_g = set().union(*(set(x["training_ids"]) for x in folds.values()))
    views = r.read(OUT / "training_effective.json")
    fitted = set(views["R_ids"]) | set(views["E_ids"]) | set(views["old112_ids"])
    assert len(screen) == 420 and len(old114) == 114 and len(reference) == 1378
    assert screen <= reference and old114 <= reference and original_g <= reference
    assert fitted <= screen | old114
    assert not set(views["R_ids"]) & old114
    p.write("label_use_ledger.json", {"new_screen_training_GT_accessed": len(screen),
                                     "old_079_view_GT_accessed": len(old114),
                                     "screen_and_old_deduplicated": len(screen | old114),
                                     "historical_053_reference_prior_GT_rows": len(reference),
                                     "historical_051_G_training_GT": len(original_g),
                                     "new_fitted_R_GT": len(views["R_ids"]),
                                     "new_fitted_E_GT": len(views["E_ids"]),
                                     "fitted_R_E_old112_deduplicated": len(fitted),
                                     "all_calibration_side_GT_accessed_deduplicated": len(screen | old114 | reference | original_g),
                                     "all_new_082_supervised_IDs_already_in_historical_reference_prior": True,
                                     "B_F4_pair_scores_share_one_doctor_label_per_claim": True,
                                     "evaluation_GT_not_read": True,
                                     "set_sha256": {"screen": p.digest(sorted(screen)), "old114": p.digest(sorted(old114)),
                                                    "reference": p.digest(sorted(reference)),
                                                    "fitted": p.digest(sorted(fitted))}})
    print(json.dumps({"screen": len(screen), "old114": len(old114),
                      "historical_reference": len(reference), "fitted_unique": len(fitted),
                      "all_calibration_side_unique": len(screen | old114 | reference | original_g)}))


if __name__ == "__main__":
    main()
