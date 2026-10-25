"""Publish hashes and timing for all A/B attempts and read-only service probes."""
import json

import preflight as p


def main():
    entries = []
    for request_path in sorted((p.PRIVATE / "attempts").glob("*/*/request.json")):
        receipt_path = request_path.parent / "receipt.json"
        request = p.read(request_path)
        receipt = p.read(receipt_path)
        entries.append({"kind": "inference", "stage": request["stage"], "request_id": request["request_id"],
                        "attempt_no": request["attempt_no"], "retry_of": request["retry_of"],
                        "http_status": receipt["http_status"], "outcome_unknown": receipt["outcome_unknown"],
                        "started_utc": receipt["started_utc"], "ended_utc": receipt["ended_utc"],
                        "elapsed_seconds": receipt["elapsed_seconds"],
                        "request_sha256": receipt["request_sha256"], "response_sha256": receipt["response_sha256"],
                        "private_attempt_dir": str(request_path.parent.relative_to(p.ROOT))})
    for probe_path in sorted((p.PRIVATE / "service_probes").glob("*/receipt.json")):
        receipt = p.read(probe_path)
        entries.append({"kind": "GET /v1/models", "http_status": receipt["http_status"],
                        "outcome_unknown": receipt["outcome_unknown"], "started_utc": receipt["started_utc"],
                        "ended_utc": receipt["ended_utc"], "elapsed_seconds": receipt["elapsed_seconds"],
                        "response_sha256": receipt["response_sha256"],
                        "private_attempt_dir": str(probe_path.parent.relative_to(p.ROOT))})
    if sum(e["kind"] == "inference" for e in entries) != 4:
        raise ValueError("expected exactly 4 inference attempts")
    if not all(e["http_status"] == 200 and not e["outcome_unknown"] for e in entries):
        raise ValueError("non-200 or unknown attempt requires separate diagnosis")
    result = {"status": "AB_STOPPED_BEFORE_FORMAL", "entries": entries,
              "inference_attempts": 4, "successful_inference": 4,
              "retries": 0, "unknown_outcomes": 0,
              "model_list_probes": sum(e["kind"] == "GET /v1/models" for e in entries),
              "api_metered_charge_cny": None, "actual_gpu_rental_cny": None,
              "cost_note": "Direct user-managed AutoDL vLLM. Instance hourly price and occupied rental time were not supplied; do not substitute historical price.",
              "GT_read": False}
    path = p.PUBLIC / "request_ledger.json"
    if not path.exists():
        p.put_json(path, result)
    elif p.read(path) != result:
        raise ValueError("saved ledger differs")
    print(json.dumps({"inference_attempts": 4, "model_list_probes": result["model_list_probes"],
                      "retries": 0, "unknown_outcomes": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
