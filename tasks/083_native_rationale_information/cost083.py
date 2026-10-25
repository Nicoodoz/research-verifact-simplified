"""Reconcile all new extraction attempts and historical Judge deployment cost."""
from __future__ import annotations

import json
from collections import Counter

import inventory083 as base
import run083 as runner

ROOT, OUT = base.ROOT, base.OUT


def main():
    attempts, answered = runner.state()
    assert len(answered) == len(runner.jobs()) == 1015
    row_by_sha = {x["cleaned_sha256"]: x for x in base.lines(
        "outputs/083_native_rationale_information/cleaned_inputs.jsonl") if x["arm"] == "F4"}
    assert len(row_by_sha) == 1015
    tokens = Counter()
    by_phase = Counter()
    for rid, answer in answered.items():
        phase = row_by_sha[answer["job"]["cleaned_sha256"]]["phase"]
        response = json.loads(answer["transport"]["body_text"])
        use = response["usage"]
        tokens["input"] += int(use["prompt_tokens"])
        tokens["output"] += int(use["completion_tokens"])
        by_phase[phase] += answer["attempt"]["original_price_cny"]
    cost = sum(x["original_price_cny"] for x in attempts)
    assert abs(cost - (tokens["input"] * .2 + tokens["output"] * 2) / 1e6) < 1e-8
    assert cost < 20
    judge_cost = Counter()
    judge_usage = Counter()
    source = base.lines("outputs/083_native_rationale_information/source_manifest.jsonl")
    for row in source:
        if row["arm"] != "F4":
            continue
        receipt = base.read(ROOT / row["receipt_source"])
        response = json.loads(receipt["transport"]["body_text"])
        use = response.get("usage", {})
        inp, out = int(use.get("prompt_tokens", 0)), int(use.get("completion_tokens", 0))
        judge_usage[row["phase"] + ":input"] += inp
        judge_usage[row["phase"] + ":output"] += out
        judge_cost[row["phase"]] += (inp * 3 + out * 9) / 1e6
    base.write("cost_ledger.json", {
        "status": "FULL_TASK_NEW_PAID_API_RECONCILED",
        "hard_cap_original_cny": 20.0,
        "new_original_price_cny": cost,
        "new_attempts": len(attempts),
        "http200": sum(x["http_status"] == 200 for x in attempts),
        "unknown_or_missing_receipts": [x for x in attempts if x["http_status"] in (0, None)],
        "input_output_tokens": dict(tokens),
        "new_cost_by_phase_cny": dict(by_phase),
        "new_original_rate_per_million": {"input": .2, "output": 2},
        "historical_F4_Judge_original_price_estimate_cny": dict(judge_cost),
        "historical_F4_Judge_usage_tokens": dict(judge_usage),
        "historical_Judge_not_charged_again_in_083": True,
        "deployment_per_case_needs_original_Judge_plus_extractor": True,
        "attempts": attempts,
        "price_source": "https://help.aliyun.com/zh/model-studio/qwen3-5-flash",
    })
    print(json.dumps({"new_original_cny": round(cost, 6), "attempts": len(attempts),
                      "tokens": dict(tokens), "judge_cost_historical": dict(judge_cost)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
