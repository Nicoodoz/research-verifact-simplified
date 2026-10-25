"""Bind native text, extraction, models, permutation and evaluation IDs before GT join."""
from __future__ import annotations

import json
from pathlib import Path

import inventory083 as base
import run083 as runner

ROOT, OUT = base.ROOT, base.OUT


def main():
    model = base.read(OUT / "models_frozen.json")
    assert model["status"] == "MODELS_FROZEN_BEFORE_083_EVALUATION_GT"
    assert model["evaluation_GT_read"] is False
    assert model["model_joblib_sha256"] == base.digest((OUT / "models_frozen.joblib").read_bytes())
    assert model["structured_arguments_sha256"] == base.digest((OUT / "structured_arguments.jsonl").read_bytes())
    attempts, answered = runner.state()
    assert len(answered) == len(runner.jobs()) == 1015
    old = base.lines("outputs/079_f4_priorg_adaptation/evaluation_blind.jsonl")
    new = base.lines("outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl")
    train = base.lines("outputs/083_native_rationale_information/train_labels.jsonl")
    repeated = base.lines("outputs/082_anchor_configuration_adaptation/repeat_blind.jsonl")
    ids = [x["id"] for x in old + new]
    assert len(old) == 352 and len(new) == 180 and len(set(ids)) == 532
    assert len(train) == len({x["id"] for x in train}) == 459
    assert not {x["sid"] for x in old + new} & {x["sid"] for x in train}
    assert len(repeated) == 24 and {x["id"] for x in repeated} <= set(ids)
    extraction = base.lines("outputs/083_native_rationale_information/structured_arguments.jsonl")
    assert len(extraction) == 1015
    assert {x["id"] for x in extraction if x["phase"] in ("old352", "new180")} == set(ids)
    perm = base.read(OUT / "permutation_frozen.json")
    assert perm["evaluation_GT_read"] is False and set(perm["mapping"]) == set(ids)
    assert sum(x["original_price_cny"] for x in attempts) <= 20
    base.write("evaluation_apply_freeze.json", {
        "status": "FROZEN_BEFORE_083_EVALUATION_GT_JOIN",
        "evaluation_GT_read": False,
        "models_sha256": base.digest((OUT / "models_frozen.json").read_bytes()),
        "model_joblib_sha256": base.digest((OUT / "models_frozen.joblib").read_bytes()),
        "structured_arguments_sha256": base.digest((OUT / "structured_arguments.jsonl").read_bytes()),
        "feature_code_sha256": base.digest((ROOT / "tasks/083_native_rationale_information/features083.py").read_bytes()),
        "permutation_sha256": base.digest((OUT / "permutation_frozen.json").read_bytes()),
        "old_blind_sha256": base.digest((ROOT / "outputs/079_f4_priorg_adaptation/evaluation_blind.jsonl").read_bytes()),
        "new_blind_sha256": base.digest((ROOT / "outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl").read_bytes()),
        "evaluation_ids": ids,
        "repeat_ids": [x["id"] for x in repeated],
        "methods": ["F4_raw", "F4_U0", "F4_U2", "F4_FrozenPriorG", "B_FrozenPriorG",
                    "N", "C", "T", "G", "R", "P_aux", "R_permuted"],
        "primary_method": "R", "primary_comparisons": ["N", "C", "G", "T", "F4_FrozenPriorG"],
        "new_charged_attempts": len(attempts),
        "original_price_at_freeze_cny": sum(x["original_price_cny"] for x in attempts),
    })
    print(json.dumps({"evaluation_n": len(ids), "repeat_n": len(repeated),
                      "extractions": len(answered),
                      "cost_cny": round(sum(x["original_price_cny"] for x in attempts), 6)}))


if __name__ == "__main__":
    main()
