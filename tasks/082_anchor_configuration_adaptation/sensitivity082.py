"""Predefined historical teaching-pool isolation and new-eval exposure sensitivities."""
from __future__ import annotations

import json

import inventory082 as i
import prepare082 as p
import analyze082 as a

ROOT, OUT = i.ROOT, i.OUT


def main():
    rows = i.lines("outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")
    pool = set(json.loads((ROOT / "outputs/078_component_ablation/f4_extension_001/cohort_lists.json").read_text(encoding="utf-8"))["original_pool_isolated128"])
    exposed = set(json.loads((OUT / "exposure_audit.json").read_text(encoding="utf-8"))["new_eval_any_historical_blind"])
    candidate_pool = set(json.loads((ROOT / "outputs/071_judge_icl_feasibility/freeze.json").read_text(encoding="utf-8"))["training_patients"])
    groups = {"old_pool_isolated128": [x for x in rows if x["id"] in pool],
              "new180_without_known_prior_blind_exposure": [x for x in rows if x["cohort"] == "new180" and x["id"] not in exposed],
              "new180_candidate_pool_patient_isolated": [x for x in rows if x["cohort"] == "new180" and x["sid"] not in candidate_pool]}
    assert len(groups["old_pool_isolated128"]) == 128
    result = {}
    for name, subset in groups.items():
        result[name] = {"n": len(subset), "patients": len({x["sid"] for x in subset}),
                        "GT": {lab: sum(x["GT"] == lab for x in subset) for lab in a.m.LABELS},
                        "metrics": [a.metric(subset, config, method)
                                    for config in ("B", "F4") for method in ("PriorG", "independent_R", "adapted_R", "selected_R")],
                        "pairs": [a.pair(subset, *args) for args in (("B", "PriorG", "F4", "PriorG"),
                                                                      ("B", "independent_R", "F4", "independent_R"),
                                                                      ("F4", "independent_R", "F4", "adapted_R"),
                                                                      ("B", "PriorG", "F4", "selected_R"))],
                        "ids": [x["id"] for x in subset]}
    p.write("sensitivity_results.json", {"status": "PRESPECIFIED_HISTORICAL_EXPOSURE_DESCRIPTIVE",
                                         "groups": result,
                                         "main_results_unchanged": True})
    print(json.dumps({name: {"n": x["n"], "patients": x["patients"]} for name, x in result.items()}))


if __name__ == "__main__":
    main()
