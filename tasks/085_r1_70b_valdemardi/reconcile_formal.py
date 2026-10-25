"""Reconcile all native attempts across resumptions; no GT access."""
from collections import Counter
import json
import statistics

import formal_runner as runner
import preflight as p


def main():
    jobs, indexed = runner.frozen_jobs()
    completion_path = p.PUBLIC / "formal_completion.json"
    if not completion_path.exists():
        raise RuntimeError("formal inference has not completed")
    entries = []
    for job in jobs:
        found = p.attempts(job["request_id"])
        if sum(r["http_status"] == 200 for _, r, _ in found) != 1:
            raise RuntimeError("missing or duplicate HTTP200")
        for request, receipt, folder in found:
            item = {"id": job["id"], "sid": job["sid"], "arm": job["arm"],
                    "request_id": job["request_id"], "stage": request["stage"],
                    "attempt_no": request["attempt_no"], "retry_of": request["retry_of"],
                    "http_status": receipt["http_status"], "outcome_unknown": receipt["outcome_unknown"],
                    "started_utc": receipt["started_utc"], "ended_utc": receipt["ended_utc"],
                    "elapsed_seconds": receipt["elapsed_seconds"],
                    "request_sha256": receipt["request_sha256"],
                    "response_sha256": receipt["response_sha256"]}
            if receipt["http_status"] == 200:
                observed = p.inspect(folder, indexed[job["request_id"]]["local_input_tokens"])
                if not observed["local_server_prompt_tokens_match"] or not observed["full_output_budget_fits_20k"]:
                    raise RuntimeError("input/context changed")
                item.update(prompt_tokens=observed["prompt_tokens"],
                            completion_tokens=observed["completion_tokens"],
                            finish_reason=observed["finish_reason"],
                            raw_verdict_valid=observed["raw_verdict_valid"],
                            label_scores_valid=observed["label_scores_valid"])
            entries.append(item)
    complete = [x for x in entries if x["http_status"] == 200]
    stages = Counter(x["stage"] for x in complete)
    if stages != {"B": 3, "formal": 357}:
        raise RuntimeError(f"expected 3 reused B and 357 formal, got {stages}")
    ledger_bytes = b"".join(p.encoded(x) + b"\n" for x in entries)
    ledger_path = p.PUBLIC / "formal_request_ledger.jsonl"
    if ledger_path.exists():
        if ledger_path.read_bytes() != ledger_bytes:
            raise ValueError("existing formal ledger differs")
    else:
        p.put(ledger_path, ledger_bytes)
    summary = {"status": "ALL_360_HTTP200_RECONCILED", "GT_read": False,
               "A_B_reused_HTTP200": 3, "new_formal_HTTP200": 357,
               "total_HTTP200": 360, "total_attempts": len(entries),
               "retries": len(entries) - 360,
               "unknown_outcomes": sum(x["outcome_unknown"] for x in entries),
               "http_status_counts": dict(Counter(str(x["http_status"]) for x in entries)),
               "B_prompt_tokens": sum(x["prompt_tokens"] for x in complete if x["arm"] == "B"),
               "F4_prompt_tokens": sum(x["prompt_tokens"] for x in complete if x["arm"] == "F4"),
               "B_completion_tokens": sum(x["completion_tokens"] for x in complete if x["arm"] == "B"),
               "F4_completion_tokens": sum(x["completion_tokens"] for x in complete if x["arm"] == "F4"),
               "successful_request_seconds_sum": sum(x["elapsed_seconds"] for x in complete),
               "longest_request_seconds": max(x["elapsed_seconds"] for x in complete),
               "median_request_seconds": statistics.median(x["elapsed_seconds"] for x in complete),
               "formal_completion_raw_sha256": p.sha(completion_path),
               "formal_request_ledger_sha256": p.sha(ledger_path),
               "gpu_rental_cny": None,
               "gpu_price_note": "Current instance hourly price and billable instance lifetime were not supplied; no historical price substituted.",
               "api_metered_charge_cny": None,
               "api_note": "Direct loopback vLLM on user-managed AutoDL; no provider per-request API invoice available."}
    path = p.PUBLIC / "formal_reconciliation.json"
    if path.exists():
        existing = p.read(path)
        for key in ("A_B_reused_HTTP200", "new_formal_HTTP200", "total_HTTP200", "total_attempts", "formal_request_ledger_sha256"):
            if existing[key] != summary[key]:
                raise ValueError("existing reconciliation differs")
    else:
        p.put_json(path, summary)
    print(json.dumps({k: summary[k] for k in ("A_B_reused_HTTP200", "new_formal_HTTP200", "total_attempts", "retries", "unknown_outcomes")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
