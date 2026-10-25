"""Freeze the full original-price task forecast and initial stage job hashes."""
from __future__ import annotations

import json

import inventory082 as i
import prepare082 as p

ROOT, OUT = i.ROOT, i.OUT
CAP = 50.0
P_B = 6.376971 / 240  # 053 T-S mean at original busy-hour price
P_F4 = 3.988890 / 95  # 079 F4 mean at original busy-hour price


def main():
    blind = json.loads((OUT / "blind_freeze.json").read_text(encoding="utf-8"))
    assert blind["status"] == "FROZEN_BEFORE_082_API_AND_EVALUATION_GT"
    cache = json.loads((OUT / "cache_index_summary.json").read_text(encoding="utf-8"))
    matched = cache["matched_logical"]
    n_screen = 420 - matched.get("screen_B/B", 0)
    n_train_f4_upper = 378  # no training F4 cache credit until E is selected
    n_eval_b = 180 - matched.get("eval/B", 0)
    n_eval_f4 = 180 - matched.get("eval/F4", 0)
    n_repeat_b = n_repeat_f4 = 24
    stage_estimates = {"screen_B": n_screen * P_B,
                       "train_F4_upper": n_train_f4_upper * P_F4,
                       "eval": n_eval_b * P_B + n_eval_f4 * P_F4,
                       "repeat": n_repeat_b * P_B + n_repeat_f4 * P_F4}
    projected = sum(stage_estimates.values())
    assert projected < 42 and CAP - projected >= 8
    plan = {"status": "FROZEN_BEFORE_FIRST_082_API", "cap_original_cny": CAP,
            "model": "deepseek-v4-flash-0731", "provider": "Alibaba Cloud Beijing workspace, fixed 0731",
            "original_input_cny_per_million": 3, "original_output_cny_per_million": 9,
            "price_source": "https://help.aliyun.com/en/model-studio/model-pricing",
            "discount_not_used_for_budget": True,
            "historical_B_original_mean_cny": P_B, "historical_F4_original_mean_cny": P_F4,
            "max_new_logical": {"screen_B": n_screen, "train_F4": n_train_f4_upper,
                                "eval_B": n_eval_b, "eval_F4": n_eval_f4,
                                "repeat_B": n_repeat_b, "repeat_F4": n_repeat_f4},
            "stage_estimates_original_cny": stage_estimates,
            "projected_original_cny": projected, "buffer_original_cny": CAP - projected,
            "screen_n": 420, "main_rep_n": 308, "boundary_n": 308,
            "old_eval_n": 352, "new_eval_n": 180, "repeat_n": 24,
            "blind_freeze_sha256": p.sha(OUT / "blind_freeze.json"),
            "cache_index_sha256": p.sha(OUT / "cache_index.jsonl"),
            "protocol_sha256": p.sha(ROOT / "tasks/082_anchor_configuration_adaptation/protocol.md")}
    p.write("cost_plan.json", plan)
    for stage, name in (("screen_B", "screen_B_jobs.jsonl"), ("eval", "eval_jobs.jsonl"),
                        ("repeat", "repeat_jobs.jsonl")):
        p.write(stage + "_freeze.json", {"stage": stage, "status": "FROZEN_BEFORE_STAGE_API",
                                          "jobs_sha256": p.sha(OUT / name),
                                          "blind_freeze_sha256": p.sha(OUT / "blind_freeze.json"),
                                          "cost_plan_sha256": p.sha(OUT / "cost_plan.json")})
    print(json.dumps({"projected_original_cny": projected, "buffer_original_cny": CAP - projected,
                      "stage_estimates": stage_estimates, "new_calls_upper": plan["max_new_logical"]}))


if __name__ == "__main__":
    main()
