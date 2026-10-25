"""Resume the 360 frozen R1 requests after the user's formal authorization.

The first HTTP200 response for each logical request is permanent. This runner
does not load GT, V4 predictions, or any evaluator.
"""
from __future__ import annotations

import argparse
import json
import time

import preflight as p


def frozen_jobs():
    profile = p.read(p.PUBLIC / "profile.json")
    if profile["model"] != p.MODEL or len(profile["jobs"]) != 360:
        raise ValueError("wrong frozen profile")
    if not (p.PUBLIC / "forecast.json").exists():
        raise ValueError("A/B forecast missing")
    jobs = p.rows(p.PRIVATE / "jobs.jsonl")
    if len(jobs) != 360:
        raise ValueError("private frozen jobs missing")
    indexed = {x["request_id"]: x for x in profile["jobs"]}
    if len(indexed) != 360:
        raise ValueError("duplicate profile requests")
    for job in jobs:
        meta = indexed.get(job["request_id"])
        if meta is None or meta["body_sha256"] != p.digest(p.encoded(job["body"])):
            raise ValueError("request differs from frozen body")
        if (meta["id"], meta["sid"], meta["arm"]) != (job["id"], job["sid"], job["arm"]):
            raise ValueError("frozen ID/patient/arm mismatch")
    if [(j["id"], j["arm"]) for j in jobs] != [(j["id"], j["arm"]) for j in p.jobs()]:
        raise ValueError("old source ordering changed")
    return jobs, indexed


def success(job):
    found = p.attempts(job["request_id"])
    valid = [(receipt, folder) for _, receipt, folder in found if receipt["http_status"] == 200]
    if len(valid) > 1:
        raise ValueError("duplicate HTTP200")
    return valid[0] if valid else None


def run():
    jobs, indexed = frozen_jobs()
    initial = [(j["id"], j["arm"]) for j in jobs if success(j)]
    expected = [(j["id"], j["arm"]) for _, j in p.selected_jobs()]
    if len(initial) < 3 or not set(expected).issubset(set(initial)):
        raise ValueError("three A/B success positions missing")
    if not (p.PUBLIC / "formal_authorization.json").exists():
        p.put_json(p.PUBLIC / "formal_authorization.json", {
            "created_utc": p.stamp(), "scope": "remaining frozen 085 Valdemardi R1-B/F4 slots",
            "user_authorized_formal": True, "user_message": "2026-09-27 继续085 Valdemardi R1-70B正式实验",
            "initial_HTTP200_slots": len(initial), "A_B_slots_included": expected,
            "frozen_profile_sha256": p.sha(p.PUBLIC / "profile.json"),
            "forecast_sha256": p.sha(p.PUBLIC / "forecast.json"),
            "GT_read": False, "client_concurrency": 1,
            "hourly_price_required_for_inference": False,
            "successful_HTTP200_never_retried": True})
    started = time.monotonic()
    complete = len(initial)
    for index, job in enumerate(jobs, 1):
        existing = success(job)
        receipt, folder = existing if existing else p.invoke(job, "formal")
        observation = p.inspect(folder, indexed[job["request_id"]]["local_input_tokens"])
        if not observation["local_server_prompt_tokens_match"] or not observation["full_output_budget_fits_20k"]:
            raise RuntimeError("frozen prompt token/context condition changed; HTTP200 retained, STOP")
        if existing is None:
            complete += 1
            if complete % 10 == 0 or complete == 360:
                print(json.dumps({"completed": complete, "total": 360,
                                  "last_id": job["id"], "last_arm": job["arm"],
                                  "elapsed_wall_seconds": round(time.monotonic() - started, 1)},
                                 ensure_ascii=False), flush=True)
    if complete != 360 or sum(success(j) is not None for j in jobs) != 360:
        raise RuntimeError("formal cohort incomplete")
    if not (p.PUBLIC / "formal_completion.json").exists():
        actual_ab = sum(any(request["stage"] == "B" and receipt["http_status"] == 200
                            for request, receipt, _ in p.attempts(j["request_id"])) for j in jobs)
        actual_formal = sum(any(request["stage"] == "formal" and receipt["http_status"] == 200
                                for request, receipt, _ in p.attempts(j["request_id"])) for j in jobs)
        p.put_json(p.PUBLIC / "formal_completion.json", {
            "completed_utc": p.stamp(), "frozen_slots": 360,
            "initial_AB_HTTP200_slots": actual_ab,
            "new_HTTP200_slots": actual_formal,
            "success_positions_at_this_process_start": len(initial),
            "all_HTTP200": True, "GT_read": False,
            "runner_wall_seconds_excluding_initial_AB": time.monotonic() - started,
            "profile_sha256": p.sha(p.PUBLIC / "profile.json")})
    print(json.dumps({"status": "FORMAL_360_HTTP200_COMPLETE", "GT_read": False}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("valdemardi-vllm-0.10.1.1",), required=True)
    args = parser.parse_args()
    run()
