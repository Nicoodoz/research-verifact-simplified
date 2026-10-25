"""One narrowly scoped Qianwen platform key check; no retry, no key output."""
from __future__ import annotations

import datetime
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = BASE.parents[3] / ".env.aliyun"
ATTEMPT = BASE / "attempt_002"
URL = "https://maas.qianwenaiapi.com/compatible-mode/v1/chat/completions"
EXPECTED_CONFIG_URL = "https://maas.qianwenaiapi.com/compatible-mode/v1" * 2
PRIOR_ALIYUN_URL = "https://llm-jfynwotrbct4d0g7.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
PRIOR_RESERVATION_CNY = 0.10
THIS_RESERVATION_CNY = 0.10


def save(path: Path, data):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    values = {}
    for line in CONFIG.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.partition("=")
        if not sep or name not in {"DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "DASHSCOPE_MODEL"} or name in values:
            raise RuntimeError("Unexpected config format")
        values[name] = value.strip().strip('"').strip("'")
    key = values["DASHSCOPE_API_KEY"]
    assert key.startswith("sk-ws-") and all(33 <= ord(ch) <= 126 for ch in key)
    assert values["DASHSCOPE_BASE_URL"] in {EXPECTED_CONFIG_URL, PRIOR_ALIYUN_URL}
    assert values["DASHSCOPE_MODEL"] == "qwen3.8-27b"
    body = json.loads((BASE / "body.json").read_text(encoding="utf-8"))
    assert body == {"model": "qwen3.8-27b", "messages": [{"role": "user", "content": "Reply with OK only."}],
                    "temperature": 0, "max_tokens": 16, "enable_thinking": False, "stream": False}
    ATTEMPT.mkdir(exist_ok=False)
    save(ATTEMPT / "request.json", {"endpoint": URL, "body": body, "task_cap_cny": 10,
                                    "previous_attempt_reservation_cny": PRIOR_RESERVATION_CNY,
                                    "this_attempt_reservation_cny": THIS_RESERVATION_CNY,
                                    "cumulative_conservative_reservation_cny": PRIOR_RESERVATION_CNY + THIS_RESERVATION_CNY,
                                    "price_basis": "https://www.qianwenai.com/models/qwen3.8-27b",
                                    "created_utc": now(), "key_in_artifact": False})
    request = urllib.request.Request(URL, data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                                     method="POST", headers={"Authorization": "Bearer " + key,
                                                             "Content-Type": "application/json"})
    try:
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=30) as response:
                status, raw, headers = response.status, response.read(), response.headers
        except urllib.error.HTTPError as error:
            status, raw, headers = error.code, error.read(), error.headers or {}
    except (OSError, urllib.error.URLError) as error:
        status, raw, headers = 0, b"", {}
        failure_type = type(error).__name__
    else:
        failure_type = None
    received = raw.decode("utf-8", errors="replace").replace(key, "[REDACTED_API_KEY]")
    receipt = {"http_status": status, "body_text": received,
               "headers": {k.lower(): v for k, v in headers.items() if k.lower() in {"x-request-id", "x-dashscope-request-id"}},
               "outcome_unknown": status == 0, "transport_error_type": failure_type, "ended_utc": now()}
    save(ATTEMPT / "receipt.json", receipt)
    try:
        response = json.loads(received)
    except json.JSONDecodeError:
        response = {}
    summary = {"http_status": status, "response_received": status == 200,
               "model": response.get("model"), "usage": response.get("usage"),
               "error_code": response.get("code") or (response.get("error") or {}).get("code"),
               "outcome_unknown": status == 0, "retries": 0,
               "cumulative_conservative_reservation_cny": PRIOR_RESERVATION_CNY + THIS_RESERVATION_CNY}
    save(ATTEMPT / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
