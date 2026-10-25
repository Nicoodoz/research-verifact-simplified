"""Append-only exact-body cached Alibaba executor with a ¥50 original-price hard cap."""
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

import inventory082 as i
import prepare082 as p

ROOT, OUT = i.ROOT, i.OUT
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config, load_config

CAP = 50.0
MODEL = "deepseek-v4-flash-0731"
STAGES = ("screen_B", "train_F4", "eval", "repeat")
RETRYABLE = {None, 0, 429, 500, 502, 503, 504}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def reserve(job):
    body = job["body"]
    return ((len(p.canonical(body).encode("utf-8")) + 2000) * 3
            + body["max_tokens"] * 9) / 1e6


def charge(request, transport):
    if transport is None or transport.get("http_status") == 0:
        return request["reservation_cny"]
    if transport["http_status"] != 200:
        return 0.0
    try:
        u = json.loads(transport["body_text"])["usage"]
        inp, out = int(u["prompt_tokens"]), int(u["completion_tokens"])
        assert 0 <= inp <= len(p.canonical(request["job"]["body"]).encode("utf-8")) + 2000
        assert 0 <= out <= request["job"]["body"]["max_tokens"]
        return (inp * 3 + out * 9) / 1e6
    except (KeyError, TypeError, ValueError, AssertionError):
        return request["reservation_cny"]


def state():
    attempts, success = [], {}
    for path in sorted((OUT / "attempts").glob("*/request.json")):
        req = read(path)
        receipt_path = path.parent / "receipt.json"
        receipt = read(receipt_path) if receipt_path.exists() else None
        if receipt:
            assert receipt["request_sha256"] == p.sha(path)
        tr = receipt["transport"] if receipt else None
        row = {"request_id": req["job"]["request_id"], "attempt_id": req["attempt_id"],
               "attempt_no": req["attempt_no"], "stage": req["stage"], "arm": req["job"]["arm"],
               "id": req["job"]["id"], "http_status": tr.get("http_status") if tr else None,
               "original_price_cny": charge(req, tr),
               "request_source": path.relative_to(ROOT).as_posix(),
               "receipt_source": receipt_path.relative_to(ROOT).as_posix() if receipt else None}
        attempts.append(row)
        if tr and tr["http_status"] == 200:
            assert row["request_id"] not in success, "successful logical answer repeated"
            success[row["request_id"]] = {"job": req["job"], "transport": tr,
                                           "attempt": row, "mode": "new"}
    return attempts, success


def cache():
    rows = i.lines("outputs/082_anchor_configuration_adaptation/cache_index.jsonl")
    assert p.sha(OUT / "cache_index.jsonl") == read(OUT / "cost_plan.json")["cache_index_sha256"]
    indexed = {}
    for x in rows:
        path = ROOT / x["receipt_source"]
        assert p.sha(path) == x["receipt_sha256"]
        receipt = read(path)
        assert receipt["request_sha256"] == x["request_sha256"]
        assert receipt["transport"]["http_status"] == 200
        indexed[x["body_sha256"]] = {"transport": receipt["transport"],
                                      "request_source": x["request_source"],
                                      "receipt_source": x["receipt_source"]}
    return indexed


def jobs(stage):
    assert stage in STAGES
    path = OUT / (stage + "_jobs.jsonl")
    freeze = read(OUT / (stage + "_freeze.json"))
    assert freeze["stage"] == stage and freeze["status"] == "FROZEN_BEFORE_STAGE_API"
    assert freeze["jobs_sha256"] == p.sha(path)
    assert freeze["blind_freeze_sha256"] == p.sha(OUT / "blind_freeze.json")
    assert freeze["cost_plan_sha256"] == p.sha(OUT / "cost_plan.json")
    rows = i.lines("outputs/082_anchor_configuration_adaptation/" + path.name)
    assert len(rows) == len({j["request_id"] for j in rows})
    assert all(j["stage"] == stage and j["body_sha256"] == p.digest(j["body"]) for j in rows)
    return rows


def answers(stage):
    job_rows = jobs(stage)
    attempts, local = state()
    historical = cache() if stage != "repeat" else {}
    out = {}
    for job in job_rows:
        rid = job["request_id"]
        if rid in local:
            out[rid] = local[rid]
        elif job["body_sha256"] in historical:
            h = historical[job["body_sha256"]]
            out[rid] = dict(job=job, transport=h["transport"], mode="historical_exact",
                            request_source=h["request_source"], receipt_source=h["receipt_source"])
    return attempts, out


