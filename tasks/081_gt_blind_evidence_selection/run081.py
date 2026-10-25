"""Append-only Alibaba executor for one frozen 081 stage; no labels or predictions imported."""
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

import blind081 as b

sys.path.insert(0, str(b.ROOT / "src"))
sys.path.insert(0, str(b.ROOT / "tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config, load_config

CAP = 20.0
RETRYABLE = {0, 429, 500, 502, 503, 504}
STAGES = ("u_plan", "u_compose", "t_plan", "t_compose", "judge", "repeat")


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


def price(job):
    return (3.0, 12.0) if job["body"]["model"] == "qwen3.8-27b" else (3.0, 9.0)


def reserve(job):
    ip, op = price(job)
    # Deliberately overbooks prompt bytes as if every byte were a token.
    return ((len(json.dumps(job["body"], ensure_ascii=False, sort_keys=True).encode()) + 2000) * ip
            + job["body"]["max_tokens"] * op) / 1e6


def charge(request, transport):
    if transport is None or transport.get("http_status") == 0:
        return request["reservation_cny"]
    if transport["http_status"] != 200:
        return 0.0
    try:
        usage = json.loads(transport["body_text"])["usage"]
        ip, op = price(request["job"])
        n_in, n_out = int(usage["prompt_tokens"]), int(usage["completion_tokens"])
        assert 0 <= n_in <= len(json.dumps(request["job"]["body"], ensure_ascii=False).encode()) + 2000
        assert 0 <= n_out <= request["job"]["body"]["max_tokens"]
        return (n_in * ip + n_out * op) / 1e6
    except (KeyError, TypeError, ValueError, AssertionError, json.JSONDecodeError):
        return request["reservation_cny"]


def state():
    attempts, success = [], {}
    for path in sorted((b.OUT / "attempts").glob("*/request.json")):
        req = read(path)
        receipt_path = path.parent / "receipt.json"
        receipt = read(receipt_path) if receipt_path.exists() else None
        if receipt:
            assert receipt["request_sha256"] == b.sha(path)
        tr = receipt["transport"] if receipt else None
        row = {"request_id": req["job"]["request_id"], "attempt_id": req["attempt_id"],
               "attempt_no": req["attempt_no"], "stage": req["stage"],
               "http_status": tr.get("http_status") if tr else None,
               "cost_cny": charge(req, tr), "path": str(path.relative_to(b.ROOT)).replace("\\", "/")}
        attempts.append(row)
        if tr and tr["http_status"] == 200:
            assert row["request_id"] not in success, "successful request resent"
            success[row["request_id"]] = {"job": req["job"], "transport": tr, "attempt": row}
    return attempts, success


def jobs(stage):
    assert stage in STAGES
    path = b.OUT / f"{stage}_jobs.jsonl"
    frozen = read(b.OUT / f"{stage}_freeze.json")
    assert frozen["stage"] == stage and frozen["jobs_sha256"] == b.sha(path)
    rows = b.lines(str(path.relative_to(b.ROOT)).replace("\\", "/"))
    assert len(rows) == len({x["request_id"] for x in rows})
    assert all(x["stage"].lower() == stage and x["body_sha256"] == b.digest(x["body"]) for x in rows)
    return rows


def run(stage, workers=4):
    assert 1 <= workers <= 4
    job_rows = jobs(stage)
    attempts, success = state()
    by_id = {}
    for a in attempts:
        by_id.setdefault(a["request_id"], []).append(a)
    pending = deque()
    for job in job_rows:
        rid = job["request_id"]
        if rid in success:
            continue
        past = sorted(by_id.get(rid, []), key=lambda a: a["attempt_no"])
        assert len(past) < 3, (rid, "retry exhausted")
        assert not past or past[-1]["http_status"] in RETRYABLE, (rid, "nonretryable")
        pending.append((job, len(past) + 1, 0.0))
    cfg = load_config(b.ROOT / ".env.aliyun")
    assert cfg.base_url == "https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    clients = {model: DirectClient(Config(cfg.api_key, cfg.base_url, model), timeout=240)
               for model in ("qwen3.8-27b", "deepseek-v4-flash-0731")}
    for job, _, _ in pending:
        assert job["body"]["model"] in clients
        clients[job["body"]["model"]].validate(job["body"])
    used = sum(x["cost_cny"] for x in attempts)
    running, in_flight, sent, last_print = {}, 0.0, 0, time.monotonic()
    lock = b.OUT / "run.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    stop_reason = None
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while pending or running:
                for _ in range(len(pending)):
                    if len(running) >= workers or stop_reason:
                        break
                    job, number, ready = pending.popleft()
                    if ready > time.monotonic():
                        pending.append((job, number, ready))
                        continue
                    reservation = reserve(job)
                    if used + in_flight + reservation > CAP + 1e-9:
                        stop_reason = "cap_before_complete"
                        pending.appendleft((job, number, ready))
                        break
                    aid = job["request_id"] + f"__try{number}"
                    apath = b.OUT / "attempts" / hashlib.sha256(aid.encode()).hexdigest()[:24]
                    apath.mkdir(parents=True, exist_ok=False)
                    req = {"created_utc": now(), "stage": stage, "job": job,
                           "attempt_id": aid, "attempt_no": number,
                           "reservation_cny": reservation, "used_before_cny": used + in_flight,
                           "cap_cny": CAP}
                    write_new(apath / "request.json", req)
                    future = pool.submit(clients[job["body"]["model"]].send, job["body"])
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
                    write_new(apath / "receipt.json", {"request_sha256": b.sha(apath / "request.json"),
                                                       "transport": tr})
                    actual = charge(read(apath / "request.json"), tr)
                    used += actual
                    in_flight -= reservation
                    if tr["http_status"] in RETRYABLE and number < 3:
                        delay = min(45, 3 * 2 ** (number - 1))
                        pending.append((job, number + 1, time.monotonic() + delay))
                    elif tr["http_status"] != 200:
                        stop_reason = f"request_failed_{tr['http_status']}"
                if time.monotonic() - last_print > 30:
                    print(json.dumps({"stage": stage, "new_attempts": sent, "pending": len(pending),
                                      "running": len(running), "used_or_reserved_cny": round(used + in_flight, 6),
                                      "stop_reason": stop_reason}), flush=True)
                    last_print = time.monotonic()
        print(json.dumps({"stage": stage, "new_attempts": sent, "remaining": len(pending),
                          "used_cny": round(used, 6), "stop_reason": stop_reason}), flush=True)
        if stop_reason or pending:
            raise RuntimeError(stop_reason or "incomplete")
    finally:
        lock.unlink()


if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4)
