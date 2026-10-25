"""Apply frozen 082 mappings to exact-body B/F4 repeats, without replacing originals."""
from __future__ import annotations

import datetime
import json
import sys
from collections import Counter

import inventory082 as i
import prepare082 as p
import run082 as r
import model082 as m
import analyze082 as a

ROOT, OUT = i.ROOT, i.OUT
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
from common053 import VALID, parse_response, decision
from common066 import priorg


def discount_estimate(attempt):
    if attempt["http_status"] != 200:
        return attempt["original_price_cny"]
    receipt = r.read(ROOT / attempt["receipt_source"])
    started = datetime.datetime.fromisoformat(receipt["transport"]["started_utc"])
    hour = (started + datetime.timedelta(hours=8)).hour
    return attempt["original_price_cny"] * (0.5 if hour >= 22 or hour < 8 else 1.0)


def main():
    jobs = r.jobs("repeat")
    attempts, answer = r.answers("repeat")
    assert len(jobs) == len(answer) == 48
    first = {x["id"]: x for x in i.lines("outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")}
    models = r.read(OUT / "models_frozen.json")
    repeat, invalid = [], []
    for pid in sorted({x["id"] for x in jobs}):
        source = first[pid]
        assert source["cohort"] == "old352"
        case = {"id": pid, "sid": source["sid"], "author": source["author"],
                "GT": source["GT"], "original_methods": source["methods"],
                "arms": {}, "methods": {}}
        scores, valid = {}, {}
        for config in ("B", "F4"):
            job = next(x for x in jobs if x["id"] == pid and x["arm"] == config)
            assert job["body_sha256"] == source["arms"][config]["body_sha256"]
            got = answer[job["request_id"]]
            assert got["mode"] == "new"
            parsed = parse_response(got["transport"], True, True)
            assert parsed.get("model_returned") in (None, r.MODEL)
            okay = parsed["status"] in VALID and parsed.get("scores") is not None
            scores[config], valid[config] = parsed.get("scores"), okay
            fallback = source["fallback_label"]
            case["arms"][config] = {"status": parsed["status"], "valid": okay,
                                     "raw": parsed.get("verdict"), "scores": parsed.get("scores"),
                                     "body_sha256": job["body_sha256"],
                                     "receipt_source": got["attempt"]["receipt_source"]}
            if not okay:
                invalid.append({"id": pid, "config": config, "status": parsed["status"], "fallback": fallback})
            case["methods"][config] = {"raw": parsed["verdict"] if okay else fallback,
                                        "U0": decision(parsed["scores"], 0) if okay else fallback,
                                        "U2": decision(parsed["scores"], 2) if okay else fallback,
                                        "PriorG": priorg(parsed["scores"]) if okay else fallback}
        learned = a.apply_models(scores, valid, source["fallback_label"], models)
        for config in ("B", "F4"):
            case["methods"][config].update(learned[config])
        repeat.append(case)
    first_rows = [first[x["id"]] for x in repeat]
    flips = {method: {config: sum(x["methods"][config][method] != x["original_methods"][config][method]
                                   for x in repeat) for config in ("B", "F4")}
             for method in ("raw", "U0", "U2", "PriorG", "independent_R", "shared_R", "adapted_R", "selected_R")}
    metrics = {run: [a.metric(rows, config, method) for config in ("B", "F4")
                     for method in ("raw", "PriorG", "independent_R", "adapted_R", "selected_R")]
               for run, rows in (("first", first_rows), ("repeat", repeat))}
    pairs = {run: [a.pair(rows, "B", method, "F4", method)
                   for method in ("raw", "PriorG", "independent_R", "adapted_R", "selected_R")]
             for run, rows in (("first", first_rows), ("repeat", repeat))}
    total_original = sum(x["original_price_cny"] for x in attempts)
    assert total_original <= 50
    cost = {"cap_original_cny": 50, "new_attempts": len(attempts),
            "successful_http200": sum(x["http_status"] == 200 for x in attempts),
            "unknown_or_no_receipt": [x for x in attempts if x["http_status"] in (None, 0)],
            "original_price_total_cny": total_original,
            "original_price_by_stage_cny": {stage: sum(x["original_price_cny"] for x in attempts if x["stage"] == stage)
                                            for stage in r.STAGES},
            "official_time_of_day_price_estimate_cny": sum(discount_estimate(x) for x in attempts),
            "discount_estimate_is_not_billing_or_budget": True, "attempts": attempts}
    p.write("cost_ledger.json", cost)
    p.write("repeat_predictions.jsonl", repeat)
    p.write("repeat_results.json", {"status": "EXACT_BODY_REPEAT_DIAGNOSTIC", "n": len(repeat),
                                    "patients": len({x["sid"] for x in repeat}),
                                    "invalid": invalid, "label_flips_first_vs_repeat": flips,
                                    "metrics": metrics, "paired_B_to_F4": pairs,
                                    "models_frozen_sha256": p.sha(OUT / "models_frozen.json"),
                                    "repeat_jobs_sha256": p.sha(OUT / "repeat_jobs.jsonl"),
                                    "original_answer_not_replaced": True})
    print(json.dumps({"original_total_cny": total_original, "attempts": len(attempts),
                      "repeat_n": len(repeat), "PriorG_flips": flips["PriorG"],
                      "selected_flips": flips["selected_R"],
                      "paired_selected_net": {run: next(x["net"] for x in rows if x["candidate"] == "F4:selected_R")
                                              for run, rows in pairs.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
