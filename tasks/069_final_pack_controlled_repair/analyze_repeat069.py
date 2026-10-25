"""Apply 069's frozen stability and second-stage gate after exact repeats."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/069_final_pack_controlled_repair"
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
import run069  # noqa: E402
from analyze_stage1_069 import jsonl, parsed  # noqa: E402


def main():
    if (OUT / "stage2_gate.json").exists():
        raise RuntimeError("gate already written")
    first = jsonl(OUT / "stage1_results.jsonl")
    repeats = jsonl(OUT / "stage1_repeat_jobs.jsonl")
    jobs = {(job["id"], job["arm"]): job for job in repeats}
    attempts, done = run069.state()
    assert len(repeats) == 16
    assert all(job["request_id"] in done for job in repeats)
    details = []
    for row in first:
        gt = row["GT"]
        out = {"id": row["id"], "sid": row["sid"], "GT": gt,
               "baseline_historical_raw": row["conditions"]["baseline_historical"]["raw"],
               "baseline_historical_pg": row["conditions"]["baseline_historical"]["pg"],
               "baseline_repeat_raw": row["conditions"]["baseline_repeat"].get("raw"),
               "baseline_repeat_pg": row["conditions"]["baseline_repeat"].get("pg"),
               "oracle_historical_raw": row["conditions"]["oracle_historical"].get("raw"),
               "oracle_historical_pg": row["conditions"]["oracle_historical"].get("pg"),
               "oracle_repeat_raw": row["conditions"]["oracle_repeat"].get("raw"),
               "oracle_repeat_pg": row["conditions"]["oracle_repeat"].get("pg"),
               "baseline_stably_wrong_pg": row["conditions"]["baseline_historical"]["pg"] != gt and row["conditions"]["baseline_repeat"].get("pg") != gt,
               "oracle_stably_right_pg": row["conditions"]["oracle_historical"].get("pg") == gt and row["conditions"]["oracle_repeat"].get("pg") == gt,
               "new_oracle_n": row["new_oracle_n"], "intersection_n": row["intersection_n"],
               "baseline_chars": row["baseline_chars"], "add_only_chars": row["add_only_chars"],
               "operations": {}}
        for arm in ("add_only", "delete_only", "combined_header"):
            result = row["conditions"][arm]
            repeat_job = jobs.get((row["id"], arm + "_repeat2"))
            repeat = parsed(repeat_job, done[repeat_job["request_id"]]["transport"]) if repeat_job else {"status": "not_sent_first_call_wrong_or_unconstructable"}
            stable_pg = bool(result.get("status") == repeat.get("status") == "valid" and result["pg"] == repeat["pg"] == gt and out["baseline_stably_wrong_pg"])
            stable_raw = bool(result.get("status") == repeat.get("status") == "valid" and result["raw"] == repeat["raw"] == gt and out["baseline_historical_raw"] != gt and out["baseline_repeat_raw"] != gt)
            out["operations"][arm] = {"first_status": result.get("status"), "first_raw": result.get("raw"), "first_pg": result.get("pg"), "repeat_status": repeat.get("status"), "repeat_raw": repeat.get("raw"), "repeat_pg": repeat.get("pg"), "stable_pg_rescue": stable_pg, "stable_raw_rescue": stable_raw, "first_pg_correct": result.get("pg") == gt, "repeat_pg_correct": repeat.get("pg") == gt if repeat.get("status") == "valid" else None}
        details.append(out)
    with (OUT / "stage1_final_cases.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in details:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    byarm = {}
    for arm in ("add_only", "delete_only", "combined_header"):
        stable = [row for row in details if row["operations"][arm]["stable_pg_rescue"]]
        first_right = [row for row in details if row["operations"][arm]["first_pg_correct"]]
        repeated_right = [row for row in details if row["operations"][arm]["repeat_pg_correct"]]
        byarm[arm] = {"first_pg_correct": len(first_right), "repeat_pg_correct": len(repeated_right), "stable_pg_rescue": len(stable), "stable_pg_rescue_patients": len({row["sid"] for row in stable}), "stable_raw_rescue": sum(row["operations"][arm]["stable_raw_rescue"] for row in details), "first_falseS": sum(row["GT"] != "Supported" and row["operations"][arm]["first_pg"] == "Supported" for row in details), "repeat_falseS": sum(row["GT"] != "Supported" and row["operations"][arm]["repeat_pg"] == "Supported" for row in details)}
    eligible = [arm for arm in ("add_only", "delete_only", "combined_header") if byarm[arm]["stable_pg_rescue"] >= 3 and byarm[arm]["stable_pg_rescue_patients"] >= 3]
    selected = eligible[0] if eligible else None
    summary = {"cases": len(details), "patients": len({row["sid"] for row in details}),
               "baseline_repeat_correct_pg": sum(row["baseline_repeat_pg"] == row["GT"] for row in details),
               "baseline_stably_wrong_pg": sum(row["baseline_stably_wrong_pg"] for row in details),
               "oracle_repeat_correct_pg": sum(row["oracle_repeat_pg"] == row["GT"] for row in details),
               "oracle_stably_right_pg": sum(row["oracle_stably_right_pg"] for row in details),
               "arm_results": byarm, "eligible_arms": eligible, "selected_arm": selected,
               "stage2_trigger": selected is not None,
               "all_repeat_jobs_valid": all(parsed(job, done[job["request_id"]]["transport"])["status"] == "valid" for job in repeats),
               "all_task_attempts": len(attempts), "all_task_http200": sum(row["http_status"] == 200 for row in attempts),
               "all_task_occupied_cny": sum(row["cost"] for row in attempts), "cap_cny": 8.0}
    (OUT / "stage1_final_analysis.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    gate = {"stage2_authorized_by_protocol": selected is not None and summary["all_repeat_jobs_valid"], "selected_arm": selected, "reason": "stable final rescues >=3 across >=3 patients in one arm" if selected else "no arm reaches stable final rescue/patient threshold", "stage1_analysis_sha256": __import__("hashlib").sha256((OUT / "stage1_final_analysis.json").read_bytes()).hexdigest(), "budget_occupied_cny": summary["all_task_occupied_cny"], "hard_cap_cny": 8.0}
    (OUT / "stage2_gate.json").write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
