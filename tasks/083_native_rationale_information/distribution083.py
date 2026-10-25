"""Describe nonempty extracted categories without using evaluation GT."""
from __future__ import annotations

from collections import Counter

import inventory083 as base


def main():
    rows = base.lines("outputs/083_native_rationale_information/structured_arguments.jsonl")
    result = {}
    for phase in ("train", "old352", "new180", "repeat"):
        arguments = [a for row in rows if row["phase"] == phase for a in row["accepted"]]
        result[phase] = {field: dict(Counter(arg[field] for arg in arguments))
                         for field in ("stance", "basis", "dimension")}
    base.write("structured_distribution.json", {"status": "GT_BLIND_DESCRIPTIVE_COUNTS", "by_phase": result})
    print({phase: {k: len(v) for k,v in value.items()} for phase,value in result.items()})


if __name__ == "__main__":
    main()
