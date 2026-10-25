"""Single-attempt shared 8 CNY executor for the frozen 069 stages."""
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
OUT = ROOT / "outputs/069_final_pack_controlled_repair"
CAP = 8.0
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
import common066 as c  # noqa: E402
sys.path.insert(0, str(ROOT / "tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient  # noqa: E402
from verifact_research.inference.aliyun import Config, load_config  # noqa: E402


def now():
    return datetime.now(timezone.utc).isoformat()


def load_jobs(stage):
    paths = {"stage1": ("stage1_jobs.jsonl", "freeze.json"), "repeat": ("stage1_repeat_jobs.jsonl", "repeat_freeze.json"), "stage2": ("stage2_jobs.jsonl", "stage2_freeze.json")}
    job_file, freeze_file = paths[stage]
    raw = (OUT / job_file).read_bytes()
    jobs = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    freeze = json.loads((OUT / freeze_file).read_text(encoding="utf-8"))
    digest = hashlib.sha256(raw).hexdigest()
    if stage == "stage1":
        source_hashes = {key.replace("\\", "/"): value for key, value in freeze["source_sha256"].items()}
        assert digest == source_hashes[f"outputs/069_final_pack_controlled_repair/{job_file}"]
        assert len(jobs) == freeze["jobs"] == 48
    else:
        assert digest == freeze["jobs_sha256"]
        assert len(jobs) == freeze["jobs"]
    assert len({job["request_id"] for job in jobs}) == len(jobs)
    assert all(job["body_sha256"] == c.digest(job["body"]) for job in jobs)
    return jobs


def state():
    attempts, done = [], {}
    if not (OUT / "attempts").exists():
        return attempts, done
    for request_file in sorted((OUT / "attempts").glob("*/request.json")):
        request = json.loads(request_file.read_text(encoding="utf-8"))
        job = request["job"]
        receipt_file = request_file.parent / "receipt.json"
        tr = json.loads(receipt_file.read_text(encoding="utf-8"))["transport"] if receipt_file.exists() else None
        amount = c.charge(job, tr) if tr else float(request["reservation_cny"])
        attempts.append({"request_id": job["request_id"], "cost": amount, "http_status": tr.get("http_status") if tr else None})
        if tr and tr.get("http_status") == 200:
            if job["request_id"] in done:
                raise RuntimeError("duplicate HTTP200")
            done[job["request_id"]] = {"job": job, "transport": tr}
    return attempts, done


def run(stage, workers=3):
    jobs = load_jobs(stage)
    attempts, done = state()
    old_counts = Counter(x["request_id"] for x in attempts)
    pending = []
    for job in jobs:
        rid = job["request_id"]
        if rid in done:
            continue
        if old_counts[rid]:
            raise RuntimeError(f"unresolved request, no automatic retry: {rid}")
        pending.append(job)
    used = sum(row["cost"] for row in attempts)
    assert used <= CAP
    cfg = load_config(ROOT / ".env.aliyun")
    client = DirectClient(Config(cfg.api_key, cfg.base_url, c.MODELS["deepseek"]), timeout=180)
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
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while queue or inflight:
                while queue and len(inflight) < workers and not errors:
                    job = queue.popleft()
                    amount = c.bound(job)
                    if used + reserved + amount > CAP + 1e-9:
                        queue.appendleft(job)
                        break
                    rid = job["request_id"]
                    dest = OUT / "attempts" / (hashlib.sha256(rid.encode()).hexdigest()[:24] + "_01")
                    if dest.exists():
                        raise RuntimeError("attempt collision")
                    dest.mkdir(parents=True)
                    record = {"created_utc": now(), "stage": stage, "job": job, "attempt": 1, "reservation_cny": amount, "prior_used_cny": used, "prior_inflight_reserved_cny": reserved, "hard_cap_cny": CAP, "body_sha256": c.digest(job["body"])}
                    (dest / "request.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
                    reserved += amount
                    inflight[pool.submit(client.send, job["body"])] = (job, dest, amount)
                if not inflight:
                    break
                ready, _ = concurrent.futures.wait(inflight, timeout=10, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in ready:
                    job, dest, amount = inflight.pop(future)
                    reserved -= amount
                    try:
                        tr = future.result()
                    except Exception as exc:
                        tr = {"http_status": 0, "body_text": "", "headers": {}, "outcome_unknown": True, "exception_type": type(exc).__name__}
                    (dest / "receipt.json").write_text(json.dumps({"request_sha256": c.sha(dest / "request.json"), "transport": tr}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
                    used += c.charge(job, tr)
                    if tr.get("http_status") != 200:
                        errors.append({"request_id": job["request_id"], "http_status": tr.get("http_status")})
                print(f"069 stage={stage} receipts={len(list((OUT/'attempts').glob('*/receipt.json')))} occupied={used:.4f} inflight={len(inflight)} remaining={len(queue)}", flush=True)
        stage_ids = {job["request_id"] for job in jobs}
        stage_attempts = [row for row in state()[0] if row["request_id"] in stage_ids]
        summary = {"completed_utc": now(), "stage": stage, "planned": len(jobs), "attempts": len(stage_attempts), "http200": sum(row["http_status"] == 200 for row in stage_attempts), "all_task_occupied_cny": sum(row["cost"] for row in state()[0]), "remaining_unsent": len(queue), "errors": errors, "hard_cap_cny": CAP}
        (OUT / f"execution_{stage}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        if errors:
            raise RuntimeError("non200/unknown response; no automatic retry")
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["stage1", "repeat", "stage2"])
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    run(args.stage, args.workers)
