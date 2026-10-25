"""Separate adaptive selections from accidental exact-body repeat variation."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/072_adaptive_judge_examples"
sys.path.insert(0, str(Path(__file__).parent))
import run072  # noqa: E402


def main(stage):
    assert stage in ("pilot", "confirmation")
    jobs = {(x["id"], x["arm"]): x for x in run072.lines(OUT / f"{stage}_jobs.jsonl")}
    predictions = {(x["id"], x["arm"]): x for x in run072.lines(OUT / f"{stage}_predictions.jsonl")}
    gt = {x["id"]: x["GT"] for x in run072.lines(OUT / "target_gt.jsonl")}
    ids = sorted({pid for pid, arm in jobs if arm == "D4"})
    result = {"stage": stage, "groups": {}}
    rows = []
    for pid in ids:
        same = jobs[(pid, "D4")]["body_sha256"] == jobs[(pid, "F4")]["body_sha256"]
        d = predictions[(pid, "D4")]
        f = predictions[(pid, "F4")]
        rows.append({"id": pid, "sid": d["sid"], "same_body": same, "GT": gt[pid],
                     "D4_raw": d["raw"], "F4_raw": f["raw"], "D4_PriorG": d["PriorG"], "F4_PriorG": f["PriorG"],
                     "correct_delta": int(d["PriorG"] == gt[pid]) - int(f["PriorG"] == gt[pid]),
                     "raw_correct_delta": int(d["raw"] == gt[pid]) - int(f["raw"] == gt[pid]) if d["raw"] and f["raw"] else None})
    for same in (True, False):
        selected = [x for x in rows if x["same_body"] == same]
        result["groups"]["exact_same_body" if same else "changed_example_body"] = {
            "n": len(selected), "PriorG_label_disagreements": sum(x["D4_PriorG"] != x["F4_PriorG"] for x in selected),
            "PriorG_net_D4_minus_F4": sum(x["correct_delta"] for x in selected),
            "raw_label_disagreements": sum(x["D4_raw"] != x["F4_raw"] for x in selected),
            "raw_net_D4_minus_F4_on_common_valid": sum(x["raw_correct_delta"] for x in selected if x["raw_correct_delta"] is not None),
            "GT_counts": dict(Counter(x["GT"] for x in selected)),
            "changed_ids": [x["id"] for x in selected if x["D4_PriorG"] != x["F4_PriorG"]],
        }
    with (OUT / f"{stage}_same_body_sensitivity.json").open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
