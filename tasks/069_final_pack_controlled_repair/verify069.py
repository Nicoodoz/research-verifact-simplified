"""Independent artifact and gate checks for the stopped 069 mechanism study."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/069_final_pack_controlled_repair"
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
import common066 as c  # noqa: E402
import run069  # noqa: E402
sys.path.insert(0, str(ROOT / "tasks/067_conservative_evidence_packing"))
import common067 as c67  # noqa: E402


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def main():
    checks = []

    def ck(name, condition, detail=None):
        checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})

    freeze = json.loads((OUT / "freeze.json").read_text(encoding="utf-8"))
    repeat_freeze = json.loads((OUT / "repeat_freeze.json").read_text(encoding="utf-8"))
    stage1 = jsonl(OUT / "stage1_jobs.jsonl")
    repeats = jsonl(OUT / "stage1_repeat_jobs.jsonl")
    controls = {x["id"]: x for x in jsonl(OUT / "stage1_controls.jsonl")}
    cases = {x["id"]: x for x in jsonl(ROOT / "outputs/066_oracle_headroom/error_cases.jsonl")}
    oracle = {x["id"]: x for x in jsonl(ROOT / "outputs/066_oracle_headroom/final_mapping.jsonl")}
    b_jobs = {x["id"]: x for x in jsonl(ROOT / "outputs/053_thinking_prior_validation/main_jobs.jsonl") if x["condition"] == "T-S"}
    o_jobs = {x["id"]: x for x in jsonl(ROOT / "outputs/066_oracle_headroom/stage3_jobs.jsonl")}
    source_hashes = {key.replace("\\", "/"): value for key, value in freeze["source_sha256"].items()}
    for rel, expected in source_hashes.items():
        ck("source_hash_" + rel, hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == expected)
    ck("repeat_jobs_hash", hashlib.sha256((OUT / "stage1_repeat_jobs.jsonl").read_bytes()).hexdigest() == repeat_freeze["jobs_sha256"])
    ck("cohort_count", len(controls) == 10 and len({x["sid"] for x in controls.values()}) == 8)
    ck("job_count", len(stage1) == 48 and len(repeats) == 16)
    ck("unique_ids", len({job["request_id"] for job in stage1 + repeats}) == 64)
    ck("no_stage2_jobs", not (OUT / "stage2_jobs.jsonl").exists())
    eval_cohort = jsonl(OUT / "stage2_cohort_blind.jsonl")
    ck("contingent_patient_disjoint", len(eval_cohort) == 20 and not ({str(x["sid"]) for x in eval_cohort} & {str(x["sid"]) for x in controls.values()}))
    ck("contingent_blind", all("GT" not in x and "oracle" not in x for x in eval_cohort))
    first = {(job["id"], job["arm"]): job for job in stage1}
    for pid, row in controls.items():
        ck("all_oracle_in_c48_" + pid, set(row["oracle_ids"]) <= set(cases[pid]["c48_pids"]))
        ck("baseline_count_" + pid, len(row["baseline_ids"]) == row["baseline_blocks"])
        ck("baseline_body_" + pid, first[(pid, "baseline_repeat")]["body"] == b_jobs[pid]["body"])
        ck("oracle_body_" + pid, first[(pid, "oracle_repeat")]["body"] == o_jobs[pid]["body"])
        ck("A_constructable_" + pid, ((pid, "add_only") in first) == bool(row["missing_ids"]))
        ck("D_constructable_" + pid, ((pid, "delete_only") in first) == row["delete_only_constructable"])
        combo = json.loads(first[(pid, "combined_header")]["body"]["messages"][1]["content"])["reference"]
        ck("C_is_header_plus_oracle_" + pid, combo.endswith(oracle[pid]["reference"]) and len(combo) - len(oracle[pid]["reference"]) == row["header_chars"])
        if (pid, "add_only") in first:
            added = json.loads(first[(pid, "add_only")]["body"]["messages"][1]["content"])["reference"]
            ck("A_retains_full_baseline_" + pid, added.startswith(cases[pid]["baseline_reference"]))
        if (pid, "delete_only") in first:
            deleted = json.loads(first[(pid, "delete_only")]["body"]["messages"][1]["content"])["reference"]
            ck("D_no_new_text_" + pid, all(block in c67.reference_blocks(cases[pid]["baseline_reference"]) for block in c67.reference_blocks(deleted)))
    occupied = 0.0
    statuses = Counter()
    for job in stage1 + repeats:
        rid = job["request_id"]
        ck("body_hash_" + rid, job["body_sha256"] == c.digest(job["body"]))
        payload = json.loads(job["body"]["messages"][1]["content"])
        ck("no_gt_in_api_" + rid, set(payload) == {"proposition", "reference"})
        ck("judge_settings_" + rid, job["body"]["model"] == c.MODELS["deepseek"] and job["body"]["enable_thinking"] is True and job["body"]["reasoning_effort"] == "high" and job["body"]["max_tokens"] == 8192)
        if job in repeats:
            source = next(x for x in stage1 if x["request_id"] == job["source_request_id"])
            ck("repeat_exact_body_" + rid, job["body"] == source["body"])
        folder = OUT / "attempts" / (hashlib.sha256(rid.encode()).hexdigest()[:24] + "_01")
        request_file, receipt_file = folder / "request.json", folder / "receipt.json"
        ck("request_exists_" + rid, request_file.exists())
        ck("receipt_exists_" + rid, receipt_file.exists())
        if not request_file.exists():
            continue
        request = json.loads(request_file.read_text(encoding="utf-8"))
        ck("request_matches_job_" + rid, request["job"] == job and request["hard_cap_cny"] == 8.0)
        if receipt_file.exists():
            receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
            ck("receipt_hash_" + rid, receipt["request_sha256"] == c.sha(request_file))
            tr = receipt["transport"]
            statuses[str(tr.get("http_status"))] += 1
            occupied += c.charge(job, tr)
        else:
            occupied += float(request["reservation_cny"])
    ck("all_http200", statuses == {"200": 64}, dict(statuses))
    ck("budget_under_8", occupied <= 8.0 + 1e-9, occupied)
    final = json.loads((OUT / "stage1_final_analysis.json").read_text(encoding="utf-8"))
    gate = json.loads((OUT / "stage2_gate.json").read_text(encoding="utf-8"))
    ck("analysis_cost", abs(final["all_task_occupied_cny"] - occupied) < 1e-8)
    ck("gate_false", gate["stage2_authorized_by_protocol"] is False and gate["selected_arm"] is None)
    ck("gate_recomputed", all(x["stable_pg_rescue"] < 3 or x["stable_pg_rescue_patients"] < 3 for x in final["arm_results"].values()))
    result = {"status": "PASS" if all(x["status"] == "PASS" for x in checks) else "FAIL", "n_checks": len(checks), "n_fail": sum(x["status"] == "FAIL" for x in checks), "occupied_cny": occupied, "checks": checks}
    (OUT / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: result[key] for key in ("status", "n_checks", "n_fail", "occupied_cny")}, ensure_ascii=False))
    if result["status"] != "PASS":
        print(json.dumps([x for x in checks if x["status"] == "FAIL"], ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
