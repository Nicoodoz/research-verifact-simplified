"""Summarize 072 per-attempt receipts and unknown reservations offline."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/072_adaptive_judge_examples"
sys.path.insert(0, str(Path(__file__).parent))
import run072  # noqa: E402


def main():
    attempts, answered = run072.attempt_state()
    grouped = defaultdict(list)
    for x in attempts:
        grouped[(x["stage"], x["arm"])].append(x)
    groups = {}
    for (stage, arm), rows in sorted(grouped.items()):
        token_inputs = token_outputs = 0
        for x in rows:
            if x["http_status"] == 200:
                usage = answered[x["logical_id"]]["parsed"].get("usage") or {}
                token_inputs += int(usage.get("prompt_tokens", 0))
                token_outputs += int(usage.get("completion_tokens", 0))
        groups[f"{stage}:{arm}"] = {"attempts": len(rows), "http_status_counts": dict(Counter(str(x["http_status"]) for x in rows)),
                                    "used_or_reserved_cny": round(sum(x["cost_cny"] for x in rows), 9),
                                    "prompt_tokens": token_inputs, "completion_tokens": token_outputs}
    unknown = [x for x in attempts if x["http_status"] in (0, None)]
    result = {"model": run072.MODEL, "busy_price_cny_per_million": {"input": run072.PRICE_INPUT, "output": run072.PRICE_OUTPUT},
              "price_source": "https://help.aliyun.com/en/model-studio/model-pricing",
              "attempts": len(attempts), "answered_logical": len(answered),
              "http200": sum(x["http_status"] == 200 for x in attempts),
              "unknown_count": len(unknown), "unknown_reserve_cny": round(sum(x["cost_cny"] for x in unknown), 9),
              "groups": groups, "total_used_or_reserved_cny": round(sum(x["cost_cny"] for x in attempts), 9),
              "cap_cny": run072.CAP, "supplier_bill_reconciled": False}
    with (OUT / "cost_summary.json").open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: result[k] for k in ("attempts", "answered_logical", "unknown_count", "total_used_or_reserved_cny")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
