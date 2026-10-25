"""085 Valdemardi execution profile: frozen A/B only, never a formal runner.

Target clinical requests and native replies live in the ignored private directory.
The public output contains identifiers, hashes, token counts and timing only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "outputs/085_r1_70b_model_swap"
AUTODL = ROOT / "outputs/085_r1_70b_autodl"
PUBLIC = ROOT / "outputs/085_r1_70b_valdemardi"
PRIVATE = ROOT / ".local_models/085_valdemardi_private"
TOKENIZER = ROOT / ".local_models/085_valdemardi_tokenizer"
MODEL = "Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ"
REVISION = "ebfea7be35ca86beee303282386399416205c306"
LABELS = ("Supported", "Not Supported", "Not Addressed")
RETRY = {0, 408, 429, 500, 502, 503, 504}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("endpoint redirects disabled")
sys.path.insert(0, str(ROOT / "tasks/085_r1_70b_model_swap"))
from parse_r1 import ParserProfile, parse  # noqa: E402


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def put(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())


def put_json(path, obj):
    put(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def check_frozen_sources():
    freeze = read(AUTODL / "offline_freeze.json")
    for rel, expected in freeze["sources"].items():
        if sha(ROOT / rel) != expected:
            raise ValueError("old frozen source changed: " + rel)
    for rel, expected in freeze["files"].items():
        if sha(AUTODL / rel) != expected:
            raise ValueError("old frozen artifact changed: " + rel)
    selected = read(OLD / "preflight_selection.json")
    if selected["status"] != "FROZEN_BEFORE_ENDPOINT_AND_R1_GT" or selected["GT_read"]:
        raise ValueError("085A selection not frozen")
    if sha(OLD / "neutral_jobs.jsonl") != selected["source_neutral_sha256"]:
        raise ValueError("neutral input changed")
    return selected


def job_from_old(old):
    source = dict(old["body"])
    if source.pop("model") != "casperhansen/deepseek-r1-distill-llama-70b-awq":
        raise ValueError("unexpected old model")
    source["model"] = MODEL
    if (source["temperature"], source["top_p"], source["max_tokens"], source["stream"]) != (0, 1, 8192, False):
        raise ValueError("unexpected request settings")
    body_hash = digest(encoded(source))
    return {"id": old["id"], "sid": old["sid"], "arm": old["arm"], "body": source,
            "body_sha256": body_hash, "source_body_sha256": old["body_sha256"],
            "request_id": digest(("085-valdemardi/" + old["id"] + "/" + old["arm"] + "/" + body_hash).encode())[:32]}


def jobs():
    check_frozen_sources()
    old = rows(AUTODL / "jobs.jsonl")
    if len(old) != 360 or {arm: sum(j["arm"] == arm for j in old) for arm in ("B", "F4")} != {"B": 180, "F4": 180}:
        raise ValueError("old 360 request cohort changed")
    result = [job_from_old(j) for j in old]
    if len({j["request_id"] for j in result}) != 360:
        raise ValueError("duplicate request ID")
    return result


def fictional():
    return job_from_old(read(AUTODL / "fictional_job.json"))


def local_tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(TOKENIZER, local_files_only=True, use_fast=True, trust_remote_code=False)


def lengths(jobs_list, tokenizer):
    result = {}
    for job in jobs_list:
        messages = job["body"]["messages"]
        result[job["request_id"]] = len(tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, truncation=False))
    return result


def prepare():
    all_jobs = jobs()
    old = rows(AUTODL / "jobs.jsonl")
    for source, target in zip(old, all_jobs):
        assert source["id"] == target["id"] and source["arm"] == target["arm"]
        assert source["body"]["messages"] == target["body"]["messages"]
        assert {k: v for k, v in source["body"].items() if k != "model"} == {k: v for k, v in target["body"].items() if k != "model"}
    old_tok = read(OLD / "tokenizer_source.json")
    files = {name: {"sha256": sha(TOKENIZER / name), "bytes": (TOKENIZER / name).stat().st_size,
                    "matches_old_official_revision": sha(TOKENIZER / name) == old_tok["files"][name]["sha256"]}
             for name in ("config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json")}
    tok = local_tokenizer()
    if not tok.is_fast or not isinstance(tok.chat_template, str):
        raise ValueError("Valdemardi tokenizer/chat template unavailable")
    counts = lengths(all_jobs + [fictional()], tok)
    if max(counts.values()) + 8192 > 20000:
        raise ValueError("Valdemardi local tokenizer predicts context overflow")
    old_counts = {(r["id"], r["arm"]): r["chat_input_tokens"] for r in rows(OLD / "tokenizer_lengths.jsonl")}
    deltas = {j["request_id"]: counts[j["request_id"]] - old_counts[j["id"], j["arm"]] for j in all_jobs}
    manifest = {"status": "FROZEN_VALDEMARDI_AB_ONLY_NO_GT", "created_utc": stamp(), "model": MODEL,
                "public_repo_revision": REVISION, "runtime_version_user_reported": "vLLM 0.10.1.1",
                "max_model_len_user_reported": 20000, "source_old_jobs_sha256": sha(AUTODL / "jobs.jsonl"),
                "source_085a_selection_sha256": sha(OLD / "preflight_selection.json"),
                "source_neutral_sha256": sha(OLD / "neutral_jobs.jsonl"),
                "old_identity_lock_sha256": sha(ROOT / "tasks/085_r1_70b_autodl/identity_lock.json"),
                "parser_source_sha256": sha(ROOT / "tasks/085_r1_70b_model_swap/parse_r1.py"),
                "tokenizer_files": files, "tokenizer_template_sha256": digest(tok.chat_template.encode()),
                "tokenizer_config_max_length": tok.model_max_length,
                "jobs": [{"id": j["id"], "sid": j["sid"], "arm": j["arm"], "request_id": j["request_id"],
                          "body_sha256": j["body_sha256"], "source_body_sha256": j["source_body_sha256"],
                          "local_input_tokens": counts[j["request_id"]], "old_official_token_delta": deltas[j["request_id"]]}
                         for j in all_jobs],
                "fictional": {"request_id": fictional()["request_id"], "body_sha256": fictional()["body_sha256"],
                              "local_input_tokens": counts[fictional()["request_id"]]},
                "input_stats": {arm: {"min": min(counts[j["request_id"]] for j in all_jobs if j["arm"] == arm),
                                      "median": statistics.median(counts[j["request_id"]] for j in all_jobs if j["arm"] == arm),
                                      "max": max(counts[j["request_id"]] for j in all_jobs if j["arm"] == arm)}
                                for arm in ("B", "F4")},
                "old_token_delta_stats": {"min": min(deltas.values()), "max": max(deltas.values()),
                                          "nonzero": sum(d != 0 for d in deltas.values())},
                "full_360_local_context_fit": True, "GT_read": False,
                "clinical_bodies_private": True}
    if (PUBLIC / "profile.json").exists():
        prior = read(PUBLIC / "profile.json")
        for key in ("model", "source_old_jobs_sha256", "source_085a_selection_sha256", "tokenizer_files", "jobs"):
            if prior[key] != manifest[key]:
                raise ValueError("existing Valdemardi profile differs: " + key)
    else:
        put_json(PUBLIC / "profile.json", manifest)
    private_jobs = PRIVATE / "jobs.jsonl"
    if private_jobs.exists():
        if rows(private_jobs) != all_jobs:
            raise ValueError("private jobs differ")
    else:
        put(private_jobs, b"".join(encoded(j) + b"\n" for j in all_jobs))
    if not (PRIVATE / "fictional_job.json").exists():
        put_json(PRIVATE / "fictional_job.json", fictional())
    return manifest


def endpoint():
    value = os.getenv("R1_BASE_URL")
    if not value:
        raise ValueError("R1_BASE_URL missing")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1") or parsed.path.rstrip("/") != "/v1" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("only credential-free loopback /v1 is accepted")
    if os.getenv("R1_MODEL") != MODEL:
        raise ValueError("R1_MODEL is not frozen Valdemardi identity")
    if os.getenv("R1_API_KEY") != "EMPTY":
        raise ValueError("R1_API_KEY must be local vLLM EMPTY token")
    return value.rstrip("/")


def request(path, body=None, timeout=900):
    url = endpoint() + path
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    data = None if body is None else encoded(body)
    req = urllib.request.Request(url, data=data, headers={"Authorization": "Bearer EMPTY", "Content-Type": "application/json"})
    started = stamp()
    before = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as response:
            raw, status = response.read(), response.status
        error, unknown = None, False
    except urllib.error.HTTPError as exc:
        raw, status, error, unknown = exc.read(), exc.code, "HTTPError", False
    except (OSError, ValueError) as exc:
        raw, status, error, unknown = b"", 0, type(exc).__name__, body is not None
    return raw, {"http_status": status, "error_type": error, "outcome_unknown": unknown,
                 "started_utc": started, "ended_utc": stamp(), "elapsed_seconds": time.monotonic() - before}


def live_models():
    raw, receipt = request("/models", timeout=30)
    folder = PRIVATE / "service_probes" / str(time.time_ns())
    put(folder / "models.raw", raw)
    put_json(folder / "receipt.json", {**receipt, "response_sha256": digest(raw)})
    if receipt["http_status"] != 200:
        raise RuntimeError("/models unavailable")
    card = json.loads(raw)["data"]
    if len(card) != 1 or card[0]["id"] != MODEL or card[0].get("max_model_len") != 20000:
        raise RuntimeError("served model or 20K context does not match frozen profile")
    public = {"created_utc": stamp(), "model": card[0]["id"], "max_model_len": card[0]["max_model_len"],
              "models_response_sha256": digest(raw), "private_response_path": str((folder / "models.raw").relative_to(ROOT)),
              "http_status": receipt["http_status"], "endpoint_scope": "loopback_only",
              "checkpoint_bytes_independently_verified": False, "runtime_version_independently_verified": False}
    if not (PUBLIC / "service_identity.json").exists():
        put_json(PUBLIC / "service_identity.json", public)
    else:
        existing = read(PUBLIC / "service_identity.json")
        if existing["model"] != MODEL or existing["max_model_len"] != 20000:
            raise RuntimeError("prior service binding mismatch")
    return public


def attempts(request_id):
    base = PRIVATE / "attempts" / request_id
    found = []
    for path in sorted(base.glob("[0-9]*/request.json"), key=lambda p: int(p.parent.name)):
        request_data = read(path)
        receipt_path = path.parent / "receipt.json"
        if receipt_path.exists():
            receipt = read(receipt_path)
            if receipt["request_sha256"] != sha(path) or receipt["response_sha256"] != sha(path.parent / "response.raw"):
                raise ValueError("attempt receipt hash mismatch")
        else:
            receipt = {"http_status": None, "outcome_unknown": True}
        found.append((request_data, receipt, path.parent))
    if sum(receipt["http_status"] == 200 for _, receipt, _ in found) > 1:
        raise ValueError("duplicate HTTP200 for logical request")
    return found


def invoke(job, stage, timeout=900):
    found = attempts(job["request_id"])
    for _, receipt, folder in found:
        if receipt["http_status"] == 200:
            return receipt, folder
    if found and found[-1][1]["http_status"] not in RETRY | {None}:
        raise RuntimeError("last attempt is not retryable")
    for attempt_no in range(len(found) + 1, 4):
        folder = PRIVATE / "attempts" / job["request_id"] / str(attempt_no)
        put_json(folder / "request.json", {"stage": stage, "attempt_no": attempt_no, "request_id": job["request_id"],
                                            "job": job, "created_utc": stamp(), "retry_of": attempt_no - 1 if attempt_no > 1 else None})
        raw, receipt = request("/chat/completions", job["body"], timeout=timeout)
        put(folder / "response.raw", raw)
        put_json(folder / "receipt.json", {**receipt, "request_sha256": sha(folder / "request.json"),
                                            "response_sha256": digest(raw)})
        if receipt["http_status"] == 200:
            return receipt, folder
        if receipt["http_status"] not in RETRY or attempt_no == 3:
            raise RuntimeError(f"request failed HTTP {receipt['http_status']}; preserved attempt")
        time.sleep(min(10 * 2 ** (attempt_no - 1), 40))
    raise RuntimeError("attempts exhausted")


def inspect(folder, expected_tokens=None):
    raw = (folder / "response.raw").read_bytes()
    envelope = json.loads(raw)
    if envelope.get("model") != MODEL:
        raise RuntimeError("response model mismatch")
    choice = envelope["choices"][0]
    message = choice["message"]
    usage = envelope["usage"]
    if not isinstance(message.get("reasoning_content"), str) or not isinstance(message.get("content"), str):
        raise RuntimeError("reasoning/content envelope paths unavailable")
    if not isinstance(choice.get("finish_reason"), str):
        raise RuntimeError("finish_reason unavailable")
    if not all(type(usage.get(k)) is int and usage[k] >= 0 for k in ("prompt_tokens", "completion_tokens", "total_tokens")):
        raise RuntimeError("usage missing")
    profile = ParserProfile(content_path=["choices", 0, "message", "content"],
                            reasoning_path=["choices", 0, "message", "reasoning_content"],
                            finish_path=["choices", 0, "finish_reason"], usage_path=["usage"])
    parsed = parse(raw, profile)
    return {"response_sha256": digest(raw), "response_model": envelope["model"],
            "reasoning_content_present": True, "reasoning_chars": len(message["reasoning_content"]),
            "content_present": True, "content_chars": len(message["content"]),
            "finish_reason": choice["finish_reason"], "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"], "total_tokens": usage["total_tokens"],
            "raw_verdict_valid": parsed["valid"], "raw_invalid_reason": parsed["invalid_reason"],
            "label_scores_valid": parsed["label_scores"] is not None,
            "truncated": parsed["truncated"],
            "local_prompt_tokens": expected_tokens,
            "local_server_prompt_tokens_match": None if expected_tokens is None else usage["prompt_tokens"] == expected_tokens,
            "full_output_budget_fits_20k": usage["prompt_tokens"] + 8192 <= 20000}


def stage_a():
    if not (PUBLIC / "profile.json").exists():
        raise RuntimeError("run prepare first")
    live_models()
    job = read(PRIVATE / "fictional_job.json")
    receipt, folder = invoke(job, "A")
    expected = read(PUBLIC / "profile.json")["fictional"]["local_input_tokens"]
    result = {"stage": "A", "fictional_only": True, "GT_read": False, "request_id": job["request_id"],
              "body_sha256": job["body_sha256"], "request_sha256": sha(folder / "request.json"),
              "elapsed_seconds": receipt["elapsed_seconds"], "http_status": 200, **inspect(folder, expected)}
    if not (PUBLIC / "stage_a.json").exists():
        put_json(PUBLIC / "stage_a.json", result)
    if not result["raw_verdict_valid"] or result["truncated"] or not result["local_server_prompt_tokens_match"]:
        raise RuntimeError("fictional A parser/tokenizer gate failed; B not started")
    return result


def selected_jobs():
    selection = check_frozen_sources()["cases"]
    mapping = {(j["id"], j["arm"]): j for j in jobs()}
    return [(item["role"], mapping[item["id"], item["arm"]]) for item in selection]


def stage_b():
    a = read(PUBLIC / "stage_a.json")
    if not a["raw_verdict_valid"] or a["truncated"] or not a["local_server_prompt_tokens_match"]:
        raise RuntimeError("A gate closed")
    live_models()
    profile = read(PUBLIC / "profile.json")
    indexed = {j["request_id"]: j for j in profile["jobs"]}
    observations = {}
    for role, job in selected_jobs():
        receipt, folder = invoke(job, "B")
        result = {"stage": "B", "role": role, "id": job["id"], "sid": job["sid"], "arm": job["arm"],
                  "request_id": job["request_id"], "body_sha256": job["body_sha256"],
                  "request_sha256": sha(folder / "request.json"), "elapsed_seconds": receipt["elapsed_seconds"],
                  "http_status": 200, "GT_read": False,
                  **inspect(folder, indexed[job["request_id"]]["local_input_tokens"])}
        observations[role] = result
        path = PUBLIC / "stage_b" / f"{role}.json"
        if not path.exists():
            put_json(path, result)
        if not result["local_server_prompt_tokens_match"] or not result["full_output_budget_fits_20k"]:
            raise RuntimeError("actual tokenizer/context gate failed; preserved HTTP200; no more B")
    return observations


def forecast():
    observations = {role: read(PUBLIC / "stage_b" / f"{role}.json") for role in ("short_B", "median_F4", "longest_F4")}
    timings = {arm: [r["elapsed_seconds"] for r in observations.values() if r["arm"] == arm] for arm in ("B", "F4")}
    remaining = {arm: 180 - sum(r["arm"] == arm for r in observations.values()) for arm in ("B", "F4")}
    base = sum(remaining[arm] * statistics.mean(timings[arm]) for arm in remaining)
    buffered = base * 1.5
    result = {"status": "AWAIT_USER_FORMAL_AUTHORIZATION", "created_utc": stamp(), "GT_read": False,
              "remaining_R1_B": remaining["B"], "remaining_R1_F4": remaining["F4"],
              "sampled_B_seconds": timings["B"], "sampled_F4_seconds": timings["F4"],
              "longest_single_request_seconds": max(r["elapsed_seconds"] for r in observations.values()),
              "estimated_serial_seconds": base, "planning_seconds_with_50percent_margin": buffered,
              "current_client_concurrency": 1, "completion_tokens": {role: r["completion_tokens"] for role, r in observations.items()},
              "actual_instance_hourly_price_cny": None, "estimated_gpu_rental_cny": None,
              "api_billing_cny": None, "api_fee_basis": "direct user-managed AutoDL vLLM; no metered provider API invoice available",
              "limitations": "Three observations only. Prefix caching, request length, load, server idle/startup, and GPU rental duration may differ; estimate is not a hard upper bound.",
              "stage_b_sha256": {role: sha(PUBLIC / "stage_b" / f"{role}.json") for role in observations}}
    if not (PUBLIC / "forecast.json").exists():
        put_json(PUBLIC / "forecast.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("prepare", "identity", "A", "B", "forecast", "status"))
    parser.add_argument("--profile", choices=("valdemardi-vllm-0.10.1.1",), default="valdemardi-vllm-0.10.1.1")
    args = parser.parse_args()
    if args.stage == "prepare":
        x = prepare()
        print(json.dumps({"status": x["status"], "jobs": len(x["jobs"]), "stats": x["input_stats"],
                          "old_token_delta": x["old_token_delta_stats"]}, ensure_ascii=False))
    elif args.stage == "identity":
        print(json.dumps(live_models(), ensure_ascii=False))
    elif args.stage == "A":
        print(json.dumps(stage_a(), ensure_ascii=False))
    elif args.stage == "B":
        print(json.dumps(stage_b(), ensure_ascii=False))
    elif args.stage == "forecast":
        print(json.dumps(forecast(), ensure_ascii=False))
    else:
        paths = list((PRIVATE / "attempts").glob("*/*/receipt.json"))
        print(json.dumps({"receipts": len(paths), "http200": sum(read(p)["http_status"] == 200 for p in paths),
                          "A": (PUBLIC / "stage_a.json").exists(),
                          "B": len(list((PUBLIC / "stage_b").glob("*.json"))),
                          "forecast": (PUBLIC / "forecast.json").exists()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
