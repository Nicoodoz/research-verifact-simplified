"""Freeze pre-registered exact repeats of every first-call successful A/D/C arm."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/069_final_pack_controlled_repair"
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
import common066 as c  # noqa: E402
import run069  # noqa: E402


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def main():
    if (OUT / "repeat_freeze.json").exists():
        raise RuntimeError("repeat already frozen")
    results = jsonl(OUT / "stage1_results.jsonl")
    prior = {(job["id"], job["arm"]): job for job in jsonl(OUT / "stage1_jobs.jsonl")}
    jobs = []
    for row in results:
        for arm in ("add_only", "delete_only", "combined_header"):
            answer = row["conditions"][arm]
            if answer.get("status") != "valid" or answer.get("pg") != row["GT"]:
                continue
            source = prior[(row["id"], arm)]
            job = {"request_id": f"069_repeat_{arm}_" + hashlib.sha256(row["id"].encode()).hexdigest()[:24],
                   "id": row["id"], "arm": arm + "_repeat2", "model_key": "deepseek", "body": source["body"],
                   "body_sha256": source["body_sha256"], "source_request_id": source["request_id"]}
            job["reservation_cny"] = c.bound(job)
            jobs.append(job)
    jobs.sort(key=lambda x: x["request_id"])
    assert len({job["request_id"] for job in jobs}) == len(jobs)
    with (OUT / "stage1_repeat_jobs.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for job in jobs:
            handle.write(json.dumps(job, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    old, _ = run069.state()
    used = sum(x["cost"] for x in old)
    bound = sum(c.bound(job) for job in jobs)
    freeze = {"stage": "stage1_positive_exact_repeats", "jobs": len(jobs), "prior_occupied_cny": used,
              "conservative_repeat_reservation_cny": bound, "combined_upper_cny": used + bound,
              "hard_cap_cny": 8.0, "dispatch_rule": "all positive first-call A/D/C in request-id order, stop before any send exceeding task cap",
              "jobs_sha256": hashlib.sha256((OUT / "stage1_repeat_jobs.jsonl").read_bytes()).hexdigest(),
              "stage1_analysis_sha256": c.sha(OUT / "stage1_analysis.json"), "GT_in_Judge_body": False}
    (OUT / "repeat_freeze.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(freeze, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
