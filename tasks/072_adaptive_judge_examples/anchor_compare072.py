"""Descriptive same-body 071→072 drift for shared B and F4; offline only."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/072_adaptive_judge_examples"
OLD = ROOT / "outputs/071_judge_icl_feasibility"


def lines(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def main():
    old = {(x["id"], x["arm"]): x for x in lines(OLD / "stage1_predictions.jsonl")}
    new = {(x["id"], x["arm"]): x for stage in ("pilot", "confirmation") for x in lines(OUT / f"{stage}_predictions.jsonl")}
    gt = {x["id"]: x["GT"] for x in lines(OUT / "target_gt.jsonl")}
    assert len(gt) == 96
    result = {"n": 96, "arms": {}}
    for current_arm, previous_arm in (("B", "B"), ("F4", "E")):
        changes = [pid for pid in gt if old[(pid, previous_arm)]["PriorG"] != new[(pid, current_arm)]["PriorG"]]
        rescue = [pid for pid in gt if old[(pid, previous_arm)]["PriorG"] != gt[pid] and new[(pid, current_arm)]["PriorG"] == gt[pid]]
        harm = [pid for pid in gt if old[(pid, previous_arm)]["PriorG"] == gt[pid] and new[(pid, current_arm)]["PriorG"] != gt[pid]]
        result["arms"][current_arm] = {"071_correct": sum(old[(pid, previous_arm)]["PriorG"] == gt[pid] for pid in gt),
                                       "072_correct": sum(new[(pid, current_arm)]["PriorG"] == gt[pid] for pid in gt),
                                       "same_body_label_changes": len(changes), "changed_ids": changes,
                                       "rescue": len(rescue), "harm": len(harm), "net": len(rescue)-len(harm)}
    result["071_F4_minus_B_net"] = result["arms"]["F4"]["071_correct"] - result["arms"]["B"]["071_correct"]
    result["072_F4_minus_B_net"] = result["arms"]["F4"]["072_correct"] - result["arms"]["B"]["072_correct"]
    with (OUT / "anchor_071_072_comparison.json").open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
