"""Freeze complete evaluation inputs and fitted models before joining evaluation GT."""
from __future__ import annotations

import json

import inventory082 as i
import prepare082 as p
import run082 as r

ROOT, OUT = i.ROOT, i.OUT


def main():
    models = r.read(OUT / "models_frozen.json")
    assert models["status"] == "FROZEN_BEFORE_082_EVALUATION_GT" and models["evaluation_GT_used"] is False
    unweighted = r.read(OUT / "unweighted_models_frozen_v2.json")
    assert unweighted["evaluation_GT_used"] is False
    assert unweighted["primary_model_sha256"] == p.sha(OUT / "models_frozen.json")
    jobs = r.jobs("eval")
    attempts, answers = r.answers("eval")
    assert len(jobs) == len(answers) == 360
    blind = i.lines("outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl")
    old = i.lines(i.OLD_EVAL)
    assert len(blind) == 180 and len(old) == 352
    assert {x["id"] for x in blind}.isdisjoint({x["id"] for x in old})
    assert {x["sid"] for x in blind} <= set(r.read(OUT / "blind_freeze.json")["eval_patients"])
    assert not ({x["sid"] for x in old + blind} & set(r.read(OUT / "blind_freeze.json")["train_patients"]))
    assert sum(x["original_price_cny"] for x in attempts) <= 50
    p.write("evaluation_apply_freeze.json", {"status": "ALL_MODELS_AND_OLD_NEW_EVALUATION_INPUTS_FROZEN_BEFORE_GT",
                                             "models_frozen_sha256": p.sha(OUT / "models_frozen.json"),
                                             "unweighted_models_frozen_sha256": p.sha(OUT / "unweighted_models_frozen_v2.json"),
                                             "training_selection_sha256": p.sha(OUT / "training_selection.json"),
                                             "training_pairs_sha256": p.sha(OUT / "training_pairs.jsonl"),
                                             "eval_new_blind_sha256": p.sha(OUT / "eval_new_blind.jsonl"),
                                             "old_eval_blind_sha256": p.sha(ROOT / i.OLD_EVAL),
                                             "eval_jobs_sha256": p.sha(OUT / "eval_jobs.jsonl"),
                                             "new_eval_ids": [x["id"] for x in blind],
                                             "old_eval_ids": [x["id"] for x in old],
                                             "planned_methods": ["Original", "raw", "U0", "U2", "FrozenPriorG",
                                                                 "independent_R", "shared_R", "adapted_R", "selected_R",
                                                                 "independent_E", "independent_old112", "independent_curve"],
                                             "new_eval_n": 180, "old_eval_n": 352,
                                             "new_eval_patients": len({x["sid"] for x in blind}),
                                             "old_eval_patients": len({x["sid"] for x in old}),
                                             "combined_n": 532, "combined_patients": 22,
                                             "evaluation_GT_not_read": True})
    print("532 evaluation IDs and all models frozen before GT join")


if __name__ == "__main__":
    main()
