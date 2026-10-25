"""Offline 072 freeze and request audit; no API calls."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/072_adaptive_judge_examples"
sys.path.insert(0, str(Path(__file__).parent))
import run072  # noqa: E402


def main():
    frozen = run072.check_frozen("pilot")
    pool = run072.lines(OUT / "example_pool.jsonl")
    blind = run072.lines(OUT / "target_blind.jsonl")
    gt = run072.lines(OUT / "target_gt.jsonl")
    jobs = run072.lines(OUT / "pilot_jobs.jsonl")
    selection = run072.lines(OUT / "dynamic_selections.jsonl")
    assert len(blind) == len(gt) == 96 and len(selection) == 36
    assert {x["id"] for x in blind} == {x["id"] for x in gt}
    assert {x["id"] for x in selection} == {x["id"] for x in blind if x["sid"] in frozen["pilot_patients"]}
    assert len(pool) == 12 and Counter(x["physician_label"] for x in pool) == {"Supported": 6, "Not Supported": 3, "Not Addressed": 3}
    assert not {x["sid"] for x in pool} & {x["sid"] for x in blind}
    assert len(jobs) == 144 and Counter(x["arm"] for x in jobs) == {"B": 36, "F4": 36, "S6": 36, "D4": 36}
    assert len({x["request_id"] for x in jobs}) == 144
    by = {(x["id"], x["arm"]): x for x in jobs}
    old = {(x["id"], x["arm"]): x for x in run072.lines(ROOT / "outputs/071_judge_icl_feasibility/main_jobs.jsonl")}
    for x in blind:
        if x["sid"] not in frozen["pilot_patients"]:
            continue
        pid = x["id"]
        assert by[(pid, "B")]["body"] == old[(pid, "B")]["body"]
        assert by[(pid, "F4")]["body"] == old[(pid, "E")]["body"]
        user = by[(pid, "B")]["body"]["messages"][-1]["content"]
        assert all(by[(pid, arm)]["body"]["messages"][-1]["content"] == user for arm in ("F4", "S6", "D4"))
        assert json.loads(user) == {"proposition": x["claim"], "reference": x["reference"]}
    for x in selection:
        chosen = x["selected"]
        assert len(chosen) == 4 and [z["label"] for z in chosen] == ["Supported", "Not Supported", "Supported", "Not Addressed"]
        assert len({z["sid"] for z in chosen}) == 4
        assert all(z["near_duplicate_ratio"] < 0.85 for z in chosen)
    projection = {arm: round(sum(run072.bound(x["body"]) for x in jobs if x["arm"] == arm), 6) for arm in ("B", "F4", "S6", "D4")}
    result = {"status": "PASS", "freeze_sha256": run072.sha(OUT / "freeze.json"),
              "pilot_patients": frozen["pilot_patients"], "confirmation_patients": frozen["confirmation_patients"],
              "pilot_n": frozen["pilot_n"], "confirmation_n": frozen["confirmation_n"],
              "pilot_jobs": len(jobs), "pool_label_counts": frozen["example_label_counts"],
              "all_pilot_request_upper_bound_cny": round(sum(projection.values()), 6),
              "upper_bound_by_arm_cny": projection,
              "expected_actual_cost_note": "Upper bound reserves max_tokens for every request; actual usage expected much lower."}
    with (OUT / "input_verification.json").open("x", encoding="utf-8", newline="\n") as target:
        json.dump(result, target, ensure_ascii=False, indent=2)
        target.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
