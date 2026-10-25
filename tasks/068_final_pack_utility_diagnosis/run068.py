"""Single-attempt, resumable 068 same-input repeats under one 10 CNY cap."""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sys
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/068_final_pack_utility_diagnosis"
sys.path.insert(0, str(ROOT / "tasks/067_conservative_evidence_packing"))
import common067 as c  # noqa: E402
sys.path.insert(0, str(ROOT / "tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient  # noqa: E402
from verifact_research.inference.aliyun import Config, load_config  # noqa: E402

CAP = 10.0
PRICE_URL = "https://help.aliyun.com/zh/model-studio/model-pricing"


def now():
    return datetime.now(timezone.utc).isoformat()


def load_jobs(stage="repeat"):
    job_names = {"repeat": "jobs_002.jsonl", "presentation": "presentation_jobs.jsonl", "v2": "jobs_v2_068.jsonl"}
    freeze_names = {"repeat": "freeze_003.json", "presentation": "presentation_freeze.json", "v2": "freeze_v2_068.json"}
    jobs_path = OUT / job_names[stage]
    freeze_path = OUT / freeze_names[stage]
    raw = jobs_path.read_bytes()
    jobs = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    assert hashlib.sha256(raw).hexdigest() == freeze["jobs_sha256"]
    if stage == "repeat":
        assert len(jobs) == freeze["all_jobs"] == 78
        assert sum(c.bound(job) for job in jobs) <= 9.5
    else:
        assert len(jobs) == freeze["planned_jobs"]
    assert all(job["body_sha256"] == c.digest(job["body"]) for job in jobs)
    return jobs


def freeze_plan():
    if (OUT / "freeze_003.json").exists():
        raise RuntimeError("freeze_003 already exists")
    forensic = json.loads((OUT / "forensics.json").read_text(encoding="utf-8"))
    assert forensic["all_baseline_pids_empty"] and forensic["all_audit_current_pack_ids_empty"]
    previous = json.loads((OUT / "freeze_002.json").read_text(encoding="utf-8"))
    raw = (OUT / "jobs_002.jsonl").read_bytes()
    jobs = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    assert len(jobs) == 78 and all(job["condition"] != "presentation_only" for job in jobs)
    bound = sum(c.bound(job) for job in jobs)
    assert bound <= 9.5
    frozen = {
        "created_utc": now(),
        "scope": "same-input repeats of original 052 baseline and actual 067 replacement pack",
        "all_jobs": len(jobs),
        "groups": previous["historical_groups"],
        "repeat_cases": previous["diagnostic_cases"],
        "hard_cap_cny": CAP,
        "total_conservative_reservation_cny": bound,
        "unknown_buffer_cny": CAP - bound,
        "model": c.MODELS["deepseek"],
        "price_peak_cny_per_million_input_output": list(c.PRICES["deepseek"]),
        "price_source": PRICE_URL,
        "price_checked_utc": now(),
        "price_region": "China North 2 (Beijing)",
        "jobs_sha256": hashlib.sha256(raw).hexdigest(),
        "forensics_sha256": c.sha(OUT / "forensics.json"),
        "protocol_sha256": c.sha(ROOT / "tasks/068_final_pack_utility_diagnosis/protocol.md"),
        "amendment_002_sha256": c.sha(ROOT / "tasks/068_final_pack_utility_diagnosis/protocol_amendment_002.md"),
        "GT_in_body": False,
        "reserved_used": False,
        "selection_after_new_answers": False,
    }
    (OUT / "freeze_003.json").write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: frozen[k] for k in ("all_jobs", "repeat_cases", "hard_cap_cny", "total_conservative_reservation_cny", "unknown_buffer_cny")}, ensure_ascii=False))


def state():
    attempts = []
    done = {}
    base = OUT / "attempts"
    if not base.exists():
        return attempts, done
    for request_file in sorted(base.glob("*/request.json")):
        request = json.loads(request_file.read_text(encoding="utf-8"))
        job = request["job"]
        receipt_file = request_file.parent / "receipt.json"
        transport = json.loads(receipt_file.read_text(encoding="utf-8"))["transport"] if receipt_file.exists() else None
        cost = c.charge(job, transport) if transport else float(request["reservation_cny"])
        attempts.append({"request_id": job["request_id"], "cost": cost, "http_status": transport.get("http_status") if transport else None})
        if transport and transport.get("http_status") == 200:
            if job["request_id"] in done:
                raise RuntimeError("duplicate successful answer")
            done[job["request_id"]] = transport
    return attempts, done


