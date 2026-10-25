"""Summarize immutable 071 receipts without accessing the API."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/071_judge_icl_feasibility"
sys.path.insert(0, str(Path(__file__).parent))
import run071  # noqa: E402


def main():
    attempts, _ = run071.state()
    groups = defaultdict(list)
    for attempt in attempts:
        request = run071.read(ROOT / attempt["request_path"])
        job = request["job"]
        groups[job.get("arm", job["stage"])].append(attempt)
    arms = {
        arm: {
            "attempts": len(rows),
            "http_status_counts": dict(Counter(str(x["http_status"]) for x in rows)),
            "used_or_reserved_cny": round(sum(x["cost_cny"] for x in rows), 9),
        }
        for arm, rows in sorted(groups.items())
    }
    unknown = [x for x in attempts if x["http_status"] == 0]
    summary = {
        "model": run071.MODEL,
        "price_cny_per_million_tokens": {"input": run071.PRICE_INPUT, "output": run071.PRICE_OUTPUT},
        "prior_key_check_conservative_reserve_cny": run071.PRIOR_RESERVED,
        "071_api_attempts": len(attempts),
        "by_arm_or_stage": arms,
        "http200_count": sum(x["http_status"] == 200 for x in attempts),
        "unknown_count": len(unknown),
        "unknown_original_request_ids": sorted(x["id"] for x in unknown),
        "unknown_reserve_cny": round(sum(x["cost_cny"] for x in unknown), 9),
        "known_usage_estimate_cny": round(sum(x["cost_cny"] for x in attempts if x["http_status"] == 200), 9),
        "task_used_or_reserved_cny": round(run071.PRIOR_RESERVED + sum(x["cost_cny"] for x in attempts), 9),
        "task_cap_cny": run071.CAP,
    }
    with (OUT / "cost_summary.json").open("x", encoding="utf-8", newline="\n") as target:
        json.dump(summary, target, ensure_ascii=False, indent=2)
        target.write("\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
