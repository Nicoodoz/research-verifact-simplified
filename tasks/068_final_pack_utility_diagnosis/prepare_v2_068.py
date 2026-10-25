"""Freeze v2 same-input repeats and reuse exact earlier baseline repeats."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/068_final_pack_utility_diagnosis"
P067 = ROOT / "outputs/067_conservative_evidence_packing"
sys.path.insert(0, str(ROOT / "tasks/067_conservative_evidence_packing"))
import common067 as c  # noqa: E402


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def attempt_folder(rid):
    return OUT / "attempts" / (hashlib.sha256(rid.encode()).hexdigest()[:24] + "_01")


def main():
    if (OUT / "freeze_v2_068.json").exists():
        raise RuntimeError("v2 already frozen")
    forensic = json.loads((OUT / "forensics_v2.json").read_text(encoding="utf-8"))
    assert forensic["changed"] == 27 and forensic["mapped_baseline_pids_nonempty"]
    changed = {x["id"]: x for x in jsonl(P067 / "pack_mapping_v2.jsonl") if x["changed"]}
    short = {x["id"]: x for x in jsonl(P067 / "stage2v2_jobs.jsonl")}
    baseline = {x["id"]: x for x in jsonl(ROOT / "outputs/052_first_tier_validation/main_jobs.jsonl") if x["condition"] == "T-S"}
    v1_repeats = {x["id"]: x for x in jsonl(OUT / "jobs_002.jsonl") if x["condition"] == "baseline_repeat"}
    assert len(changed) == len(short) == 27
    jobs, reused = [], {}
    for pid in sorted(changed, key=lambda x: hashlib.sha256(x.encode()).hexdigest()):
        body = baseline[pid]["body"]
        previous = v1_repeats.get(pid)
        if previous and previous["body"] == body and (attempt_folder(previous["request_id"]) / "receipt.json").exists():
            rec = json.loads((attempt_folder(previous["request_id"]) / "receipt.json").read_text(encoding="utf-8"))
            assert rec["transport"].get("http_status") == 200
            reused[pid] = previous["request_id"]
        else:
            rid = "068_v2_baseline_" + hashlib.sha256(pid.encode()).hexdigest()[:24]
            jobs.append({"request_id": rid, "id": pid, "condition": "v2_baseline_repeat", "model_key": "deepseek", "body": body, "body_sha256": c.digest(body), "conservative_reservation_cny": c.bound({"model_key": "deepseek", "body": body})})
        final = short[pid]["body"]
        assert final["model"] == c.MODELS["deepseek"] and final["enable_thinking"] is True and final["reasoning_effort"] == "high"
        rid = "068_v2_final_" + hashlib.sha256(pid.encode()).hexdigest()[:24]
        jobs.append({"request_id": rid, "id": pid, "condition": "v2_final_repeat", "model_key": "deepseek", "body": final, "body_sha256": c.digest(final), "conservative_reservation_cny": c.bound({"model_key": "deepseek", "body": final})})
    with (OUT / "jobs_v2_068.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for job in jobs:
            handle.write(json.dumps(job, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    # Preserve all prior 068 charges and unknown reservations in the same task ledger.
    prior_occupied = 0.0
    for request in (OUT / "attempts").glob("*/request.json"):
        record = json.loads(request.read_text(encoding="utf-8"))
        receipt = request.parent / "receipt.json"
        prior_occupied += c.charge(record["job"], json.loads(receipt.read_text(encoding="utf-8"))["transport"]) if receipt.exists() else float(record["reservation_cny"])
    bound = sum(c.bound(job) for job in jobs)
    assert prior_occupied + bound <= 10.0, f"v2 would exceed task cap: {prior_occupied}+{bound}"
    freeze = {
        "task": "068 v2 independent branch diagnosis",
        "selected_changed_cases": len(changed),
        "reused_exact_baseline_repeats": reused,
        "new_baseline_repeat_jobs": sum(x["condition"] == "v2_baseline_repeat" for x in jobs),
        "new_v2_final_repeat_jobs": sum(x["condition"] == "v2_final_repeat" for x in jobs),
        "planned_jobs": len(jobs),
        "prior_068_occupied_cny": prior_occupied,
        "new_conservative_reservation_cny": bound,
        "combined_before_send_upper_cny": prior_occupied + bound,
        "hard_cap_cny": 10.0,
        "price_peak_cny_per_million_input_output": list(c.PRICES["deepseek"]),
        "price_source": "https://help.aliyun.com/zh/model-studio/model-pricing",
        "jobs_sha256": hashlib.sha256((OUT / "jobs_v2_068.jsonl").read_bytes()).hexdigest(),
        "v2_mapping_sha256": c.sha(P067 / "pack_mapping_v2.jsonl"),
        "v2_judge_jobs_sha256": c.sha(P067 / "stage2v2_jobs.jsonl"),
        "protocol_amendment_sha256": c.sha(ROOT / "tasks/068_final_pack_utility_diagnosis/protocol_amendment_004.md"),
        "GT_in_API": False,
        "reserved_used": False,
    }
    (OUT / "freeze_v2_068.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: freeze[k] for k in ("selected_changed_cases", "new_baseline_repeat_jobs", "new_v2_final_repeat_jobs", "planned_jobs", "prior_068_occupied_cny", "new_conservative_reservation_cny", "combined_before_send_upper_cny")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