def run(workers=3, stage="repeat"):
    jobs = load_jobs(stage)
    attempts, done = state()
    prior_counts = Counter(x["request_id"] for x in attempts)
    pending = []
    for job in jobs:
        rid = job["request_id"]
        if rid in done:
            continue
        if prior_counts[rid]:
            raise RuntimeError(f"unresolved prior attempt: {rid}; no automatic retry")
        pending.append(job)
    used = sum(x["cost"] for x in attempts)
    if used > CAP:
        raise RuntimeError("prior spend exceeds cap")
    config = load_config(ROOT / ".env.aliyun")
    client = DirectClient(Config(config.api_key, config.base_url, c.MODELS["deepseek"]), timeout=180)
    for job in pending:
        assert job["body"]["model"] == c.MODELS["deepseek"]
        client.validate(job["body"])
    lock = OUT / "live.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    queue = deque(pending)
    inflight = {}
    reserved = 0.0
    errors = []
    budget_exhausted = False
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while queue or inflight:
                while queue and len(inflight) < workers and not errors:
                    job = queue.popleft()
                    reservation = c.bound(job)
                    if used + reserved + reservation > CAP + 1e-9:
                        if stage == "repeat":
                            raise RuntimeError("068 hard budget cap")
                        queue.appendleft(job)
                        budget_exhausted = True
                        break
                    rid = job["request_id"]
                    dest = OUT / "attempts" / (hashlib.sha256(rid.encode()).hexdigest()[:24] + "_01")
                    if dest.exists():
                        raise RuntimeError("attempt path already exists")
                    dest.mkdir(parents=True)
                    request = {
                        "created_utc": now(), "job": job, "attempt": 1,
                        "reservation_cny": reservation, "prior_used_cny": used,
                        "prior_inflight_reserved_cny": reserved, "hard_cap_cny": CAP,
                        "body_sha256": c.digest(job["body"]),
                    }
                    (dest / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
                    reserved += reservation
                    future = pool.submit(client.send, job["body"])
                    inflight[future] = (job, dest, reservation)
                if not inflight:
                    break
                ready, _ = concurrent.futures.wait(inflight, timeout=10, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in ready:
                    job, dest, reservation = inflight.pop(future)
                    reserved -= reservation
                    try:
                        transport = future.result()
                    except Exception as exc:
                        transport = {"http_status": 0, "body_text": "", "headers": {}, "outcome_unknown": True, "exception_type": type(exc).__name__}
                    (dest / "receipt.json").write_text(json.dumps({"request_sha256": c.sha(dest / "request.json"), "transport": transport}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
                    used += c.charge(job, transport)
                    if transport.get("http_status") != 200:
                        errors.append({"request_id": job["request_id"], "http_status": transport.get("http_status")})
                print(f"068 receipts={len(list((OUT / 'attempts').glob('*/receipt.json')))} used_or_reserved={used:.4f} inflight={len(inflight)} remaining={len(queue)}", flush=True)
        stage_ids = {job["request_id"] for job in jobs}
        stage_attempts = [x for x in state()[0] if x["request_id"] in stage_ids]
        summary = {"completed_utc": now(), "stage": stage, "planned": len(jobs), "attempts": len(stage_attempts), "receipts": sum(x["http_status"] is not None for x in stage_attempts), "used_or_reserved_cny_all_068": used, "errors": errors, "budget_exhausted": budget_exhausted, "remaining_unsent": len(queue), "price_source": PRICE_URL}
        filename = {"repeat": "execution.json", "presentation": "execution_presentation.json", "v2": "execution_v2.json"}[stage]
        (OUT / filename).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        if errors:
            raise RuntimeError("non-200/unknown result; stopped without retry")
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["freeze", "run", "run-presentation", "run-v2"])
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.mode == "freeze":
        freeze_plan()
    else:
        run(args.workers, "presentation" if args.mode == "run-presentation" else "v2" if args.mode == "run-v2" else "repeat")
