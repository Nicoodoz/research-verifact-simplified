"""Freeze prespecified equal-claim weighting sensitivity before evaluation GT."""
from __future__ import annotations

import inventory082 as i
import prepare082 as p
import run082 as r
import model082 as m
import numpy as np
from unittest.mock import patch


def main():
    out = i.OUT
    frozen = r.read(out / "models_frozen.json")
    selection = r.read(out / "training_selection.json")
    effective = r.read(out / "training_effective.json")
    pair = {x["id"]: x for x in i.lines("outputs/082_anchor_configuration_adaptation/training_pairs.jsonl")}
    lam = selection["chosen_by_family"]["independent"]["regularization"]
    with patch.object(m, "patient_weights", side_effect=lambda rows: np.full(len(rows), 1 / len(rows))):
        models = {view: m.fit([pair[pid] for pid in effective[f"{view}_ids"]],
                              "independent", lam) for view in ("R", "E")}
    for value in models.values():
        value["weight_rule"] = "equal weight per independent claim; paired B/F4 loss averaged per claim"
    p.write("unweighted_models_frozen_v2.json", {
        "status": "PRESPECIFIED_EQUAL_CLAIM_SENSITIVITY_FROZEN_BEFORE_EVALUATION_GT",
        "primary_model_sha256": p.sha(out / "models_frozen.json"),
        "evaluation_GT_used": False,
        "regularization": lam,
        "models": models,
    })
    print({"R": models["R"]["n_labels"], "E": models["E"]["n_labels"],
           "regularization": lam})


if __name__ == "__main__":
    main()
