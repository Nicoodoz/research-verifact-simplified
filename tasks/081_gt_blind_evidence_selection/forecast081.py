"""Pre-API cost forecast from frozen blind Stage 1 requests and historical aggregate DS usage."""
import json
import statistics
from pathlib import Path

import blind081 as b
import selector081 as s


def main():
    sample = [x for x in b.lines("outputs/081_gt_blind_evidence_selection/sample_blind.jsonl") if x["stage"] == 1]
    composer_bytes = []
    for x in sample:
        lines = [s.candidate_line(c["short_id"], c) for c in x["candidates"]]
        body = s.compose_body(x["claim"], [x["claim"]], lines)
        composer_bytes.append(len(s.compact(body).encode("utf-8")))
    plan_bytes = [len(s.compact(s.plan_body(x["claim"])).encode("utf-8")) for x in sample]
    # A conservative planning rate of 1 token per 3 UTF-8 bytes, with 400/300
    # actual output tokens for composer/planner, and DS 20% above historical T-S average.
    plan = sum(v / 3 * 3 + 300 * 12 for v in plan_bytes) * 2 / 1e6
    compose = sum(v / 3 * 3 + 400 * 12 for v in composer_bytes) * 2 / 1e6
    historical_ds = 6.376971 / 240
    judge = 288 * historical_ds * 1.20
    projected = plan + compose + judge
    result = {"stage1_n": 96, "logical_requests": 672,
              "composer_bytes_mean": statistics.mean(composer_bytes),
              "composer_bytes_max": max(composer_bytes),
              "baseline_reference_chars_mean": statistics.mean(len(x["baseline_reference"]) for x in sample),
              "historical_053_TS_mean_cny": historical_ds,
              "assumptions": "Qwen input <=1 token/3 UTF8 bytes; plan/composer output 300/400 tokens; Judge 1.2x 053 T-S aggregate mean; no retry",
              "selector_plan_cny": plan, "selector_compose_cny": compose,
              "judge_cny": judge, "projected_base_cny": projected,
              "retry_unknown_buffer_cny": 20 - projected,
              "safe_to_start": projected <= 17.5 and 20 - projected >= 2.5}
    path = b.OUT / "stage1_cost_estimate.json"
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
