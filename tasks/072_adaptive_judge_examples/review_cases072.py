"""Offline actual-claim/reference review material for paired changed cases."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/072_adaptive_judge_examples"
sys.path.insert(0, str(Path(__file__).parent))
import run072  # noqa: E402


def write_lines(path, rows):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run(stage):
    assert stage in ("pilot", "confirmation")
    analysis = run072.read(OUT / f"{stage}_analysis.json")
    changed = set()
    for pair in list(analysis["final_pairs"].values()) + list(analysis["raw_pairs"].values()):
        changed.update(pair["rescue_ids"])
        changed.update(pair["harm_ids"])
    blind = {x["id"]: x for x in run072.lines(OUT / "target_blind.jsonl")}
    gold = {x["id"]: x for x in run072.lines(OUT / "target_gt.jsonl")}
    predictions = {(x["id"], x["arm"]): x for x in run072.lines(OUT / f"{stage}_predictions.jsonl")}
    jobs = {(x["id"], x["arm"]): x for x in run072.lines(OUT / f"{stage}_jobs.jsonl")}
    selection_file = OUT / ("dynamic_selections.jsonl" if stage == "pilot" else "confirmation_dynamic_selections.jsonl")
    selections = {x["id"]: x["selected"] for x in run072.lines(selection_file)} if selection_file.exists() else {}
    _, answered = run072.attempt_state()
    result = []
    for pid in sorted(changed):
        source = blind[pid]
        arms = {}
        for arm in analysis["arms"]:
            pred = predictions[(pid, arm)]
            job = jobs[(pid, arm)]
            parsed = answered[job["request_id"]]["parsed"]
            content = parsed.get("parsed") or {}
            arms[arm] = {"raw": pred["raw"], "PriorG": pred["PriorG"], "scores": pred["scores"],
                         "reason": content.get("reason"), "checks": content.get("checks"),
                         "parsed_status": pred["parsed_status"], "fallback": pred["fallback"]}
        result.append({"id": pid, "sid": source["sid"], "author": source["author"],
                       "claim": source["claim"], "reference": source["reference"],
                       "reference_sha256": hashlib.sha256(source["reference"].encode()).hexdigest(),
                       "GT": gold[pid]["GT"], "arms": arms, "dynamic_selection": selections.get(pid)})
    write_lines(OUT / f"{stage}_changed_cases.jsonl", result)
    print(json.dumps({"stage": stage, "changed_cases": len(result)}, ensure_ascii=False))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("pilot", "confirmation"))
    run(p.parse_args().stage)
