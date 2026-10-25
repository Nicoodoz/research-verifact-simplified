"""Evaluate the pre-frozen equal-claim weighting sensitivity on identical IDs."""
from __future__ import annotations

import json

import inventory082 as i
import prepare082 as p
import run082 as r
import analyze082 as a
import model082 as m


def main():
    out = i.OUT
    freeze = r.read(out / "evaluation_apply_freeze.json")
    assert freeze["unweighted_models_frozen_sha256"] == p.sha(out / "unweighted_models_frozen_v2.json")
    models = r.read(out / "unweighted_models_frozen_v2.json")["models"]
    rows = i.lines("outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")
    for row in rows:
        supplied = {arm: row["arms"][arm]["scores"] if row["arms"][arm]["valid"]
                    else {lab: (100 if lab == "Not Addressed" else 0) for lab in m.LABELS}
                    for arm in ("B", "F4")}
        for view, model in models.items():
            labels = m.predict([supplied], model)[0]
            for j, arm in enumerate(("B", "F4")):
                name = "independent_" + view + "_equal_claim"
                row["methods"][arm][name] = (m.LABELS[int(labels[j])] if row["arms"][arm]["valid"]
                                               else row["fallback_label"])
    results = {}
    for name, subset in (("old352", [x for x in rows if x["cohort"] == "old352"]),
                         ("new180", [x for x in rows if x["cohort"] == "new180"]),
                         ("combined532", rows)):
        results[name] = {"metrics": [a.metric(subset, arm, method, bootstrap=False)
                                     for arm in ("B", "F4")
                                     for method in ("independent_R_equal_claim", "independent_E_equal_claim")],
                         "paired": [a.pair(subset, arm, "independent_" + view, arm,
                                            "independent_" + view + "_equal_claim")
                                    for arm in ("B", "F4") for view in ("R", "E")]}
    p.write("unweighted_sensitivity_results.json", {
        "status": "PRESPECIFIED_WEIGHTING_SENSITIVITY",
        "model_sha256": p.sha(out / "unweighted_models_frozen_v2.json"),
        "evaluation_predictions_sha256": p.sha(out / "evaluation_predictions.jsonl"),
        "cohorts": results,
    })
    print(json.dumps({name: [(x["config"], x["method"], x["correct"], x["false_S"])
                            for x in value["metrics"]] for name, value in results.items()}))


if __name__ == "__main__":
    main()
