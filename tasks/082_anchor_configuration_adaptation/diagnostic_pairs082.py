"""Post-evaluation descriptive pairs among the pre-frozen methods; no selection."""
from __future__ import annotations

import json
from collections import Counter

import inventory082 as i
import prepare082 as p
import analyze082 as a


def main():
    records = i.lines("outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")
    specs = [("F4", "PriorG", "F4", "adapted_R"),
             ("B", "PriorG", "B", "adapted_R"),
             ("B", "PriorG", "F4", "independent_R"),
             ("B", "PriorG", "F4", "independent_E")]
    result = {}
    for name, rows in (("old352", [x for x in records if x["cohort"] == "old352"]),
                       ("new180", [x for x in records if x["cohort"] == "new180"]),
                       ("combined532", records)):
        result[name] = [a.pair(rows, *q) for q in specs]
    transitions = {}
    for config in ("B", "F4"):
        transitions[config] = dict(Counter(
            (x["methods"][config]["PriorG"], x["methods"][config]["adapted_R"], x["GT"])
            for x in records if x["methods"][config]["PriorG"] != x["methods"][config]["adapted_R"]))
    serial = {arm: [{"from": k[0], "to": k[1], "GT": k[2], "n": n}
                     for k, n in sorted(group.items())] for arm, group in transitions.items()}
    p.write("diagnostic_pairs.json", {"status": "POSTHOC_DESCRIPTIVE_PRE_FROZEN_METHODS",
                                      "pairs": result, "priorg_to_adapted_transitions": serial})
    print(json.dumps({name: [(x["base"], x["candidate"], x["net"], x["delta_false_S"],
                              x["patient_wins"], x["patient_losses"], x["metrics"]["mcc"]["delta"])
                             for x in pairs] for name, pairs in result.items()}))


if __name__ == "__main__":
    main()
