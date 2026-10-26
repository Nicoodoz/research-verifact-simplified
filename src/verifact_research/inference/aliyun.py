"""Alibaba Model Studio OpenAI-compatible HTTP transport; no implicit retries."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import json
import math
import urllib.error
import urllib.request

from .siliconflow_pool import canonical, fingerprint, require, save, NoRedirect

DEFAULT_BASE_URL = 'https://maas.qianwenaiapi.com/compatible-mode/v1'
DEFAULT_MODEL = 'deepseek-v4-flash-0731'


@dataclass(frozen=True)
class Config:
    api_key: str = field(repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL

    def __post_init__(self):
        require(isinstance(self.api_key, str) and all(33 <= ord(x) <= 126 for x in self.api_key),
                'API key must contain printable ASCII without whitespace')
        url = urlsplit(self.base_url)
        host = url.hostname or ''
        require(url.scheme == 'https' and not url.username and not url.password and url.port in (None, 443)
                and not url.query and not url.fragment and url.path.rstrip('/') == '/compatible-mode/v1'
                and (host.endswith('.maas.aliyuncs.com') or host in
                     {'dashscope.aliyuncs.com', 'dashscope-intl.aliyuncs.com', 'dashscope-us.aliyuncs.com', 'maas.qianwenaiapi.com'}),
                'Use an Alibaba HTTPS OpenAI-compatible base URL, without chat/completions')
        require(isinstance(self.model, str) and self.model and not any(x.isspace() for x in self.model), 'Invalid model ID')

    @property
    def endpoint(self):
        return self.base_url.rstrip('/') + '/chat/completions'


def load_config(path: Path) -> Config:
    """Read only the named local file; environment variables do not override it."""
    values = {}
    allowed = {'DASHSCOPE_API_KEY', 'DASHSCOPE_BASE_URL', 'DASHSCOPE_MODEL'}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, sep, value = line.partition('=')
        name, value = name.strip(), value.strip()
        require(sep and name in allowed and name not in values, 'Invalid or duplicate config field')
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name] = value
    return Config(values.get('DASHSCOPE_API_KEY', ''), values.get('DASHSCOPE_BASE_URL', DEFAULT_BASE_URL),
                  values.get('DASHSCOPE_MODEL', DEFAULT_MODEL))


class AliyunClient:
    def __init__(self, config: Config, timeout=180):
        require(math.isfinite(timeout) and timeout > 0, 'Invalid timeout')
        self.config, self.timeout = config, timeout

    def validate(self, body):
        require(self.config.api_key, 'Fill DASHSCOPE_API_KEY in the local configuration file')
        require(isinstance(body, dict) and body.get('model') == self.config.model, 'Request model must match configured Alibaba model')
        require(isinstance(body.get('messages'), list) and body['messages'], 'Missing messages')
        require(body.get('stream', False) is False, 'Only non-streaming requests are supported')
        require('extra_body' not in body, 'HTTP requests use enable_thinking at the top level, not SDK extra_body')
        require(type(body.get('max_tokens')) is int and body['max_tokens'] > 0, 'Explicit positive max_tokens required')
        text = canonical(body)
        require(self.config.api_key not in text and json.dumps(self.config.api_key)[1:-1] not in text,
                'Credential in request body; refusing to send or persist')

    def send(self, body):
        """Return original transport fields (credential-redacted), including failed responses."""
        self.validate(body)
        started = datetime.now(timezone.utc).isoformat()
        request = urllib.request.Request(self.config.endpoint, data=canonical(body).encode('utf-8'), method='POST',
            headers={'Authorization': 'Bearer ' + self.config.api_key, 'Content-Type': 'application/json'})
        try:
            try:
                with urllib.request.build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers or {}
        except (OSError, urllib.error.URLError):
            status, raw, headers = 0, b'', {}
        transport = dict(http_status=status, body_text=raw.decode('utf-8', errors='replace'),
            headers={k.lower(): v for k, v in headers.items() if k.lower() in {'x-request-id', 'x-dashscope-request-id', 'retry-after'}},
            outcome_unknown=status == 0, started_utc=started, ended_utc=datetime.now(timezone.utc).isoformat())
        # Replace within parsed string values, preserving a readable JSON receipt even if an error echoes a key.
        def redact(value):
            if isinstance(value, str):
                return value.replace(self.config.api_key, '[REDACTED_API_KEY]').replace(json.dumps(self.config.api_key)[1:-1], '[REDACTED_API_KEY]')
            if isinstance(value, dict):
                return {k: redact(v) for k, v in value.items()}
            return value
        return redact(transport)


def chat_body(config, messages, *, max_tokens=2048, enable_thinking=True, reasoning_effort='high'):
    require(type(enable_thinking) is bool, 'enable_thinking must be boolean')
    body = dict(model=config.model, messages=messages, temperature=0, max_tokens=max_tokens,
                enable_thinking=enable_thinking, stream=False)
    if enable_thinking:
        require(reasoning_effort in {'low', 'medium', 'high'}, 'Invalid reasoning effort')
        body['reasoning_effort'] = reasoning_effort
    return body


def call_once(config, body, output: Path, *, max_cost_cny, task_used_cny, task_cap_cny=40, client=None):
    """One new attempt, durable reservation before send, never overwrite or retry.

    Bounds are supplied by the task's price/token estimate. This utility does not
    replace the experiment's cumulative ledger or infer Alibaba prices from SiliconFlow.
    """
    require(all(type(x) in (int, float) and math.isfinite(x) for x in (max_cost_cny, task_used_cny, task_cap_cny)), 'Invalid budget')
    require(max_cost_cny > 0 and task_used_cny >= 0 and 0 < task_cap_cny <= 40, 'Invalid task cap or reservation')
    require(task_used_cny + max_cost_cny <= task_cap_cny, 'Whole-task budget would exceed cap')
    client = client or AliyunClient(config)
    AliyunClient(config).validate(body)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    record = dict(provider='aliyun_model_studio', endpoint=config.endpoint, requested_model=config.model,
        body=body, body_sha256=fingerprint(body), prior_task_used_or_reserved_cny=task_used_cny,
        this_attempt_reservation_cny=max_cost_cny, task_cap_cny=task_cap_cny,
        cumulative_reserved_cny=task_used_cny + max_cost_cny, created_utc=datetime.now(timezone.utc).isoformat())
    save(output/'request.json', record, new=True)
    tr = client.send(body)
    save(output/'receipt.json', dict(provider=record['provider'], endpoint=config.endpoint, body_sha256=record['body_sha256'], transport=tr), new=True)
    try:
        native = json.loads(tr['body_text'])
    except (ValueError, TypeError):
        native = {}
    if not isinstance(native, dict):
        native = {}
    result = dict(http_status=tr['http_status'], response_received=tr['http_status'] == 200,
        response_model=native.get('model'), response_id=native.get('id'), usage=native.get('usage'),
        cumulative_reserved_cny=record['cumulative_reserved_cny'], price_or_bill_reconciled=False,
        clinical_prediction_validated=False, retries=0, outcome_unknown=tr['outcome_unknown'])
    save(output/'summary.json', result, new=True)
    return result
