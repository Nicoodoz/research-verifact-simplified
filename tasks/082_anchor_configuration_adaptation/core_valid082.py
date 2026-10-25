"""Common B/F4 core-valid sensitivity; complete fallback analysis stays primary."""
from __future__ import annotations

import json

import inventory082 as i
import prepare082 as p
import analyze082 as a


def main():
    rows = i.lines("outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")
    groups = {"old352": [x for x in rows if x["cohort"] == "old352"],
              "new180": [x for x in rows if x["cohort"] == "new180"],
              "combined532": rows}
    result = {}
    for name, full in groups.items():
        subset = [x for x in full if x["arms"]["B"]["valid"] and x["arms"]["F4"]["valid"]]
        methods = [("B", "PriorG"), ("F4", "PriorG"),
                   ("F4", "independent_R"), ("F4", "shared_R"), ("F4", "adapted_R")]
        comparisons = [("B", "PriorG", "F4", "PriorG"),
                       ("B", "PriorG", "F4", "adapted_R"),
                       ("F4", "independent_R", "F4", "adapted_R")]
        result[name] = {"full_n": len(full), "common_valid_n": len(subset),
                        "excluded_ids": [x["id"] for x in full if x not in subset],
                        "metrics": [a.metric(subset, arm, method, bootstrap=False) for arm, method in methods],
                        "paired": [a.pair(subset, *q) for q in comparisons]}
    p.write("common_core_valid_sensitivity.json", {
        "status": "SENSITIVITY_ONLY_COMPLETE_FALLBACK_PRIMARY",
        "groups": result,
    })
    print(json.dumps({name: {"n": value["common_valid_n"], "excluded": len(value["excluded_ids"])}
                      for name, value in result.items()}))


if __name__ == "__main__":
    main()
