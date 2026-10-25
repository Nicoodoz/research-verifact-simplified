"""Resume-safe paired Alibaba Judge runner with a ¥20 original-price hard cap."""
import concurrent.futures
import datetime
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/084_f4_coverage_validation"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/024_lambda2_transfer_validation"))
sys.path.insert(0, str(ROOT / "tasks/082_anchor_configuration_adaptation"))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config, load_config
import prepare082 as p

CAP = 20.0
MODEL = "deepseek-v4-flash-0731"
RETRYABLE = {0, 429, 500, 502, 503, 504}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, item):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(item, f, ensure_ascii=False, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def reserve(job):
    body = job["body"]
    return ((len(p.canonical(body).encode("utf-8")) + 2000) * 3 + body["max_tokens"] * 9) / 1e6


def charge(request, transport):
    if transport is None or transport.get("http_status") == 0:
        return request["reservation_cny"]
    if transport["http_status"] != 200:
        return 0.0
    try:
        payload = json.loads(transport["body_text"])
        usage = payload["usage"]
        inp, out = int(usage["prompt_tokens"]), int(usage["completion_tokens"])
        assert 0 <= inp <= len(p.canonical(request["job"]["body"]).encode("utf-8")) + 2000
        assert 0 <= out <= request["job"]["body"]["max_tokens"]
        return (inp * 3 + out * 9) / 1e6
    except (KeyError, TypeError, ValueError, AssertionError):
        return request["reservation_cny"]


def state():
    attempts = []
    success = {}
    count_by_rid = defaultdict(int)
    for path in sorted((OUT / "attempts").glob("*/request.json")):
        req = read(path)
        rp = path.parent / "receipt.json"
        receipt = read(rp) if rp.exists() else None
        if receipt is not None:
            assert receipt["request_sha256"] == sha(path)
        tr = receipt["transport"] if receipt else None
        row = {"attempt_id": req["attempt_id"], "request_id": req["job"]["request_id"],
               "id": req["job"]["id"], "sid": req["job"]["sid"], "arm": req["job"]["arm"],
               "attempt_no": req["attempt_no"], "http_status": tr.get("http_status") if tr else None,
               "original_price_or_unknown_reserved_cny": charge(req, tr),
               "request_source": path.relative_to(ROOT).as_posix(),
               "receipt_source": rp.relative_to(ROOT).as_posix() if receipt else None}
        attempts.append(row)
        count_by_rid[row["request_id"]] += 1
        if tr and tr["http_status"] == 200:
            assert row["request_id"] not in success
            success[row["request_id"]] = row
    return attempts, success, count_by_rid


def client():
    config = load_config(ROOT / ".env.aliyun")
    assert config.base_url == "https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    return DirectClient(Config(config.api_key, config.base_url, MODEL), timeout=240)


def audit_jobs():
    freeze = read(OUT / "freeze.json")
    assert freeze["status"] == "FROZEN_BEFORE_FIRST_084_API_AND_GT" and freeze["cap_original_cny"] == CAP
    assert freeze["jobs_sha256"] == sha(OUT / "main_jobs.jsonl")
    assert freeze["sample_sha256"] == sha(OUT / "sample_blind.jsonl")
    for rel, digest in freeze["source_sha256"].items():
        assert sha(ROOT / rel) == digest, rel
    jobs = [json.loads(s) for s in (OUT / "main_jobs.jsonl").open(encoding="utf-8") if s.strip()]
    assert len(jobs) == 360
    grouped = defaultdict(list)
    cli = client()
    for job in jobs:
        assert p.digest(job["body"]) == job["body_sha256"]
        body = job["body"]
        cli.validate(body)
        assert body["model"] == MODEL and body["enable_thinking"] is True
        assert body["reasoning_effort"] == "high" and body["temperature"] == 0 and body["max_tokens"] == 8192
        assert set(json.loads(body["messages"][1]["content"])) == {"proposition", "reference"}
        grouped[job["id"]].append(job)
    assert len(grouped) == 180 and all(len(group) == 2 and {j["arm"] for j in group} == {"B", "F4"} for group in grouped.values())
    return list(grouped.values())


def attempt(cli, job, number):
    aid = job["request_id"] + f"__try{number}"
    path = OUT / "attempts" / hashlib.sha256(aid.encode()).hexdigest()[:24]
    path.mkdir(parents=True, exist_ok=False)
    req = {"created_utc": now(), "attempt_id": aid, "attempt_no": number,
           "job": job, "reservation_cny": reserve(job), "task_cap_original_cny": CAP,
           "price_source": "https://help.aliyun.com/en/model-studio/model-pricing"}
    write_new(path / "request.json", req)
    start = time.monotonic()
    try:
        tr = cli.send(job["body"])
        assert isinstance(tr, dict) and "http_status" in tr
    except Exception as exc:
        tr = {"http_status": 0, "failure_phase": "unknown_after_attempt", "error_type": type(exc).__name__, "body_text": ""}
    tr["client_elapsed_seconds"] = time.monotonic() - start
    write_new(path / "receipt.json", {"request_sha256": sha(path / "request.json"), "transport": tr})
    if tr["http_status"] == 200:
        try:
            payload = json.loads(tr["body_text"])
            if payload.get("model") != MODEL:
                raise RuntimeError("model_mismatch")
        except (ValueError, TypeError, AttributeError) as exc:
            raise RuntimeError("malformed_provider_envelope") from exc
    return tr


def run_pair(group, counts, successful):
    cli = client()
    statuses = []
    for job in group:
        rid = job["request_id"]
        if rid in successful:
            statuses.append((rid, "historical_084_success"))
            continue
        past = counts[rid]
        assert past < 3
        for number in range(past + 1, 4):
            tr = attempt(cli, job, number)
            status = tr["http_status"]
            statuses.append((rid, status))
            if status == 200:
                break
            if status not in RETRYABLE:
                raise RuntimeError(f"nonretryable_http_{status}")
            if number == 3:
                raise RuntimeError(f"recovery_exhausted_{status}")
            time.sleep(3 * 2 ** (number - 1))
    return statuses


def run(workers=4):
    assert 1 <= workers <= 4
    groups = audit_jobs()
    (OUT / "attempts").mkdir(exist_ok=True)
    previous, successful, counts = state()
    used = sum(x["original_price_or_unknown_reserved_cny"] for x in previous)
    pending = [group for group in groups if not all(j["request_id"] in successful for j in group)]
    lock = OUT / "run.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    running = {}
    in_flight = 0.0
    complete = 0
    last_print = time.monotonic()
    stop = None
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while pending or running:
                while pending and len(running) < workers and stop is None:
                    group = pending[0]
                    # Reserve six maximum-length attempts per pair. This pays for
                    # both arms and all retries before the pair is dispatched.
                    reservation = sum(reserve(j) * (3 - counts[j["request_id"]]) for j in group if j["request_id"] not in successful)
                    if used + in_flight + reservation > CAP + 1e-9:
                        stop = "pair_reservation_would_exceed_hard_cap"
                        break
                    pending.pop(0)
                    future = pool.submit(run_pair, group, counts, successful)
                    running[future] = (group, reservation)
                    in_flight += reservation
                if not running:
                    break
                done, _ = concurrent.futures.wait(running, timeout=5, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    group, reservation = running.pop(future)
                    in_flight -= reservation
                    current, successful, counts = state()
                    active_rids = {j["request_id"] for active_group, _ in running.values() for j in active_group}
                    used = sum(x["original_price_or_unknown_reserved_cny"] for x in current if x["request_id"] not in active_rids)
                    previous = current
                    try:
                        future.result()
                    except Exception as exc:
                        stop = f"{type(exc).__name__}:{str(exc)[:80]}"
                    if all(j["request_id"] in successful for j in group):
                        complete += 1
                if time.monotonic() - last_print >= 30:
                    print(json.dumps({"completed_new_pairs": complete, "pending_pairs": len(pending),
                                      "running_pairs": len(running), "used_or_unknown_cny": round(used, 6),
                                      "inflight_reserved_cny": round(in_flight, 6), "stop": stop}), flush=True)
                    last_print = time.monotonic()
        print(json.dumps({"completed_new_pairs": complete, "pending_pairs": len(pending),
                          "original_used_or_unknown_cny": round(used, 6), "stop": stop}), flush=True)
        if stop or pending or len(successful) != 360:
            raise RuntimeError(stop or "incomplete_pair_queue")
    finally:
        lock.unlink()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--preflight":
        groups = audit_jobs()
        print(json.dumps({"preflight": "PASS", "pairs": len(groups),
                          "first_pair_six_attempt_reservation_cny": round(sum(reserve(j) * 3 for j in groups[0]), 6)}))
    else:
        run(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
