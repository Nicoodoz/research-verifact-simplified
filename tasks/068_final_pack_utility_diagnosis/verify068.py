"""Independent artifact checks for 068 inputs, receipts, budget, and evaluation."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/068_final_pack_utility_diagnosis"
sys.path.insert(0, str(ROOT / "tasks/067_conservative_evidence_packing"))
import common067 as c  # noqa: E402
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.evaluation import evaluate  # noqa: E402


def lines(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def main():
    checks = []

    def ck(name, condition, detail=None):
        checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})

    f067 = ROOT / "outputs/067_conservative_evidence_packing"
    old = {x["id"]: x for x in lines(ROOT / "outputs/052_first_tier_validation/main_jobs.jsonl") if x["condition"] == "T-S"}
    short = {x["id"]: x for x in lines(f067 / "stage2_jobs.jsonl")}
    cases = {x["id"]: x for x in lines(f067 / "cases_blind.jsonl")}
    audits = lines(f067 / "stage1_jobs.jsonl")
    mapping = {x["id"]: x for x in lines(f067 / "pack_mapping.jsonl")}
    for name, job_file, freeze_file in (("repeat", "jobs_002.jsonl", "freeze_003.json"), ("presentation", "presentation_jobs.jsonl", "presentation_freeze.json"), ("v2", "jobs_v2_068.jsonl", "freeze_v2_068.json")):
        freeze = json.loads((OUT / freeze_file).read_text(encoding="utf-8"))
        ck("freeze_hash_" + name, hashlib.sha256((OUT / job_file).read_bytes()).hexdigest() == freeze["jobs_sha256"])
    first_jobs = lines(OUT / "jobs_002.jsonl") + lines(OUT / "presentation_jobs.jsonl")
    jobs = first_jobs + lines(OUT / "jobs_v2_068.jsonl")
    first_ids = {job["request_id"] for job in first_jobs}
    v2_short = {x["id"]: x for x in lines(f067 / "stage2v2_jobs.jsonl")}
    v2_cases = {x["id"]: x for x in lines(f067 / "cases_blind_v2.jsonl")}
    v2_freeze = json.loads((OUT / "freeze_v2_068.json").read_text(encoding="utf-8"))
    ck("unique_job_ids", len({job["request_id"] for job in jobs}) == len(jobs))
    ck("jobs_count", len(jobs) == 164)
    ck("067_baseline_pids_empty", all(not case["baseline_pids"] for case in cases.values()))
    ck("067_audit_current_ids_empty", all(json.loads(job["body"]["messages"][1]["content"])["current_pack_ids"] == [] for job in audits))
    ck("067_changed_count", sum(bool(mp["changed"]) for mp in mapping.values()) == 226)
    ck("067_reported_drops_zero", all(not mp["dropped_pids"] for mp in mapping.values()))
    ck("v2_mapped_nonempty", all((not case["mapped"]) or bool(case["baseline_pids"]) for case in v2_cases.values()))
    ck("v2_changed_27", sum(x["changed"] for x in lines(f067 / "pack_mapping_v2.jsonl")) == 27)
    occupied = 0.0
    first_occupied = 0.0
    status_counts = Counter()
    for job in jobs:
        pid = job["id"]
        body = job["body"]
        rid = job["request_id"]
        ck("body_hash_" + rid, job["body_sha256"] == c.digest(body))
        ck("settings_" + rid, body.get("model") == c.MODELS["deepseek"] and body.get("enable_thinking") is True and body.get("reasoning_effort") == "high" and body.get("max_tokens") == 8192)
        payload = json.loads(body["messages"][1]["content"])
        ck("api_fields_" + rid, set(payload) == {"proposition", "reference"})
        if job["condition"] == "baseline_repeat":
            ck("same_baseline_body_" + rid, body == old[pid]["body"])
        elif job["condition"] == "added_repeat":
            ck("same_067_body_" + rid, body == short[pid]["body"])
        elif job["condition"] == "linebreak_presentation":
            formal_payload = json.loads(short[pid]["body"]["messages"][1]["content"])
            ck("linebreak_only_" + rid, payload["proposition"] == formal_payload["proposition"] and payload["reference"] == formal_payload["reference"].replace("\\n", "\n"))
        elif job["condition"] == "v2_baseline_repeat":
            ck("same_v2_baseline_body_" + rid, body == old[pid]["body"])
        elif job["condition"] == "v2_final_repeat":
            ck("same_v2_final_body_" + rid, body == v2_short[pid]["body"])
        folder = OUT / "attempts" / (hashlib.sha256(rid.encode()).hexdigest()[:24] + "_01")
        request_file, receipt_file = folder / "request.json", folder / "receipt.json"
        ck("request_exists_" + rid, request_file.exists())
        ck("receipt_exists_" + rid, receipt_file.exists())
        if not request_file.exists():
            continue
        request = json.loads(request_file.read_text(encoding="utf-8"))
        ck("request_body_" + rid, request["job"] == job and request["body_sha256"] == c.digest(body) and request["hard_cap_cny"] == 10.0)
        if receipt_file.exists():
            receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
            ck("receipt_request_hash_" + rid, receipt["request_sha256"] == c.sha(request_file))
            status = receipt["transport"].get("http_status")
            status_counts[str(status)] += 1
            cost = c.charge(job, receipt["transport"])
            occupied += cost
            if rid in first_ids:
                first_occupied += cost
        else:
            cost = float(request["reservation_cny"])
            occupied += cost
            if rid in first_ids:
                first_occupied += cost
    ck("budget_within_10", occupied <= 10 + 1e-9, occupied)
    ck("all_http200", status_counts == {"200": len(jobs)}, dict(status_counts))
    first_repeat_by_rid = {job["request_id"]: job for job in first_jobs}
    for pid, rid in v2_freeze["reused_exact_baseline_repeats"].items():
        ck("v2_reused_body_" + pid, first_repeat_by_rid[rid]["body"] == old[pid]["body"])
        reused_receipt = OUT / "attempts" / (hashlib.sha256(rid.encode()).hexdigest()[:24] + "_01") / "receipt.json"
        ck("v2_reused_receipt_" + pid, reused_receipt.exists() and json.loads(reused_receipt.read_text(encoding="utf-8"))["transport"].get("http_status") == 200)
    rows = list(csv.DictReader((f067 / "results.csv").open(encoding="utf-8-sig", newline="")))
    cohort = [{"proposition_id": row["id"], "subject_id": row["sid"], "human_gt": row["GT"]} for row in rows]
    preds = [{"proposition_id": row["id"], "verdict": row["baseline_pg"]} for row in rows]
    eval_baseline = evaluate(cohort, preds, profile="none", missing="error")
    ck("complete_236_baseline", eval_baseline["coverage"]["evaluated_n"] == 236)
    analysis = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))
    ck("analysis_v1_cost_matches", abs(analysis["cost"]["occupied_cny"] - first_occupied) < 1e-7)
    ck("analysis_diagnostic_cases", analysis["diagnostic_cases"] == 39)
    ck("no_reserved", analysis["reserved_used"] is False)
    analysis_v2 = json.loads((OUT / "analysis_v2_068.json").read_text(encoding="utf-8"))
    ck("analysis_v2_cost_matches", abs(analysis_v2["all_068_occupied_cny"] - occupied) < 1e-7)
    ck("v2_diagnostic_cases", analysis_v2["v2_changed_n"] == 27)
    ck("v2_no_reserved", analysis_v2["reserved_used"] is False)
    for rel in ("AGENTS.md", "docs/API_POLICY.md", "docs/aliyun/CURRENT.md", "docs/siliconflow_pool/README.md"):
        ck("policy_10_" + rel, "10元" in (ROOT / rel).read_text(encoding="utf-8"))
    result = {"status": "PASS" if all(x["status"] == "PASS" for x in checks) else "FAIL", "n_checks": len(checks), "n_fail": sum(x["status"] == "FAIL" for x in checks), "occupied_cny": occupied, "checks": checks}
    (OUT / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("status", "n_checks", "n_fail", "occupied_cny")}, ensure_ascii=False))
    if result["status"] != "PASS":
        print(json.dumps([x for x in checks if x["status"] == "FAIL"], ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
