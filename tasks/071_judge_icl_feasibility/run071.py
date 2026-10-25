"""Bounded append-only DeepSeek 0731 execution for frozen 071 jobs."""
from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import json
import os
import sys
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/071_judge_icl_feasibility"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/024_lambda2_transfer_validation"))
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
from transport_direct024 import DirectClient  # noqa: E402
from verifact_research.inference.aliyun import Config, load_config  # noqa: E402
import common053 as c53  # noqa: E402

MODEL = "deepseek-v4-flash-0731"
CAP = 20.0
PRIOR_RESERVED = 0.60  # Conservative accounting for preceding key checks.
PRICE_INPUT, PRICE_OUTPUT = 3.0, 9.0  # Busy-time CNY per million tokens.
VALID = ("valid", "valid_with_format_anomaly")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def lines(path):
    return [json.loads(s) for s in Path(path).read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def bound(body):
    return ((len(canonical(body).encode("utf-8")) + 2000) * PRICE_INPUT + body["max_tokens"] * PRICE_OUTPUT) / 1e6


def charge(transport, reservation):
    try:
        if transport["http_status"] != 200:
            return reservation if transport["outcome_unknown"] else 0.0
        usage = json.loads(transport["body_text"])["usage"]
        i, o = int(usage["prompt_tokens"]), int(usage["completion_tokens"])
        assert i >= 0 and o >= 0
        return (i * PRICE_INPUT + o * PRICE_OUTPUT) / 1e6
    except (KeyError, ValueError, TypeError, AssertionError):
        return reservation


def state():
    attempts = []
    terminal = {}
    for path in sorted((OUT / "attempts").glob("*/request.json")):
        request = read(path)
        job = request["job"]
        receipt_path = path.parent / "receipt.json"
        if receipt_path.exists():
            receipt = read(receipt_path)
            assert receipt["request_sha256"] == sha(path)
            transport = receipt["transport"]
        else:
            transport = None
        cost = charge(transport, request["reservation_cny"]) if transport else request["reservation_cny"]
        attempts.append({"id": job["request_id"], "stage": job["stage"], "cost_cny": cost,
                         "http_status": transport.get("http_status") if transport else None,
                         "request_path": str(path.relative_to(ROOT)).replace("\\", "/")})
        if transport and transport.get("http_status") == 200:
            assert job["request_id"] not in terminal
            terminal[job["request_id"]] = {"job": job, "transport": transport,
                                           "parsed": c53.parse_response(transport, True, True)}
    return attempts, terminal


def resolved_state():
    """Expose successful explicit recovery receipts as aliases, retaining originals."""
    attempts, terminal = state()
    mapping_path = OUT / "recovery_mapping.json"
    if mapping_path.exists():
        by_attempt = {x["id"]: x for x in attempts}
        originals = {j["request_id"]: j for j in lines(OUT / "main_jobs.jsonl")}
        for row in read(mapping_path):
            old, new = row["source_request_id"], row["recovery_request_id"]
            assert by_attempt[old]["http_status"] == 0 and old not in terminal
            assert originals[old]["body_sha256"] == row["body_sha256"]
            if new in terminal:
                assert terminal[new]["job"]["body_sha256"] == row["body_sha256"]
                terminal[old] = {**terminal[new], "recovered_by_request_id": new}
    return attempts, terminal


def check_frozen():
    freeze = read(OUT / "freeze.json")
    assert freeze["status"] == "FROZEN_BEFORE_071_API" and freeze["cap_cny"] == CAP
    for relative, expected in freeze["source_sha256"].items():
        assert sha(ROOT / relative) == expected, relative
    assert len(lines(OUT / "evaluation_blind.jsonl")) == 96
    assert len(lines(OUT / "examples.jsonl")) == 4
    assert len(lines(OUT / "main_jobs.jsonl")) == 288
    continuation = OUT / "continuation_001_freeze.json"
    if continuation.exists():
        entry = read(continuation)
        assert entry["cap_cny"] == CAP and entry["recovery_n"] == 6 and entry["unsent_n"] == 174
        assert entry["source_protocol_sha256"] == sha(ROOT / "tasks/071_judge_icl_feasibility/protocol.md")
        assert entry["source_freeze_sha256"] == sha(OUT / "freeze.json")
        assert entry["continuation_addendum_sha256"] == sha(ROOT / "tasks/071_judge_icl_feasibility/continuation_001.md")
    return freeze


def client():
    existing = load_config(ROOT / ".env.aliyun")
    assert existing.base_url == "https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    return DirectClient(Config(existing.api_key, existing.base_url, MODEL), timeout=240)


def jobs_for(stage):
    if stage == "preflight":
        body = read(OUT / "preflight_body.json")
        return [{"request_id": "071_preflight_001", "stage": stage, "body": body, "body_sha256": digest(body)}]
    if stage == "main":
        return lines(OUT / "main_jobs.jsonl")
    if stage == "recovery":
        assert read(OUT / "continuation_001_freeze.json")["recovery_n"] == 6
        return lines(OUT / "recovery_jobs.jsonl")
    if stage == "repeat":
        gate = read(OUT / "stage1_gate.json")
        assert gate["stage2_authorized_by_frozen_gate"] is True
        return lines(OUT / "repeat_jobs.jsonl")
    raise ValueError(stage)


def run(stage, workers=6):
    check_frozen()
    attempts, terminal = resolved_state()
    by_id = Counter(x["id"] for x in attempts)
    if stage != "preflight":
        pre = terminal.get("071_preflight_001")
        assert pre is not None and pre["parsed"]["status"] in VALID and pre["parsed"].get("reasoning_present")
    all_jobs = jobs_for(stage)
    pending = []
    for job in all_jobs:
        rid = job["request_id"]
        if rid in terminal:
            continue
        if by_id[rid]:
            raise RuntimeError("Unresolved previous attempt; refusing resend: " + rid)
        assert digest(job["body"]) == job["body_sha256"]
        pending.append(job)
    if stage == "preflight" and not pending:
        print("Preflight already complete")
        return
    if stage == "repeat":
        assert all(j["request_id"] in terminal for j in lines(OUT / "main_jobs.jsonl"))
    cli = client()
    for job in pending:
        cli.validate(job["body"])
        assert job["body"]["model"] == MODEL and job["body"]["enable_thinking"] is True
    used = PRIOR_RESERVED + sum(x["cost_cny"] for x in attempts)
    inflight_res = 0.0
    queue = deque(pending)
    running = {}
    lock = OUT / "run.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    nnew = 0
    stop = False
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while queue or running:
                while queue and len(running) < workers and not stop:
                    job = queue[0]
                    reservation = bound(job["body"])
                    if used + inflight_res + reservation > CAP:
                        stop = True
                        break
                    queue.popleft()
                    path = OUT / "attempts" / f"{hashlib.sha256(job['request_id'].encode()).hexdigest()[:24]}_01"
                    path.mkdir(parents=True, exist_ok=False)
                    save(path / "request.json", {"created_utc": now(), "job": job,
                                                         "reservation_cny": reservation,
                                                         "task_cap_cny": CAP,
                                                         "prior_used_reserved_cny": used + inflight_res,
                                                         "price_basis": "https://help.aliyun.com/en/model-studio/model-routing"})
                    inflight_res += reservation
                    future = pool.submit(cli.send, job["body"])
                    running[future] = (job, path, reservation)
                if not running:
                    break
                ready, _ = concurrent.futures.wait(running, timeout=10,
                    return_when=concurrent.futures.FIRST_COMPLETED)
                for future in ready:
                    job, path, reservation = running.pop(future)
                    inflight_res -= reservation
                    try:
                        transport = future.result()
                    except Exception as exc:
                        transport = {"http_status": 0, "body_text": "", "outcome_unknown": True,
                                     "transport_error_type": type(exc).__name__, "headers": {}}
                    save(path / "receipt.json", {"request_sha256": sha(path / "request.json"), "transport": transport})
                    used += charge(transport, reservation)
                    nnew += 1
                    if transport.get("http_status") != 200:
                        stop = True
                    if nnew % 20 == 0 or stop:
                        print(json.dumps({"stage": stage, "completed_new": nnew,
                                          "pending": len(queue) + len(running),
                                          "used_reserved_cny": round(used + inflight_res, 5),
                                          "last_http_status": transport.get("http_status")}), flush=True)
        summary = {"stage": stage, "created_utc": now(), "planned": len(all_jobs), "already_complete": len(all_jobs)-len(pending),
                   "completed_new": nnew, "remaining_unsent": len(queue), "used_reserved_cny": used,
                   "cap_cny": CAP, "stop_reason": "non200_or_budget" if stop else None}
        save(OUT / f"{stage}_execution_{len(attempts)+nnew:04}.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("preflight", "recovery", "main", "repeat"))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    run(args.stage, args.workers)
