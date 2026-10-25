"""Run the authorized fixed pilot, resuming service failures without answer selection."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import gzip
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time

import pilot
import siliconflow as sf

SOURCE = pilot.OUT / "run_001"
SETTINGS = pilot.TASK / "siliconflow_config.json"


def settings() -> dict:
    value = json.loads(SETTINGS.read_text(encoding="utf-8"))
    pilot.require(value["model_id"] == sf.MODEL and value["endpoint"] == sf.ENDPOINT, "Unauthorized endpoint/model")
    pilot.require(value["authorization"]["real_inputs_authorized"] is True, "No real-input authorization")
    pilot.require(value["enable_thinking"] is False and value["content_repair_or_regeneration"] is False, "Changed design")
    return value


def runtime_config(base: dict, spec: dict) -> dict:
    config = copy.deepcopy(base)
    config.update(stage="authorized_live_pilot", live_inference_authorized=True)
    config["judge"] = dict(provider="siliconflow_official", model_id=sf.MODEL,
        model_revision="immutable_revision_not_exposed_by_provider", region="provider_managed_cn_endpoint",
        inference_profile=None, context_window_tokens=spec["context_tokens_documented"],
        tokenizer_or_counting_method="byte_size_preflight_and_provider_response_usage")
    config["generation"].update(max_output_tokens=spec["max_tokens"], temperature=spec["temperature"],
        thinking_mode="disabled", provider_parameter_mapping_verified=True,
        response_format=spec["response_format"], n=1, stream=False)
    config["budget"].update(automatic_retries=spec["maximum_service_attempts"] - 1,
        execution_cap_cny=spec["execution_cap_cny"], content_repair_calls=0)
    config["live_policy"] = spec
    return config


def copy_exclusive(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, target.open("xb") as dst:
        shutil.copyfileobj(src, dst)


def save_atomic(path: Path, value: dict) -> None:
    pilot.require(not path.exists(), "Refusing to replace receipt: " + str(path))
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(pilot.canonical(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    # os.rename refuses an existing destination on Windows; receipt names are unique.
    temporary.rename(path)


def fictional_inputs() -> list[dict]:
    fixture = json.loads((pilot.TASK / "fixtures/synthetic.json").read_text(encoding="utf-8"))
    pilot.require(fixture["entirely_fictional"] is True, "Expected fictional fixture")
    result = []
    for i, case in enumerate(fixture["cases"]):
        result.append(dict(proposition_id=f"fictional-service-{i+1}", subject_id=f"fictional-subject-{i+1}",
            hadm_id=f"fictional-admission-{i+1}", author_type="llm", text=case["proposition"],
            reference=case["reference"], reference_id=pilot.digest_text(case["reference"])))
    # Larger than the longest frozen message. This contains invented text only.
    long = "\n".join(f"{i}. Date: 2001-03-02, Time: 10:00, Note Category: synthetic, Note Description: invented stress test | Text: "
        + "This entirely fictional note records that assessment A was planned for tomorrow and has not yet been completed. " * 4 for i in range(1, 101))
    result.append(dict(proposition_id="fictional-long-context", subject_id="fictional-long-subject", hadm_id="fictional-long-admission",
        author_type="llm", text="Assessment A had already been completed on March 2.", reference=long, reference_id=pilot.digest_text(long)))
    return result


def preflight() -> Path:
    spec = settings()
    _, base, prompts, _, _ = pilot.load_bundle(SOURCE)
    config = runtime_config(base, spec)
    out = pilot.new_run(pilot.OUT / "api_preflight", None, pilot.ROOT / "data/00_raw")
    pilot.write_json(out / "config.json", config)
    inputs = fictional_inputs()
    pilot.write_jsonl(out / "fictional_inputs.jsonl", inputs)
    jobs = [(item, arm) for item in inputs for arm in pilot.ARMS]
    client = sf.Client(timeout=spec["timeout_seconds"])
    def one(pair):
        item, arm = pair
        req = pilot.make_request(item, arm, config, prompts)
        body = sf.api_body(req, spec["response_format"])
        response = client.send(body)
        normalized = sf.normalize_result(req, item, response, config)
        pilot.write_json(out / f"{item['proposition_id']}_{arm}.json", dict(request=body, response=response, normalized=normalized))
        return normalized
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, jobs))
    summary = dict(stage="fictional_service_preflight", requests=len(results),
        success=sum(r["status"] == "success" for r in results),
        adherence_deviations=sum(bool(r["adherence_errors"]) for r in results),
        all_model_ids={r.get("model_returned") for r in results} == {sf.MODEL},
        explicit_zero_reasoning=all(r.get("usage", {}).get("reasoning_counter_basis") == "provider_explicit_counter" and r["usage"]["reasoning_tokens"] == 0 for r in results),
        cost_estimate_cny=sum(r.get("cost", {}).get("cny", 0) for r in results),
        max_fictional_reference_utf8_bytes=max(len(r["reference"].encode()) for r in inputs),
        latency_seconds=pilot.distribution([r["latency_ms"] / 1000 for r in results if r["status"] == "success"]),
        settings_sha256=pilot.digest_file(SETTINGS), contains_real_patient_text=False,
        ready=all(r["status"] == "success" for r in results))
    pilot.write_json(out / "summary.json", summary)
    print(pilot.canonical(dict(out=str(out), **summary)), flush=True)
    return out


def freeze(preflight_path: Path) -> Path:
    spec = settings()
    preflight_summary = json.loads((preflight_path / "summary.json").read_text(encoding="utf-8"))
    pilot.require(preflight_summary["ready"] and preflight_summary["all_model_ids"] and preflight_summary["explicit_zero_reasoning"], "Preflight not ready")
    pilot.require(preflight_summary["settings_sha256"] == pilot.digest_file(SETTINGS), "Settings changed after preflight")
    manifest, base, prompts, cohort, inputs = pilot.load_bundle(SOURCE)
    selected = pilot.patients_in_order(pilot.load_split())
    pilot.require(len(cohort) == 421 and {r["subject_id"] for r in cohort} == set(selected), "Frozen sample changed")
    config = runtime_config(base, spec)
    run = pilot.new_run(pilot.OUT, None, pilot.ROOT / "data/00_raw")
    for name in ("inputs.jsonl", "cohort_llm.csv", "cohort_human.csv", "excluded_invalid.csv", "selected_patients.csv",
                 "historical_predictions_llm.csv", "historical_predictions_human.csv"):
        copy_exclusive(SOURCE / name, run / name)
    for name in ("common", *pilot.ARMS):
        copy_exclusive(SOURCE / "prompts" / (name + ".md"), run / "prompts" / (name + ".md"))
    pilot.write_json(run / "config.json", config)
    sequence = pilot.schedule(inputs, config, prompts)
    pilot.write_csv(run / "request_schedule.csv", sequence)
    by_id = {i["proposition_id"]: i for i in inputs}
    jobs = []
    for row in sequence:
        item = by_id[row["proposition_id"]]
        request = pilot.make_request(item, row["arm"], config, prompts)
        body = sf.api_body(request, spec["response_format"])
        # Byte-level size screen is deliberately not presented as exact tokenization.
        screen = len(pilot.canonical(body).encode("utf-8")) + spec["context_overhead_reserve_tokens"]
        pilot.require(screen + spec["max_tokens"] < spec["context_tokens_documented"], "Context-size screen failed; no truncation permitted")
        jobs.append(dict(sequence=row["sequence"], request=request, api_body=body,
            api_body_sha256=pilot.fingerprint(body), input_byte_screen=screen,
            charge_bound_cny=(screen * 3 + spec["max_tokens"] * 9) / 1e6))
    with (run / "requests.jsonl.gz").open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as handle:
            for job in jobs:
                handle.write((pilot.canonical(job) + "\n").encode())
    bound = sum(j["charge_bound_cny"] for j in jobs)
    pilot.require(bound < spec["execution_cap_cny"], "Conservative planned budget exceeds cap")
    pilot.require(preflight_summary["max_fictional_reference_utf8_bytes"] > max(j["input_byte_screen"] - spec["context_overhead_reserve_tokens"] for j in jobs), "Fictional context test did not cover real request size")
    protected = {p.relative_to(pilot.ROOT).as_posix(): pilot.digest_file(p) for p in (pilot.ROOT / "reviews").glob("*.md")}
    protected.update({".vscode/settings.json": pilot.digest_file(pilot.ROOT / ".vscode/settings.json"),
        ".gitignore": pilot.digest_file(pilot.ROOT / ".gitignore"), "environment.yml": pilot.digest_file(pilot.ROOT / "environment.yml")})
    pilot.write_json(run / "preflight.json", dict(frozen_utc=sf.utcnow(), planned_requests=len(jobs),
        selected_patients=selected, source_bundle=str(SOURCE.relative_to(pilot.ROOT)),
        source_manifest_sha256=pilot.digest_file(SOURCE / "manifest.json"),
        fictional_preflight=str(preflight_path.relative_to(pilot.ROOT)),
        fictional_preflight_summary_sha256=pilot.digest_file(preflight_path / "summary.json"),
        protected_files_sha256=protected, maximum_context_byte_screen=max(j["input_byte_screen"] for j in jobs),
        nominal_context=spec["context_tokens_documented"], exact_input_token_counts_preflight=False,
        input_token_measurement="UTF-8 byte screen with 10k overhead; exact usage collected post-response",
        uncached_peak_charge_bound_cny=bound, price_settlement_verified=False,
        validation_policy_change_before_real_inference=spec["response_policy"],
        user_authorization=spec["authorization"], prompt_bytes_unchanged=True))
    code = [pilot.TASK / "live.py", pilot.TASK / "siliconflow.py", pilot.TASK / "pilot.py", SETTINGS,
            pilot.TASK / "live_protocol.md",
            *sorted((pilot.ROOT / "src/verifact_research/evaluation").glob("*.py"))]
    pilot.write_json(run / "manifest.json", dict(stage="frozen_authorized_real_pilot", created_utc=sf.utcnow(),
        code_sha256={p.relative_to(pilot.ROOT).as_posix(): pilot.digest_file(p) for p in code},
        output_sha256={p.relative_to(run).as_posix(): pilot.digest_file(p) for p in run.rglob("*") if p.is_file()}))
    print(pilot.canonical(dict(run=str(run), planned=len(jobs), conservative_peak_bound_cny=bound)), flush=True)
    return run


def load_jobs(run: Path):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    for name, sha in manifest["output_sha256"].items():
        pilot.require(pilot.digest_file(run / name) == sha, "Frozen input changed: " + name)
    for name, sha in manifest["code_sha256"].items():
        pilot.require(pilot.digest_file(pilot.ROOT / name) == sha, "Inference code/settings changed since freeze: " + name)
    with gzip.open(run / "requests.jsonl.gz", "rt", encoding="utf-8") as handle:
        jobs = [pilot.strict_json(line) for line in handle]
    config = json.loads((run / "config.json").read_text(encoding="utf-8"))
    inputs = {r["proposition_id"]: r for r in pilot.jsonl(run / "inputs.jsonl")}
    return jobs, config, inputs


class Execution:
    def __init__(self, run: Path, jobs: list[dict], config: dict, inputs: dict, client=None):
        self.run, self.jobs, self.config, self.inputs = run, jobs, config, inputs
        self.spec = config["live_policy"]
        self.client = client or sf.Client(timeout=self.spec["timeout_seconds"])
        self.lock = threading.Lock()
        self.reserved, self.spent = 0.0, 0.0
        (run / "receipts").mkdir(exist_ok=True)
        self.started = []
        events = run / "attempt_starts.jsonl"
        if events.exists():
            self.started = pilot.jsonl(events)
        self.receipts = {}
        # A complete fsynced temporary receipt may survive a crash before rename.
        # Recover it, never regenerate its answer. Preserve a partial file too.
        for temporary in sorted((run / "receipts").glob("*.json.tmp")):
            target = temporary.with_suffix("")
            pilot.require(not target.exists(), "Both receipt and temporary exist; inspect before resuming")
            try:
                value = pilot.strict_json(temporary.read_text(encoding="utf-8"))
                pilot.require(all(k in value for k in ("sequence", "attempt", "transport", "normalized", "budget_charge_cny")), "Incomplete receipt")
            except (ValueError, TypeError):
                temporary.rename(temporary.with_suffix(".partial"))
            else:
                temporary.rename(target)
        for path in sorted((run / "receipts").glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            self.receipts.setdefault(value["sequence"], []).append(value)
            self.spent += value["budget_charge_cny"]

    def receipt_path(self, sequence: int, attempt: int) -> Path:
        return self.run / "receipts" / f"{sequence:04d}_attempt_{attempt:02d}.json"

    def start(self, job: dict, attempt: int) -> None:
        with self.lock:
            bound = job["charge_bound_cny"]
            pilot.require(self.spent + self.reserved + bound <= self.spec["execution_cap_cny"], "Execution cap reached; no further calls sent")
            self.reserved += bound
            record = dict(sequence=job["sequence"], request_id=job["request"]["request_id"], attempt=attempt,
                api_body_sha256=job["api_body_sha256"], started_utc=sf.utcnow())
            with (self.run / "attempt_starts.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(pilot.canonical(record) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self.started.append(record)

    def one(self, job: dict) -> dict:
        seq = job["sequence"]
        previous = self.receipts.get(seq, [])
        for value in previous:
            pilot.require(value["api_body_sha256"] == job["api_body_sha256"], "Receipt belongs to a different request")
            if not value["transport"]["service_retryable"]:
                return value["normalized"]
        begun = [r["attempt"] for r in self.started if r["sequence"] == seq]
        done = {r["attempt"] for r in previous}
        # A crash after send can leave no receipt; its answer is unknown. Record
        # that uncertainty before retrying exactly the same request, never select an answer.
        for missing in sorted(set(begun) - done):
            uncertain = dict(http_status=0, error_kind="interrupted_without_receipt", response_json=None,
                response_body_text="", response_headers={}, service_retryable=True, outcome_unknown=True,
                started_utc=next(r["started_utc"] for r in self.started if r["sequence"] == seq and r["attempt"] == missing),
                ended_utc=sf.utcnow(), elapsed_seconds=0)
            normalized = sf.normalize_result(job["request"], self.inputs[job["request"]["proposition_id"]], uncertain, self.config)
            receipt = dict(sequence=seq, attempt=missing, api_body_sha256=job["api_body_sha256"],
                transport=uncertain, normalized=normalized, budget_charge_cny=job["charge_bound_cny"])
            save_atomic(self.receipt_path(seq, missing), receipt)
            with self.lock:
                self.spent += receipt["budget_charge_cny"]
            previous.append(receipt)
        start_at = max(begun + list(done), default=0) + 1
        for attempt in range(start_at, self.spec["maximum_service_attempts"] + 1):
            self.start(job, attempt)
            transport = self.client.send(job["api_body"])
            normalized = sf.normalize_result(job["request"], self.inputs[job["request"]["proposition_id"]], transport, self.config)
            charge = normalized.get("cost", {}).get("cny",
                job["charge_bound_cny"] if transport["outcome_unknown"] or transport["http_status"] == 200 else 0)
            receipt = dict(sequence=seq, attempt=attempt, api_body_sha256=job["api_body_sha256"],
                transport=transport, normalized=normalized, budget_charge_cny=charge)
            save_atomic(self.receipt_path(seq, attempt), receipt)
            with self.lock:
                self.reserved -= job["charge_bound_cny"]
                self.spent += charge
            previous.append(receipt)
            if not transport["service_retryable"]:
                return normalized
            if attempt < self.spec["maximum_service_attempts"]:
                delay = self.spec["retry_delays_seconds"][attempt - 1]
                try:
                    delay = max(delay, min(60, float(transport["response_headers"].get("retry-after", "0"))))
                except ValueError:
                    pass
                time.sleep(delay)
        return previous[-1]["normalized"]


def execute(run: Path) -> None:
    jobs, config, inputs = load_jobs(run)
    # One active runner per experiment. A stale lock is inspectable after a crash.
    lockfile = run / "runner.lock"
    with lockfile.open("x", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    try:
        worker = Execution(run, jobs, config, inputs)
        completed = 0
        failures = 0
        with ThreadPoolExecutor(max_workers=config["live_policy"]["concurrency"]) as pool:
            futures = {pool.submit(worker.one, job): job["sequence"] for job in jobs}
            for future in as_completed(futures):
                result = future.result()
                completed += 1
                failures += result["status"] != "success"
                if completed % 25 == 0 or completed == len(jobs):
                    print(pilot.canonical(dict(completed=completed, total=len(jobs), terminal_failures=failures,
                        cost_estimate_or_unknown_charge_bound_cny=round(worker.spent, 6))), flush=True)
        print("INFERENCE_FINISHED", flush=True)
    finally:
        lockfile.unlink()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="command", required=True)
    subs.add_parser("preflight")
    frozen = subs.add_parser("freeze")
    frozen.add_argument("--preflight", type=Path, required=True)
    run = subs.add_parser("run")
    run.add_argument("--run", type=Path, required=True)
    args = p.parse_args()
    if args.command == "preflight":
        preflight()
    elif args.command == "freeze":
        freeze(args.preflight.resolve())
    else:
        execute(args.run.resolve())


if __name__ == "__main__":
    main()
