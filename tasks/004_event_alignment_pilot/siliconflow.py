"""Small SiliconFlow transport. Credentials exist only in request-header memory."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import socket
import time
import urllib.error
import urllib.request

import pilot

MODEL = "deepseek-ai/DeepSeek-V4-Flash"
ENDPOINT = "https://api.siliconflow.cn/v1/chat/completions"
RETRYABLE = {408, 429, 500, 502, 503, 504}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_key() -> str:
    key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    # VS Code's Python environment may load .env while the execution shell does not.
    # Read the user's existing file only; never create, copy, hash or rewrite it.
    path = pilot.ROOT / ".env"
    if not key and path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            name, sep, value = line.strip().removeprefix("export ").partition("=")
            if sep and name.strip() == "SILICONFLOW_API_KEY":
                key = value.strip().strip('"').strip("'")
                break
    pilot.require(bool(key), "SILICONFLOW_API_KEY is unavailable; do not print or paste the key")
    return key


def response_schema() -> dict:
    # The identical generic schema is sent to all arms. Arm-specific checks remain
    # in the original instructions, rather than extra treatment-only API constraints.
    check = dict(type="object", additionalProperties=False,
        required=["aspect", "assessment", "evidence_ids"], properties={
            "aspect": {"type": "string"}, "assessment": {"type": "string"},
            "evidence_ids": {"type": "array", "items": {"type": "integer"}}})
    return dict(type="json_schema", json_schema=dict(name="verifact_verdict", strict=True,
        schema=dict(type="object", additionalProperties=False, required=["verdict", "reason", "checks"],
            properties={"verdict": {"type": "string", "enum": list(pilot.LABELS)},
                "reason": {"type": "string"}, "checks": {"type": "array", "items": check}})))


def api_body(request: dict, response_format: str = "json_schema") -> dict:
    pilot.require(request["judge"]["model_id"] == MODEL, "Unexpected Judge")
    gen = request["generation"]
    pilot.require(gen["thinking_mode"] == "disabled", "Live run requires thinking disabled")
    body = dict(model=MODEL, messages=request["messages"], temperature=gen["temperature"],
        max_tokens=gen["max_output_tokens"], enable_thinking=False, stream=False, n=1,
        response_format=response_schema() if response_format == "json_schema" else {"type": "json_object"})
    pilot.require(response_format in {"json_schema", "json_object"}, "Unknown output mode")
    return body


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect refused", headers, fp)


class Client:
    def __init__(self, key: str | None = None, timeout: float = 120):
        self._key = load_key() if key is None else key
        self.timeout = timeout

    def scrub(self, text: str) -> str:
        return text.replace(self._key, "[REDACTED_API_KEY]") if self._key else text

    def send(self, body: dict) -> dict:
        encoded = pilot.canonical(body).encode("utf-8")
        pilot.require(not self._key or self._key.encode() not in encoded, "Credential appeared in API body")
        request = urllib.request.Request(ENDPOINT, data=encoded, method="POST", headers={
            "Authorization": "Bearer " + self._key, "Content-Type": "application/json"})
        started = utcnow()
        clock = time.monotonic()
        status, raw, headers, error = 0, "", {}, None
        try:
            opener = urllib.request.build_opener(NoRedirect())
            with opener.open(request, timeout=self.timeout) as response:
                status = response.status
                raw = response.read().decode("utf-8")
                headers = dict(response.headers)
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read().decode("utf-8", errors="replace")
            headers = dict(exc.headers or {})
            error = "http_error"
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
            # Exception text can contain request internals; store only its class.
            error = type(exc).__name__
        raw = self.scrub(raw)
        safe_headers = {k.lower(): self.scrub(v) for k, v in headers.items()
            if k.lower() in {"date", "retry-after", "x-siliconcloud-trace-id"} or k.lower().startswith("x-ratelimit-")}
        try:
            parsed = pilot.strict_json(raw) if raw else None
        except ValueError:
            parsed = None
        return dict(started_utc=started, ended_utc=utcnow(), elapsed_seconds=time.monotonic() - clock,
            http_status=status, error_kind=error, response_headers=safe_headers,
            response_body_text=raw, response_json=parsed,
            service_retryable=status in RETRYABLE or (status == 0 and error is not None),
            outcome_unknown=status == 0)


def normalize_usage(response: dict) -> dict:
    usage = response["usage"]
    prompt, completion = usage["prompt_tokens"], usage["completion_tokens"]
    pilot.require(all(type(n) is int and n >= 0 for n in (prompt, completion)), "Invalid usage counts")
    message = response["choices"][0]["message"]
    reasoning = usage.get("completion_tokens_details", {}).get("reasoning_tokens")
    if reasoning is None:
        # Absence is not silently converted to zero. Report the evidential basis.
        pilot.require(message.get("reasoning_content") in (None, ""), "Uncounted reasoning content")
        reasoning_basis = "disabled_request_and_empty_reasoning_content; provider_counter_absent"
        reasoning = 0
    else:
        pilot.require(type(reasoning) is int and 0 <= reasoning <= completion, "Invalid reasoning counter")
        reasoning_basis = "provider_explicit_counter"
    cached = usage.get("prompt_cache_hit_tokens", usage.get("prompt_tokens_details", {}).get("cached_tokens"))
    pilot.require(cached is None or (type(cached) is int and 0 <= cached <= prompt), "Invalid cache counter")
    return dict(input_tokens=prompt, output_tokens=completion, reasoning_tokens=reasoning,
        reasoning_counter_basis=reasoning_basis, cache_hit_tokens=cached,
        cache_counter_available=cached is not None, total_tokens=usage.get("total_tokens"))


def cost_estimate(usage: dict, when: str) -> dict:
    local = datetime.fromisoformat(when).astimezone(timezone(timedelta(hours=8)))
    factor = 0.5 if 2 <= local.hour < 8 else 1.0
    # Dated official announcement effective 2026-09-01; website listing also
    # shows older/different prices, so these are estimates, not an invoice.
    cached = usage["cache_hit_tokens"]
    hit = cached if cached is not None else 0
    estimated = ((usage["input_tokens"] - hit) * 3 + hit * .3 + usage["output_tokens"] * 9) * factor / 1e6
    return dict(cny=estimated, settlement_verified=False, off_peak=factor == .5,
        cache_assumption="provider_count" if cached is not None else "no_cache_conservative",
        website_listing_scenario_cny=(usage["input_tokens"] + 2 * usage["output_tokens"]) / 1e6)


def normalize_result(request: dict, item: dict, attempt: dict, config: dict) -> dict:
    result = dict(request_id=request["request_id"], proposition_id=request["proposition_id"], arm=request["arm"],
        request_sha256=request["request_sha256"], judge=config["judge"], status="failed",
        structural_errors=[], adherence_errors=[], verdict=None)
    if attempt["http_status"] != 200 or not isinstance(attempt["response_json"], dict):
        result["structural_errors"] = ["No successful JSON service response"]
        return result
    response = attempt["response_json"]
    result.update(model_returned=response.get("model"), system_fingerprint=response.get("system_fingerprint"),
        provider_id=response.get("id"), latency_ms=attempt["elapsed_seconds"] * 1000)
    # Account for generated tokens even when the answer later fails validation.
    try:
        usage = normalize_usage(response)
        result.update(usage=usage, cost=cost_estimate(usage, attempt["ended_utc"]))
    except (ValueError, TypeError, KeyError, IndexError):
        pass
    try:
        pilot.require(response.get("model") == MODEL, "Provider returned a different model")
        pilot.require(len(response["choices"]) == 1, "Unexpected choice count")
        choice = response["choices"][0]
        result.update(output_text=choice["message"].get("content"), finish_reason=choice["finish_reason"])
        pilot.require(choice["finish_reason"] == "stop", "Truncated/filtered/nonfinal generation")
        text = choice["message"]["content"]
        answer = pilot.strict_json(text)
        pilot.require(isinstance(answer, dict) and answer.get("verdict") in pilot.LABELS, "No unambiguous valid final verdict")
        usage = normalize_usage(response)
        pilot.require(usage["reasoning_tokens"] == 0 and not choice["message"].get("reasoning_content"), "Thinking was not disabled")
        pilot.require(usage["output_tokens"] <= config["generation"]["max_output_tokens"], "API output limit violated")
        result.update(status="success", verdict=answer["verdict"], output_text=text, usage=usage,
            cost=cost_estimate(usage, attempt["ended_utc"]), model_returned=response["model"],
            system_fingerprint=response.get("system_fingerprint"), provider_id=response.get("id"),
            latency_ms=attempt["elapsed_seconds"] * 1000, finish_reason=choice["finish_reason"])
        # Predeclared: checklist/word-count violations are diagnostics, not reasons
        # to rerun or discard a valid label. No textual repair is performed.
        try:
            pilot.parse_answer(text, request["arm"], item["reference"], config["budget"]["visible_explanation_word_limit"])
        except (ValueError, TypeError, KeyError) as exc:
            result["adherence_errors"].append(str(exc))
        result["explanation_words"] = len(str(answer.get("reason", "")).split()) + sum(
            len(str(c.get("assessment", "")).split()) for c in answer.get("checks", []) if isinstance(c, dict)) if isinstance(answer.get("checks", []), list) else None
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        result["structural_errors"].append(str(exc))
    return result
