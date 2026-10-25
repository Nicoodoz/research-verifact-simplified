"""Append-only bounded 074 executor with finite transport recovery."""
from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import json
import os
import sys
import time
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/074_anchor_dynamic_examples"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/024_lambda2_transfer_validation"))
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
from transport_direct024 import DirectClient  # noqa: E402
from verifact_research.inference.aliyun import Config, load_config  # noqa: E402
import common053 as c53  # noqa: E402

CAP = 20.0
MODEL = "deepseek-v4-flash-0731"
PRICE_INPUT, PRICE_OUTPUT = 3.0, 9.0
RETRYABLE = {0, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def lines(path):
    return [json.loads(s) for s in Path(path).read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def save(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def bound(body):
    return ((len(canonical(body).encode("utf-8")) + 2000) * PRICE_INPUT + body["max_tokens"] * PRICE_OUTPUT) / 1e6


def charge(transport, reservation):
    if transport is None:
        return reservation
    status = transport.get("http_status")
    if status == 0:
        return reservation
    if status != 200:
        return 0.0
    try:
        usage = json.loads(transport["body_text"])["usage"]
        inp, out = int(usage["prompt_tokens"]), int(usage["completion_tokens"])
        assert inp >= 0 and out >= 0
        return (inp * PRICE_INPUT + out * PRICE_OUTPUT) / 1e6
    except (KeyError, ValueError, AssertionError, TypeError):
        return reservation


def check_frozen(stage):
    freeze = read(OUT / "freeze.json")
    assert freeze["status"] == "FROZEN_BEFORE_074_API" and freeze["cap_cny"] == CAP and freeze["model"] == MODEL
    for relative, expected in freeze["source_sha256"].items():
        assert sha(ROOT / relative) == expected, relative
    for name, expected in freeze["artifact_sha256"].items():
        assert sha(OUT / name) == expected, name
    if stage != "pilot":
        extra = read(OUT / f"{stage}_freeze.json")
        assert extra["stage"] == stage and extra["source_freeze_sha256"] == sha(OUT / "freeze.json")
        assert extra["jobs_sha256"] == sha(OUT / f"{stage}_jobs.jsonl")
        assert extra["decision_sha256"] == sha(OUT / extra["decision_file"])
    return freeze


def client():
    original = load_config(ROOT / ".env.aliyun")
    assert original.base_url == "https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    return DirectClient(Config(original.api_key, original.base_url, MODEL), timeout=240)


def attempt_state():
    attempts, answered = [], {}
    for path in sorted((OUT / "attempts").glob("*/request.json")):
        request = read(path)
        receipt_path = path.parent / "receipt.json"
        if receipt_path.exists():
            receipt = read(receipt_path)
            assert receipt["request_sha256"] == sha(path)
            transport = receipt["transport"]
        else:
            transport = None
        job = request["job"]
        attempt = {"logical_id": job["request_id"], "attempt_id": request["attempt_id"],
                   "attempt_no": request["attempt_no"], "stage": job["stage"], "arm": job["arm"],
                   "id": job["id"], "http_status": transport.get("http_status") if transport else None,
                   "cost_cny": charge(transport, request["reservation_cny"]),
                   "request_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                   "receipt_path": str(receipt_path.relative_to(ROOT)).replace("\\", "/") if receipt_path.exists() else None}
        attempts.append(attempt)
        if transport and transport.get("http_status") == 200:
            parsed = c53.parse_response(transport, True, True)
            assert parsed.get("model_returned") == MODEL, (job["request_id"], parsed.get("model_returned"))
            assert job["request_id"] not in answered, "successful answer repeated"
            answered[job["request_id"]] = {"job": job, "parsed": parsed, "transport": transport,
                                             "attempt_id": request["attempt_id"]}
    return attempts, answered


def jobs_for(stage):
    path = OUT / f"{stage}_jobs.jsonl"
    jobs = lines(path)
    assert len(jobs) == len({j["request_id"] for j in jobs})
    assert all(j["stage"] == stage and j["body_sha256"] == digest(j["body"]) for j in jobs)
    return jobs


def run(stage, workers=6):
    assert stage in ("pilot", "adaptive", "confirmation")
    assert 1 <= workers <= 6
    check_frozen(stage)
    jobs = jobs_for(stage)
    attempts, answered = attempt_state()
    by_logical = {}
    for attempt in attempts:
        by_logical.setdefault(attempt["logical_id"], []).append(attempt)
    for values in by_logical.values():
        assert len(values) <= MAX_ATTEMPTS
        assert len({x["attempt_no"] for x in values}) == len(values)
    pending = []
    for job in jobs:
        rid = job["request_id"]
        if rid in answered:
            continue
        past = sorted(by_logical.get(rid, []), key=lambda x: x["attempt_no"])
        if past and (past[-1]["http_status"] not in RETRYABLE and past[-1]["http_status"] is not None):
            raise RuntimeError("Non-retryable prior response for " + rid)
        if len(past) >= MAX_ATTEMPTS:
            raise RuntimeError("Recovery attempts exhausted for " + rid)
        pending.append((job, len(past) + 1, 0.0))
    cli = client()
    for job, _, _ in pending:
        cli.validate(job["body"])
        assert job["body"]["model"] == MODEL and job["body"]["enable_thinking"] is True
    used = sum(x["cost_cny"] for x in attempts)
    running, queue = {}, deque(pending)
    in_flight = 0.0
    completed_new, failure_streak, success_streak = 0, 0, 0
    current_workers = workers
    stop_reason = None
    lock = OUT / "run.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while queue or running:
                queue_length = len(queue)
                for _ in range(queue_length):
                    if len(running) >= current_workers or stop_reason:
                        break
                    job, attempt_no, ready_at = queue.popleft()
                    if ready_at > time.monotonic():
                        queue.append((job, attempt_no, ready_at))
                        continue
                    reservation = bound(job["body"])
                    if used + in_flight + reservation > CAP + 1e-10:
                        stop_reason = "task_cap"
                        queue.appendleft((job, attempt_no, ready_at))
                        break
                    attempt_id = job["request_id"] + f"__try{attempt_no}"
                    path = OUT / "attempts" / hashlib.sha256(attempt_id.encode()).hexdigest()[:24]
                    path.mkdir(parents=True, exist_ok=False)
                    save(path / "request.json", {"created_utc": now(), "job": job, "attempt_id": attempt_id,
                                                "attempt_no": attempt_no, "reservation_cny": reservation,
                                                "prior_used_or_reserved_cny": used + in_flight,
                                                "task_cap_cny": CAP,
                                                "price_source": "https://help.aliyun.com/en/model-studio/model-pricing"})
                    in_flight += reservation
                    future = pool.submit(cli.send, job["body"])
                    running[future] = (job, attempt_no, path, reservation)
                if not running:
                    if stop_reason:
                        break
                    if queue:
                        time.sleep(0.5)
                    continue
                ready, _ = concurrent.futures.wait(running, timeout=5, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in ready:
                    job, attempt_no, path, reservation = running.pop(future)
                    in_flight -= reservation
                    try:
                        transport = future.result()
                    except Exception as exc:
                        transport = {"http_status": 0, "body_text": "", "outcome_unknown": True,
                                     "transport_diagnostic": {"exception_type": type(exc).__name__},
                                     "started_utc": None, "ended_utc": now(), "headers": {}}
                    save(path / "receipt.json", {"request_sha256": sha(path / "request.json"), "transport": transport})
                    used += charge(transport, reservation)
                    completed_new += 1
                    status = transport.get("http_status")
                    if status == 200:
                        parsed = c53.parse_response(transport, True, True)
                        if parsed.get("model_returned") != MODEL:
                            stop_reason = "unexpected_model"
                        failure_streak = 0
                        success_streak += 1
                        if success_streak >= 6:
                            current_workers = min(workers, current_workers + 1)
                            success_streak = 0
                    elif status in RETRYABLE and attempt_no < MAX_ATTEMPTS:
                        failure_streak += 1
                        success_streak = 0
                        if failure_streak >= 2:
                            current_workers = 1
                        delay = 2 if attempt_no == 1 else 8
                        queue.append((job, attempt_no + 1, time.monotonic() + delay))
                    else:
                        stop_reason = "nonrecoverable_or_attempts_exhausted"
                    if completed_new % 20 == 0 or status != 200:
                        print(json.dumps({"stage": stage, "new_attempts": completed_new,
                                          "remaining_logical_or_running": len(queue) + len(running),
                                          "used_and_inflight_cny": round(used + in_flight, 6),
                                          "last_http_status": status, "workers": current_workers}), flush=True)
        summary = {"stage": stage, "created_utc": now(), "planned_logical": len(jobs),
                   "previous_answered": len(jobs) - len(pending), "new_attempts": completed_new,
                   "remaining_queue": len(queue), "used_or_reserved_cny": used, "cap_cny": CAP,
                   "stop_reason": stop_reason}
        save(OUT / f"{stage}_execution_{len(attempts)+completed_new:04}.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("pilot", "adaptive", "confirmation"))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    run(args.stage, args.workers)
