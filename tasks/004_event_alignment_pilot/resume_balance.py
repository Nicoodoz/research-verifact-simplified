"""Explicit service-only amendment: recover unanswered HTTP 402 after recharge."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import json
import os
from pathlib import Path
import threading

import live
import pilot
import siliconflow as sf


def balance_error(transport: dict) -> bool:
    r = transport.get("response_json")
    return (transport.get("http_status") == 402 and isinstance(r, dict) and r.get("code") == 30001
        and r.get("data") is None and not r.get("choices") and not r.get("usage"))


def register(run: Path) -> dict:
    live.load_jobs(run)  # Existing frozen code, input and settings remain immutable.
    path = run / "balance_recovery.json"
    if path.exists():
        result = json.loads(path.read_text(encoding="utf-8"))
        pilot.require(result["recovery_code_sha256"] == pilot.digest_file(Path(__file__)), "Recovery code changed")
        for name, digest in result["original_balance_receipts_sha256"].items():
            pilot.require(pilot.digest_file(run / name) == digest, "Original billing failure was modified")
        return result
    bad, hashes = [], {}
    for p in sorted((run / "receipts").glob("*.json")):
        value = pilot.strict_json(p.read_text(encoding="utf-8"))
        if balance_error(value["transport"]):
            pilot.require(value["normalized"]["status"] == "failed" and value["normalized"]["verdict"] is None, "Balance error unexpectedly has answer")
            bad.append(value["sequence"])
            hashes[p.relative_to(run).as_posix()] = pilot.digest_file(p)
    pilot.require(bool(bad) and len(bad) == len(set(bad)), "Expected original unanswered billing failures")
    result = dict(registered_utc=sf.utcnow(), stage="service_only_balance_recovery_amendment",
        reason="Original runner treated 402 as terminal but did not stop scheduling; account exhausted. No model answer exists for these requests.",
        user_recharge_confirmed=True, original_real_input_authorization_still_applies=True,
        source_manifest_sha256=pilot.digest_file(run / "manifest.json"), target_sequences=sorted(bad),
        original_balance_receipts_sha256=hashes, recovery_code_sha256=pilot.digest_file(Path(__file__)),
        model_prompt_reference_generation_budget_changed=False, existing_successes_regenerated=False,
        service_exception="HTTP 402 with code 30001 and no choices/usage is recoverable after recharge; originals remain byte-identical",
        fail_fast="On another balance failure stop unsent work; up to concurrency=8 already in-flight requests may finish",
        inference_attempt_limit="Original maximum 5 attempts per logical request, including original 402",
        interruption_effect="Later unanswered inputs run after recharge; retain actual timings and model ID/fingerprint, do not assume unchanged backend revision")
    pilot.write_json(path, result)
    return result


class BalancePaused(Exception):
    pass


class StopOnBalance:
    def __init__(self, client, stop):
        self.client, self.stop = client, stop

    def send(self, body):
        result = self.client.send(body)
        if balance_error(result):
            self.stop.set()
        return result


class Recovery(live.Execution):
    def __init__(self, run, jobs, config, inputs, amendment, client=None):
        super().__init__(run, jobs, config, inputs, client)
        self.stop = threading.Event()
        self.client = StopOnBalance(self.client, self.stop)
        targets = set(amendment["target_sequences"])
        # Change retry interpretation in memory only. Original receipts and their
        # recorded service_retryable=false flags are not edited or rewritten.
        self.receipts = copy.deepcopy(self.receipts)
        for seq, history in self.receipts.items():
            for value in history:
                if balance_error(value["transport"]):
                    pilot.require(seq in targets, "Unregistered billing failure")
                    value["transport"]["service_retryable"] = True

    def start(self, job, attempt):
        if self.stop.is_set():
            raise BalancePaused()
        super().start(job, attempt)

    def one(self, job):
        try:
            return super().one(job)
        except BalancePaused:
            return dict(status="deferred_balance", request_id=job["request"]["request_id"])


def execute(run: Path):
    amendment = register(run)
    jobs, config, inputs = live.load_jobs(run)
    lockfile = run / "runner.lock"
    with lockfile.open("x", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    try:
        worker = Recovery(run, jobs, config, inputs, amendment)
        completed, failed, deferred = 0, 0, 0
        with ThreadPoolExecutor(max_workers=config["live_policy"]["concurrency"]) as pool:
            futures = [pool.submit(worker.one, j) for j in jobs]
            for future in as_completed(futures):
                result = future.result()
                completed += 1
                deferred += result["status"] == "deferred_balance"
                failed += result["status"] == "failed"
                if completed % 50 == 0 or completed == len(jobs):
                    print(pilot.canonical(dict(accounted_logical_requests=completed, total=len(jobs),
                        failed=failed, deferred=deferred, cost_estimate_or_bound_cny=worker.spent)), flush=True)
        print("RECOVERY_FINISHED" if not failed and not deferred else "RECOVERY_INCOMPLETE", flush=True)
    finally:
        lockfile.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    execute(args.run.resolve())
