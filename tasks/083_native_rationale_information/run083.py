"""Resumable, append-only Qwen extraction with a shared ¥20 original-price cap."""
from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import json
import os
import sys
import time
from collections import deque
from pathlib import Path

import inventory083 as base
import prepare083 as prep

ROOT, OUT = base.ROOT, base.OUT
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config, load_config

CAP = 20.0
MODEL = prep.MODEL
RETRYABLE = {0, 429, 500, 502, 503, 504}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def jobs():
    plan = read(OUT / "preflight_and_cost_plan.json")
    path = OUT / "extraction_jobs.jsonl"
    assert base.digest(path.read_bytes()) == plan["jobs_sha256"]
    rows = base.lines("outputs/083_native_rationale_information/extraction_jobs.jsonl")
    assert len(rows) == plan["unique_extraction_requests"]
    assert len({x["request_id"] for x in rows}) == len(rows)
    for job in rows:
        assert job["body_sha256"] == base.digest(prep.canonical(job["body"]).encode())
        assert job["body"]["model"] == MODEL
        assert job["body"]["enable_thinking"] is False
        assert job["body"]["response_format"] == {"type": "json_object"}
        payload = json.loads(job["body"]["messages"][1]["content"])
        assert set(payload) == {"rationale_text"}
        assert base.digest(payload["rationale_text"].encode()) == job["cleaned_sha256"]
    return rows


def reserve(job):
    body = job["body"]
    return ((len(prep.canonical(body).encode("utf-8")) + 2000) * .2 + body["max_tokens"] * 2) / 1e6


def charge(request, transport):
    if transport is None or transport.get("http_status") == 0:
        return request["reservation_cny"]
    if transport["http_status"] != 200:
        return 0.0
    try:
        response = json.loads(transport["body_text"])
        usage = response["usage"]
        inp, out = int(usage["prompt_tokens"]), int(usage["completion_tokens"])
        assert 0 <= inp <= len(prep.canonical(request["job"]["body"]).encode()) + 2000
        assert 0 <= out <= request["job"]["body"]["max_tokens"]
        return (inp * .2 + out * 2) / 1e6
    except (KeyError, ValueError, TypeError, AssertionError):
        return request["reservation_cny"]


def state():
    attempts, success = [], {}
    for path in sorted((OUT / "attempts").glob("*/request.json")):
        req = read(path)
        receipt_path = path.parent / "receipt.json"
        receipt = read(receipt_path) if receipt_path.exists() else None
        if receipt:
            assert receipt["request_sha256"] == base.digest(path.read_bytes())
        transport = receipt["transport"] if receipt else None
        row = {"request_id": req["job"]["request_id"], "attempt_id": req["attempt_id"],
               "attempt_no": req["attempt_no"],
               "http_status": transport.get("http_status") if transport else None,
               "original_price_cny": charge(req, transport),
               "request_source": path.relative_to(ROOT).as_posix(),
               "receipt_source": receipt_path.relative_to(ROOT).as_posix() if receipt else None}
        attempts.append(row)
        if transport and transport["http_status"] == 200:
            assert row["request_id"] not in success, "successful logical request repeated"
            response = json.loads(transport["body_text"])
            assert response.get("model") == MODEL, (row["request_id"], response.get("model"))
            success[row["request_id"]] = {"job": req["job"], "transport": transport,
                                          "attempt": row}
    return attempts, success


def client():
    original = load_config(ROOT / ".env.aliyun")
    assert original.base_url == "https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    return DirectClient(Config(original.api_key, original.base_url, MODEL), timeout=180)


def run(workers=6, limit=None):
    assert 1 <= workers <= 8
    all_jobs = jobs()
    attempts, answered = state()
    by_id = {}
    for row in attempts:
        by_id.setdefault(row["request_id"], []).append(row)
    pending = deque()
    for job in all_jobs:
        rid = job["request_id"]
        if rid in answered:
            continue
        past = sorted(by_id.get(rid, []), key=lambda x: x["attempt_no"])
        assert len(past) < 3, (rid, "retries exhausted")
        assert not past or past[-1]["http_status"] in RETRYABLE, (rid, "not retryable")
        pending.append((job, len(past) + 1, 0.0))
    cli = client()
    for job, _, _ in pending:
        cli.validate(job["body"])
    used = sum(x["original_price_cny"] for x in attempts)
    running, inflight, sent = {}, 0.0, 0
    last_print, streak, active_workers, stop_reason = time.monotonic(), 0, workers, None
    lock = OUT / "run.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while pending or running:
                for _ in range(len(pending)):
                    if len(running) >= active_workers or stop_reason or (limit is not None and sent >= limit):
                        break
                    job, number, ready = pending.popleft()
                    if ready > time.monotonic():
                        pending.append((job, number, ready))
                        continue
                    reservation = reserve(job)
                    if used + inflight + reservation > CAP + 1e-9:
                        stop_reason = "original_price_cap"
                        pending.appendleft((job, number, ready))
                        break
                    aid = job["request_id"] + f"__try{number}"
                    apath = OUT / "attempts" / hashlib.sha256(aid.encode()).hexdigest()[:24]
                    apath.mkdir(parents=True, exist_ok=False)
                    request = {"created_utc": now(), "job": job, "attempt_id": aid,
                               "attempt_no": number, "reservation_cny": reservation,
                               "used_or_reserved_before_cny": used + inflight,
                               "task_cap_original_cny": CAP,
                               "price_source": "https://help.aliyun.com/zh/model-studio/qwen3-5-flash"}
                    save(apath / "request.json", request)
                    future = pool.submit(cli.send, job["body"])
                    running[future] = (job, number, apath, reservation)
                    inflight += reservation
                    sent += 1
                if not running:
                    if stop_reason or (limit is not None and sent >= limit):
                        break
                    time.sleep(.5)
                    continue
                done, _ = concurrent.futures.wait(running, timeout=5, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    job, number, apath, reservation = running.pop(future)
                    tr = future.result()
                    assert isinstance(tr, dict) and "http_status" in tr
                    save(apath / "receipt.json", {"request_sha256": base.digest((apath / "request.json").read_bytes()),
                                                  "transport": tr})
                    actual = charge(read(apath / "request.json"), tr)
                    used += actual
                    inflight -= reservation
                    if tr["http_status"] == 200:
                        native = json.loads(tr["body_text"])
                        if native.get("model") != MODEL:
                            stop_reason = "model_returned_mismatch"
                        else:
                            streak = 0
                    elif tr["http_status"] in RETRYABLE and number < 3:
                        streak += 1
                        pending.append((job, number + 1, time.monotonic() + min(60, 3 * 2 ** (number - 1))))
                        if streak >= 3:
                            active_workers = max(1, active_workers // 2)
                    else:
                        stop_reason = f"request_failed_{tr['http_status']}"
                if time.monotonic() - last_print > 30:
                    print(json.dumps({"sent": sent, "pending": len(pending), "running": len(running),
                                      "active_workers": active_workers,
                                      "used_or_reserved_cny": round(used + inflight, 6),
                                      "stop_reason": stop_reason}), flush=True)
                    last_print = time.monotonic()
        print(json.dumps({"sent": sent, "answered": len(state()[1]),
                          "remaining": len(pending), "original_used_cny": round(used, 6),
                          "stop_reason": stop_reason}), flush=True)
        if stop_reason or (limit is None and pending):
            raise RuntimeError(stop_reason or "incomplete")
    finally:
        lock.unlink()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 6,
        int(sys.argv[2]) if len(sys.argv) > 2 else None)
