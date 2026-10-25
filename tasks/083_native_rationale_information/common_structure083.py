"""Descriptive shared score-and-grounded-structure coverage sensitivity."""
import json

import inventory083 as base
import evaluate083 as ev


def main():
    full = base.lines("outputs/083_native_rationale_information/evaluation_predictions.jsonl")
    subset = [x for x in full if x["f4_core_valid"] and x["structured_accepted"] > 0]
    assert len(full) == 532 and len(subset) == 523
    methods = ("F4_FrozenPriorG", "N", "C", "T", "G", "R")
    base.write("common_structure_valid_sensitivity.json", {
        "status": "DESCRIPTIVE_ONLY_FULL_532_PRIMARY",
        "n": len(subset), "patients": len({x["sid"] for x in subset}),
        "excluded_ids": [x["id"] for x in full if x not in subset],
        "metrics": [ev.metric(subset, x) for x in methods],
        "paired": [ev.pair(subset, x, "R") for x in ("N", "G", "F4_FrozenPriorG")],
    })
    print(json.dumps({"n":len(subset),"results":[(x, sum(y["predictions"][x]==y["GT"] for y in subset)) for x in methods]}))


if __name__ == "__main__":
    main()
