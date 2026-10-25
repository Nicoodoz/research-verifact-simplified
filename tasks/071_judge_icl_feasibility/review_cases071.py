"""Collect every first-round changed decision for offline, source-grounded review."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/071_judge_icl_feasibility"
sys.path.insert(0, str(Path(__file__).parent))
import run071  # noqa: E402


def records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def write(path, rows):
    with path.open("x", encoding="utf-8", newline="\n") as target:
        for row in rows:
            target.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main():
    analysis = run071.read(OUT / "stage1_analysis.json")
    changed = set()
    for pair in list(analysis["final_pairs"].values()) + list(analysis["raw_pairs"].values()) + [analysis["B_vs_historical"]]:
        changed.update(pair["rescue_ids"])
        changed.update(pair["harm_ids"])
    blind = {r["id"]: r for r in records(OUT / "evaluation_blind.jsonl")}
    gold = {r["id"]: r for r in records(OUT / "evaluation_gt.jsonl")}
    predictions = {(r["id"], r["arm"]): r for r in records(OUT / "stage1_predictions.jsonl")}
    jobs = {(r["id"], r["arm"]): r for r in records(OUT / "main_jobs.jsonl")}
    _, terminal = run071.resolved_state()
    result = []
    for pid in sorted(changed):
        source = blind[pid]
        ref = source["reference"]
        arms = {}
        for arm in ("B", "E", "C"):
            prediction = predictions[(pid, arm)]
            request_id = jobs[(pid, arm)]["request_id"]
            parsed = terminal[request_id]["parsed"]
            response = parsed.get("parsed") or {}
            arms[arm] = {
                "raw": prediction["raw"],
                "PriorG": prediction["PriorG"],
                "scores": prediction["scores"],
                "reason": response.get("reason"),
                "checks": response.get("checks"),
                "status": parsed["status"],
            }
        result.append({
            "id": pid,
            "sid": source["sid"],
            "author": source["author"],
            "claim": source["claim"],
            "GT": gold[pid]["GT"],
            "reference_sha256": hashlib.sha256(ref.encode()).hexdigest(),
            "reference": ref,
            "arms": arms,
        })
    write(OUT / "stage1_changed_cases.jsonl", result)
    print(json.dumps({"changed_cases": len(result), "file": str(OUT / "stage1_changed_cases.jsonl")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
