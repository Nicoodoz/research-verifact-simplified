"""Freeze six explicit same-body retries for user-authorized 071 continuation."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/071_judge_icl_feasibility"
sys.path.insert(0, str(ROOT / "tasks/071_judge_icl_feasibility"))
import run071  # noqa: E402


def save(path, obj):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


run071.check_frozen()
diagnosis = run071.read(OUT / "execution_diagnosis.json")
assert diagnosis["task_status"] == "STOPPED_AFTER_TRANSPORT_UNKNOWN" and diagnosis["main_unknown"] == 6
attempts, terminal = run071.state()
original = {j["request_id"]: j for j in run071.lines(OUT / "main_jobs.jsonl")}
unknown = diagnosis["unknown_receipts"]
assert len(unknown) == 6 and len({x["request_id"] for x in unknown}) == 6
jobs, mapping = [], []
for row in unknown:
    rid = row["request_id"]
    assert rid in original and rid not in terminal
    job = original[rid]
    receipt = run071.read(ROOT / row["receipt_path"])
    assert receipt["transport"]["http_status"] == 0 and receipt["transport"]["outcome_unknown"] is True
    retry = dict(job)
    retry["request_id"] = rid.replace("071_", "071_recovery_", 1)
    retry["stage"] = "recovery"
    retry["source_request_id"] = rid
    assert retry["body_sha256"] == job["body_sha256"] == run071.digest(retry["body"])
    jobs.append(retry)
    mapping.append({"source_request_id": rid, "recovery_request_id": retry["request_id"],
                    "body_sha256": job["body_sha256"], "original_receipt_path": row["receipt_path"]})
jobs.sort(key=lambda j: hashlib.sha256(j["source_request_id"].encode()).hexdigest())
save(OUT / "continuation_001_freeze.json", {"prior_task_used_or_reserved_cny": diagnosis["cumulative_actual_plus_unknown_reserve_cny"],
                                           "cap_cny": 20, "recovery_n": 6, "unsent_n": 174,
                                           "user_authorization": "continue 071; same frozen design and cumulative budget",
                                           "source_protocol_sha256": run071.sha(ROOT / "tasks/071_judge_icl_feasibility/protocol.md"),
                                           "source_freeze_sha256": run071.sha(OUT / "freeze.json"),
                                           "continuation_addendum_sha256": run071.sha(ROOT / "tasks/071_judge_icl_feasibility/continuation_001.md")})
with (OUT / "recovery_jobs.jsonl").open("x", encoding="utf-8", newline="\n") as f:
    for job in jobs:
        f.write(run071.canonical(job) + "\n")
save(OUT / "recovery_mapping.json", mapping)
print(json.dumps({"recovery_n": len(jobs), "body_hashes_preserved": True,
                  "cumulative_before_send_cny": diagnosis["cumulative_actual_plus_unknown_reserve_cny"]}, ensure_ascii=False))
