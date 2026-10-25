"""Sequential account failover with durable per-request progress and offline tests.

Budget accounting reserves the supplied upper bound per sent attempt. It is not
an invoice estimate. Only unequivocal unanswered balance failures release it.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
import urllib.error
import urllib.request


ENDPOINT = "https://api.siliconflow.cn/v1/chat/completions"
KEY_NAME = re.compile(r"SILICONFLOW_API_KEY_([1-9][0-9]*)\Z")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(path, value, *, new=False):
    require(not new or not path.exists(), "Refusing to overwrite an existing artifact")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=".pending-", suffix=".json", delete=False) as f:
        temporary = Path(f.name)
        f.write(canonical(value) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)


@dataclass(frozen=True)
class Account:
    alias: str
    key: str = field(repr=False)


def load_accounts(path: Path, environ=None) -> list[Account]:
    """Read only the dedicated file and numbered environment variables; never log values."""
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            name, separator, value = text.partition("=")
            require(separator and KEY_NAME.fullmatch(name.strip()), "Invalid numbered key variable in key file")
            name, value = name.strip(), value.strip()
            require(name not in values, "Duplicate variable in key file")
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[name] = value
    for name, value in (os.environ if environ is None else environ).items():
        if KEY_NAME.fullmatch(name) and value.strip():
            values[name] = value.strip()
    entries = [(int(KEY_NAME.fullmatch(n).group(1)), v) for n, v in values.items() if v]
    require(len({key for _, key in entries}) == len(entries), "Duplicate API key configured; use one key per account")
    require(all(not any(c.isspace() for c in key) for _, key in entries), "API keys must not contain whitespace")
    return [Account(f"account_{number}", key) for number, key in sorted(entries)]


def balance_exhausted(transport):
    try:
        body = json.loads(transport["body_text"])
    except (ValueError, KeyError, TypeError):
        return False
    return (transport["http_status"] == 402 and isinstance(body, dict) and type(body.get("code")) is int
        and body["code"] == 30001 and body.get("data") is None and not body.get("choices") and not body.get("usage"))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect refused", headers, fp)


class HttpClient:
    def __init__(self, timeout=120):
        self.timeout = timeout

    def send(self, account, body):
        started = datetime.now(timezone.utc).isoformat()
        request = urllib.request.Request(ENDPOINT, data=canonical(body).encode("utf-8"), method="POST",
            headers={"Authorization": "Bearer " + account.key, "Content-Type": "application/json"})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                status, raw, headers = response.status, response.read(), response.headers
        except urllib.error.HTTPError as exc:
            status, raw, headers = exc.code, exc.read(), exc.headers or {}
        except (OSError, urllib.error.URLError):
            # A timeout may already have incurred cost. Do not retry or log the exception text.
            return dict(http_status=0, body_text="", headers={}, outcome_unknown=True, started_utc=started,
                ended_utc=datetime.now(timezone.utc).isoformat())
        return dict(http_status=status, body_text=raw.decode("utf-8", errors="replace"),
            headers={k.lower(): v for k, v in headers.items() if k.lower() in {"retry-after", "x-siliconcloud-trace-id"}},
            outcome_unknown=False, started_utc=started, ended_utc=datetime.now(timezone.utc).isoformat())


class Runner:
    """All threads share account state. Late failures retire only their own account."""
    def __init__(self, accounts, jobs, output: Path, budget_cny, max_attempts=5, client=None):
        require(accounts and len({a.alias for a in accounts}) == len(accounts), "No accounts or duplicate account aliases")
        require(all(a.key for a in accounts) and len({a.key for a in accounts}) == len(accounts), "Empty or duplicate credentials")
        require(type(budget_cny) in (int, float) and math.isfinite(budget_cny) and budget_cny > 0, "Invalid total budget")
        require(type(max_attempts) is int and max_attempts > 0, "Invalid attempt limit")
        require(jobs and len({j["request_id"] for j in jobs}) == len(jobs), "Empty task list or duplicate request IDs")
        for job in jobs:
            require(set(job) == {"request_id", "body", "max_cost_cny"}, "Unexpected task fields")
            body, bound = job["body"], job["max_cost_cny"]
            require(isinstance(job["request_id"], str) and job["request_id"], "Invalid request ID")
            require(isinstance(body, dict) and body.get("model") and isinstance(body.get("messages"), list) and body["messages"], "Invalid chat request")
            require(body.get("stream", False) is False, "This runner supports non-streaming requests only")
            require(type(bound) in (int, float) and math.isfinite(bound) and bound > 0, "Missing positive per-attempt cost bound")
        self.accounts, self.jobs, self.output = accounts, jobs, output.resolve()
        self.client, self.lock, self.halt = client or HttpClient(), threading.Lock(), None
        self.spec = dict(schema_version=1, jobs=jobs, budget_cny=budget_cny, max_attempts=max_attempts,
            runner_sha256=file_hash(Path(__file__)), endpoint=ENDPOINT)
        encoded = canonical(self.spec)
        require(all(json.dumps(a.key, ensure_ascii=False)[1:-1] not in encoded for a in accounts),
            "Credential found in task metadata; refusing to persist it")
        self.run_id = fingerprint(self.spec)

    def _save(self):
        save(self.output / "state.json", self.state)

    def _read_receipt(self, item):
        path = self.output / item["file"]
        require(path.is_file() and file_hash(path) == item["sha256"], "Receipt missing or changed; inspect before resuming")
        return json.loads(path.read_text(encoding="utf-8"))

    def _initialize(self):
        manifest = self.output / "manifest.json"
        aliases = [a.alias for a in self.accounts]
        if manifest.exists():
            require(json.loads(manifest.read_text(encoding="utf-8")) == self.spec, "Task input, budget, attempt limit or runner code changed")
            self.state = json.loads((self.output / "state.json").read_text(encoding="utf-8"))
            require(self.state["run_id"] == self.run_id, "State belongs to another task")
            require(aliases[:len(self.state["accounts"])] == self.state["accounts"], "Keep existing account aliases/order; only append new accounts")
            self.state["accounts"] = aliases
            for index, job in enumerate(self.jobs):
                progress = self.state["jobs"][job["request_id"]]
                for item in progress["receipts"]:
                    self._read_receipt(item)
                if progress["status"] == "in_flight":
                    path = self._receipt_path(index, progress["attempts"])
                    if path.exists():
                        value = json.loads(path.read_text(encoding="utf-8"))
                        self._finish(index, job, value)
                    else:
                        progress["status"] = "unknown"
                if progress["status"] == "unknown":
                    self.halt = "unknown_previous_outcome"
        else:
            require(set(p.name for p in self.output.iterdir()) == {"runner.lock"}, "Output directory must be empty or belong to this runner")
            self.state = dict(run_id=self.run_id, accounts=aliases, exhausted_accounts=[], reserved_budget_cny=0,
                jobs={j["request_id"]: dict(status="pending", attempts=0, receipts=[]) for j in self.jobs})
            save(manifest, self.spec, new=True)
        self._save()

    def _receipt_path(self, index, attempt):
        return self.output / f"receipt_{index + 1:06d}_{attempt:03d}.json"

    def _finish(self, index, job, receipt):
        progress = self.state["jobs"][job["request_id"]]
        require(receipt["run_id"] == self.run_id and receipt["request_sha256"] == fingerprint(job["body"])
            and receipt["request_id"] == job["request_id"] and receipt["attempt"] == progress["attempts"]
            and receipt["account"] == progress["account"], "Receipt identity mismatch")
        path = self._receipt_path(index, progress["attempts"])
        transport = receipt["transport"]
        if balance_exhausted(transport):
            if receipt["account"] not in self.state["exhausted_accounts"]:
                self.state["exhausted_accounts"].append(receipt["account"])
            self.state["reserved_budget_cny"] = float(max(Decimal(0),
                Decimal(str(self.state["reserved_budget_cny"])) - Decimal(str(job["max_cost_cny"]))))
            progress["status"] = "pending"
        elif transport["http_status"] == 200:
            # Even truncated/malformed model output is a terminal received answer.
            progress["status"] = "response_received"
        else:
            progress["status"] = "unknown" if transport.get("outcome_unknown") else "service_error"
            self.halt = progress["status"]
        progress["receipts"].append(dict(file=path.name, sha256=file_hash(path), account=receipt["account"]))

    def _one(self, index, job):
        while True:
            with self.lock:
                progress = self.state["jobs"][job["request_id"]]
                if self.halt or progress["status"] == "response_received":
                    return
                if progress["status"] in {"unknown", "in_flight"}:
                    self.halt = "unknown_previous_outcome"
                    return
                account = next((a for a in self.accounts if a.alias not in self.state["exhausted_accounts"]), None)
                if account is None or progress["attempts"] >= self.spec["max_attempts"]:
                    return
                reserved = Decimal(str(self.state["reserved_budget_cny"])) + Decimal(str(job["max_cost_cny"]))
                if reserved > Decimal(str(self.spec["budget_cny"])):
                    return
                progress.update(status="in_flight", attempts=progress["attempts"] + 1, account=account.alias)
                self.state["reserved_budget_cny"] = float(reserved)
                self._save()  # Persist before sending; crashes cannot silently reset cost or progress.
                attempt = progress["attempts"]
            try:
                transport = self.client.send(account, job["body"])
            except Exception:
                transport = dict(http_status=0, body_text="", headers={}, outcome_unknown=True,
                    error_kind="transport_exception_redacted")
            safe = canonical(transport)
            for configured in self.accounts:
                safe = safe.replace(json.dumps(configured.key, ensure_ascii=False)[1:-1], "[REDACTED_API_KEY]")
            receipt = dict(run_id=self.run_id, request_id=job["request_id"], request_sha256=fingerprint(job["body"]),
                account=account.alias, attempt=attempt, transport=json.loads(safe))
            with self.lock:
                save(self._receipt_path(index, attempt), receipt, new=True)
                self._finish(index, job, receipt)
                self._save()
                if self.state["jobs"][job["request_id"]]["status"] != "pending":
                    return

    def _guarded_one(self, index, job):
        try:
            self._one(index, job)
        except BaseException:
            with self.lock:
                self.halt = "local_execution_error"
            raise

    def run(self, workers=1):
        require(type(workers) is int and 1 <= workers <= 32, "workers must be between 1 and 32")
        self.output.mkdir(parents=True, exist_ok=True)
        lockfile = self.output / "runner.lock"
        try:
            with lockfile.open("x", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except FileExistsError:
            raise ValueError("Runner lock exists; verify its process has exited before removing it") from None
        try:
            self._initialize()
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(self._guarded_one, i, job) for i, job in enumerate(self.jobs)]
                for future in futures:
                    future.result()
            completed = sum(p["status"] == "response_received" for p in self.state["jobs"].values())
            result = dict(status="complete" if completed == len(self.jobs) else "paused", completed=completed,
                total=len(self.jobs), pause_reason=self.halt or "accounts_budget_or_attempt_limit",
                exhausted_accounts=self.state["exhausted_accounts"], reserved_budget_cny=self.state["reserved_budget_cny"],
                budget_is_conservative_reservation_not_actual_bill=True)
            if result["status"] == "complete":
                result["pause_reason"] = None
            elif not self.halt:
                pending = [j for j in self.jobs if self.state["jobs"][j["request_id"]]["status"] != "response_received"]
                if len(self.state["exhausted_accounts"]) == len(self.accounts):
                    result["pause_reason"] = "accounts_exhausted"
                elif any(self.state["jobs"][j["request_id"]]["attempts"] >= self.spec["max_attempts"] for j in pending):
                    result["pause_reason"] = "attempt_limit"
                else:
                    result["pause_reason"] = "budget_reservation_limit"
            save(self.output / "summary.json", result)
            return result
        finally:
            lockfile.unlink()
