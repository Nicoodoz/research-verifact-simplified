"""Confirm frozen 072 holdout requests are GT-blind and source aligned."""
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
    frozen = run072.check_frozen("confirmation")
    selected = run072.read(OUT / "pilot_decision.json")
    assert selected["selected_arm"] == "D4" and selected["confirmation_not_inspected"] is True
    assert selected["pilot_analysis_sha256"] == run072.sha(OUT / "pilot_analysis.json")
    jobs = run072.jobs_for("confirmation")
    assert len(jobs) == 180 and Counter(x["arm"] for x in jobs) == {"B": 60, "F4": 60, "D4": 60}
    blind = {x["id"]: x for x in run072.lines(OUT / "target_blind.jsonl") if x["sid"] in frozen["confirmation_patients"]}
    assert len(blind) == 60
    assert all(x["id"] in blind and x["sid"] in frozen["confirmation_patients"] for x in jobs)
    by = {(x["id"], x["arm"]): x for x in jobs}
    old = {(x["id"], x["arm"]): x for x in run072.lines(ROOT / "outputs/071_judge_icl_feasibility/main_jobs.jsonl")}
    for pid, case in blind.items():
        assert by[(pid, "B")]["body"] == old[(pid, "B")]["body"]
        assert by[(pid, "F4")]["body"] == old[(pid, "E")]["body"]
        for arm in ("B", "F4", "D4"):
            user = by[(pid, arm)]["body"]["messages"][-1]["content"]
            assert json.loads(user) == {"proposition": case["claim"], "reference": case["reference"]}
    selections = run072.lines(OUT / "confirmation_dynamic_selections.jsonl")
    assert len(selections) == 60 and {x["id"] for x in selections} == set(blind)
    assert all(len(x["selected"]) == 4 and len({y["sid"] for y in x["selected"]}) == 4 for x in selections)
    cap_bound = sum(run072.bound(x["body"]) for x in jobs)
    current = sum(x["cost_cny"] for x in run072.attempt_state()[0])
    print(json.dumps({"status": "PASS", "confirmation_jobs": len(jobs), "candidate": selected["selected_arm"],
                      "task_used_cny": round(current, 6),
                      "all_confirmation_max_token_reservations_cny": round(cap_bound, 6),
                      "remaining_cap_cny": round(30-current, 6)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