def client():
    original = load_config(ROOT / ".env.aliyun")
    assert original.base_url == "https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    return DirectClient(Config(original.api_key, original.base_url, MODEL), timeout=240)


def run(stage, workers=4):
    assert 1 <= workers <= 4
    job_rows = jobs(stage)
    attempts, answered = answers(stage)
    by_id = {}
    for a in attempts:
        by_id.setdefault(a["request_id"], []).append(a)
    pending = deque()
    for job in job_rows:
        rid = job["request_id"]
        if rid in answered:
            continue
        past = sorted(by_id.get(rid, []), key=lambda x: x["attempt_no"])
        assert len(past) < 3, (rid, "recovery exhausted")
        assert not past or past[-1]["http_status"] in RETRYABLE, (rid, "nonretryable")
        pending.append((job, len(past) + 1, 0.0))
    cli = client()
    for job, _, _ in pending:
        body = job["body"]
        cli.validate(body)
        assert body["model"] == MODEL and body["enable_thinking"] is True and body["reasoning_effort"] == "high"
        assert set(json.loads(body["messages"][1]["content"])) == {"proposition", "reference"}
    used = sum(x["original_price_cny"] for x in attempts)
    in_flight, sent, running, last_print, failure_streak, active_workers = 0.0, 0, {}, time.monotonic(), 0, workers
    stop_reason = None
    lock = OUT / "run.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while pending or running:
                for _ in range(len(pending)):
                    if len(running) >= active_workers or stop_reason:
                        break
                    job, number, ready = pending.popleft()
                    if ready > time.monotonic():
                        pending.append((job, number, ready))
                        continue
                    reservation = reserve(job)
                    if used + in_flight + reservation > CAP + 1e-9:
                        stop_reason = "task_original_price_cap"
                        pending.appendleft((job, number, ready))
                        break
                    aid = job["request_id"] + f"__try{number}"
                    apath = OUT / "attempts" / hashlib.sha256(aid.encode()).hexdigest()[:24]
                    apath.mkdir(parents=True, exist_ok=False)
                    req = {"created_utc": now(), "stage": stage, "job": job,
                           "attempt_id": aid, "attempt_no": number,
                           "reservation_cny": reservation, "used_or_reserved_before_cny": used + in_flight,
                           "task_cap_original_cny": CAP,
                           "price_source": "https://help.aliyun.com/en/model-studio/model-pricing"}
                    write_new(apath / "request.json", req)
                    future = pool.submit(cli.send, job["body"])
                    running[future] = (job, number, apath, reservation)
                    in_flight += reservation
                    sent += 1
                if not running:
                    if stop_reason:
                        break
                    time.sleep(0.5)
                    continue
                done, _ = concurrent.futures.wait(running, timeout=5, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    job, number, apath, reservation = running.pop(future)
                    tr = future.result()
                    assert isinstance(tr, dict) and "http_status" in tr
                    write_new(apath / "receipt.json", {"request_sha256": p.sha(apath / "request.json"),
                                                       "transport": tr})
                    actual = charge(read(apath / "request.json"), tr)
                    used += actual
                    in_flight -= reservation
                    if tr["http_status"] in RETRYABLE and number < 3:
                        failure_streak += 1
                        delay = min(60, 3 * 2 ** (number - 1))
                        pending.append((job, number + 1, time.monotonic() + delay))
                        if failure_streak >= 3:
                            active_workers = max(1, active_workers // 2)
                    elif tr["http_status"] != 200:
                        stop_reason = f"request_failed_{tr['http_status']}"
                    else:
                        failure_streak = 0
                if time.monotonic() - last_print > 30:
                    print(json.dumps({"stage": stage, "new_attempts": sent, "pending": len(pending),
                                      "running": len(running), "active_workers": active_workers,
                                      "original_used_or_reserved_cny": round(used + in_flight, 6),
                                      "stop_reason": stop_reason}), flush=True)
                    last_print = time.monotonic()
        print(json.dumps({"stage": stage, "new_attempts": sent, "remaining": len(pending),
                          "original_used_cny": round(used, 6), "stop_reason": stop_reason}), flush=True)
        if stop_reason or pending:
            raise RuntimeError(stop_reason or "incomplete")
    finally:
        lock.unlink()


if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4)
