"""Account rotation tested with fictional credentials/responses; networking forbidden."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.inference.siliconflow_pool import Account, ENDPOINT, HttpClient, Runner, balance_exhausted, canonical, load_accounts


ACCOUNTS = [Account("account_1", "FICTIONAL-KEY-A"), Account("account_2", "FICTIONAL-KEY-B")]


def response(status=200, body=None):
    if body is None:
        body = {"choices": [{"finish_reason": "stop", "message": {"content": "invented answer"}}]}
    return dict(http_status=status, body_text=json.dumps(body), headers={}, outcome_unknown=False)


def exhausted():
    return response(402, dict(code=30001, data=None))


def jobs(n=2):
    return [dict(request_id=f"fictional-{i}", max_cost_cny=.1, body=dict(model="fictional-model",
        messages=[dict(role="user", content=f"Invented request {i}")], max_tokens=10, stream=False)) for i in range(n)]


class Client:
    def __init__(self, callback):
        self.callback, self.calls = callback, []
        self.lock = threading.Lock()

    def send(self, account, body):
        with self.lock:
            self.calls.append((account.alias, copy.deepcopy(body)))
        return self.callback(account, body)


class SiliconFlowPoolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "run"
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            guard = patch(name, side_effect=AssertionError("Network forbidden in tests"))
            guard.start()
            self.addCleanup(guard.stop)

    def test_local_keys_numeric_order_blank_entries_and_no_secret_repr(self):
        p = self.root / ".env.siliconflow_pool"
        p.write_text('SILICONFLOW_API_KEY_10="FICTIONAL-10"\nSILICONFLOW_API_KEY_2=\nSILICONFLOW_API_KEY_1=FICTIONAL-1\n', encoding="utf-8")
        result = load_accounts(p, {"SILICONFLOW_API_KEY_2": "FICTIONAL-2"})
        self.assertEqual([a.alias for a in result], ["account_1", "account_2", "account_10"])
        self.assertNotIn("FICTIONAL", repr(result))
        with self.assertRaisesRegex(ValueError, "Duplicate API key"):
            load_accounts(p, {"SILICONFLOW_API_KEY_2": "FICTIONAL-1"})

    def test_unambiguous_balance_failure_only(self):
        self.assertTrue(balance_exhausted(exhausted()))
        for r in (response(429, {"code": 30001}), response(402, {"code": "30001"}),
                response(402, {"code": 30001, "usage": {"total_tokens": 10}}),
                response(402, {"code": 30001, "choices": [{"message": "answer"}]})):
            self.assertFalse(balance_exhausted(r))

    def test_http_adapter_uses_fixed_endpoint_and_excludes_auth_response_headers(self):
        class Reply:
            status = 200
            headers = {"Authorization": "not-for-logs", "x-siliconcloud-trace-id": "fictional-trace"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return b'{"choices":[]}'
        with patch("urllib.request.build_opener") as factory:
            factory.return_value.open.return_value = Reply()
            body = jobs(1)[0]["body"]
            result = HttpClient().send(ACCOUNTS[0], body)
            request = factory.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, ENDPOINT)
            self.assertEqual(request.get_header("Authorization"), "Bearer " + ACCOUNTS[0].key)
            self.assertEqual(request.data, canonical(body).encode("utf-8"))
            self.assertEqual(result["headers"], {"x-siliconcloud-trace-id": "fictional-trace"})

    def test_http_adapter_preserves_balance_error_body(self):
        error = urllib.error.HTTPError(ENDPOINT, 402, "fictional", {}, io.BytesIO(b'{"code":30001,"data":null}'))
        with patch("urllib.request.build_opener") as factory:
            factory.return_value.open.side_effect = error
            self.assertTrue(balance_exhausted(HttpClient().send(ACCOUNTS[0], jobs(1)[0]["body"])))

    def test_switches_identical_request_preserves_receipts_and_resume_skips_answers(self):
        client = Client(lambda a, b: exhausted() if a.alias == "account_1" else response())
        first = Runner(ACCOUNTS, jobs(), self.output, 1, client=client).run()
        self.assertEqual(first["status"], "complete")
        self.assertEqual([c[0] for c in client.calls], ["account_1", "account_2", "account_2"])
        self.assertEqual(client.calls[0][1], client.calls[1][1])
        self.assertEqual(first["reserved_budget_cny"], .2)
        self.assertEqual(len(list(self.output.glob("receipt_*.json"))), 3)
        Runner(ACCOUNTS, jobs(), self.output, 1, client=client).run()
        self.assertEqual(len(client.calls), 3)

    def test_late_concurrent_failure_does_not_skip_new_active_account(self):
        barrier, switched = threading.Barrier(2), threading.Event()
        def send(account, body):
            if account.alias == "account_1":
                barrier.wait(timeout=5)
                if body["messages"][0]["content"].endswith("1"):
                    self.assertTrue(switched.wait(5))
                return exhausted()
            switched.set()
            return response()
        client = Client(send)
        result = Runner(ACCOUNTS, jobs(), self.output, 1, client=client).run(workers=2)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["exhausted_accounts"], ["account_1"])
        self.assertEqual([a for a, _ in client.calls].count("account_2"), 2)

    def test_all_accounts_exhausted_then_append_account_and_resume(self):
        client = Client(lambda a, b: exhausted())
        result = Runner(ACCOUNTS, jobs(), self.output, 1, client=client).run()
        self.assertEqual(result["pause_reason"], "accounts_exhausted")
        self.assertEqual(result["reserved_budget_cny"], 0)
        extra = [*ACCOUNTS, Account("account_3", "FICTIONAL-KEY-C")]
        later = Client(lambda a, b: response())
        result = Runner(extra, jobs(), self.output, 1, client=later).run()
        self.assertEqual(result["completed"], 2)
        self.assertEqual([a for a, _ in later.calls], ["account_3", "account_3"])

    def test_truncated_or_invalid_model_answer_is_not_regenerated(self):
        client = Client(lambda a, b: response(200, {"choices": [{"finish_reason": "length", "message": {"content": "{"}}]}))
        result = Runner(ACCOUNTS, jobs(1), self.output, 1, client=client).run()
        self.assertEqual(result["completed"], 1)
        self.assertEqual(len(client.calls), 1)

    def test_timeout_or_exception_is_unknown_and_never_auto_retried(self):
        def fail(a, b):
            raise RuntimeError(a.key)
        client = Client(fail)
        result = Runner(ACCOUNTS, jobs(), self.output, 1, client=client).run()
        self.assertEqual(result["completed"], 0)
        self.assertEqual(len(client.calls), 1)
        result = Runner(ACCOUNTS, jobs(), self.output, 1, client=client).run()
        self.assertEqual(result["pause_reason"], "unknown_previous_outcome")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result["reserved_budget_cny"], .1)
        for path in self.output.glob("*.json"):
            self.assertNotIn(ACCOUNTS[0].key, path.read_text(encoding="utf-8"))

    def test_rate_limit_pauses_without_switching_accounts(self):
        client = Client(lambda a, b: response(429, {"message": "rate limited"}))
        result = Runner(ACCOUNTS, jobs(), self.output, 1, client=client).run()
        self.assertEqual(result["pause_reason"], "service_error")
        self.assertEqual([a for a, _ in client.calls], ["account_1"])

    def test_global_budget_and_attempt_limit_do_not_reset_on_rotation(self):
        client = Client(lambda a, b: response())
        result = Runner(ACCOUNTS, jobs(), self.output, .1, client=client).run(workers=2)
        self.assertEqual(result["pause_reason"], "budget_reservation_limit")
        self.assertEqual(len(client.calls), 1)
        Runner(ACCOUNTS, jobs(), self.output, .1, client=client).run()
        self.assertEqual(len(client.calls), 1)
        other = Client(lambda a, b: exhausted())
        result = Runner(ACCOUNTS, jobs(1), self.root / "limited", 1, max_attempts=1, client=other).run()
        self.assertEqual(result["pause_reason"], "attempt_limit")
        self.assertEqual(len(other.calls), 1)

    def test_crash_after_saved_receipt_recovers_without_resending(self):
        client = Client(lambda a, b: response())
        runner = Runner(ACCOUNTS, jobs(1), self.output, 1, client=client)
        with patch.object(runner, "_finish", side_effect=RuntimeError("fictional crash")):
            with self.assertRaises(RuntimeError):
                runner.run()
        result = Runner(ACCOUNTS, jobs(1), self.output, 1, client=client).run()
        self.assertEqual(result["completed"], 1)
        self.assertEqual(len(client.calls), 1)

    def test_decimal_budget_boundary_does_not_prematurely_pause(self):
        client = Client(lambda a, b: response())
        result = Runner(ACCOUNTS, jobs(3), self.output, .3, client=client).run()
        self.assertEqual(result["completed"], 3)
        self.assertEqual(result["reserved_budget_cny"], .3)

    def test_crash_without_receipt_blocks_further_sends(self):
        def fail(a, b):
            raise KeyboardInterrupt()
        client = Client(fail)
        with self.assertRaises(KeyboardInterrupt):
            Runner(ACCOUNTS, jobs(1), self.output, 1, client=client).run()
        result = Runner(ACCOUNTS, jobs(1), self.output, 1, client=client).run()
        self.assertEqual(result["pause_reason"], "unknown_previous_outcome")
        self.assertEqual(len(client.calls), 1)

    def test_changed_input_budget_or_receipt_is_rejected_on_resume(self):
        client = Client(lambda a, b: response())
        Runner(ACCOUNTS, jobs(1), self.output, 1, client=client).run()
        changed = jobs(1)
        changed[0]["body"]["max_tokens"] = 11
        with self.assertRaisesRegex(ValueError, "Task input, budget"):
            Runner(ACCOUNTS, changed, self.output, 1, client=client).run()
        with self.assertRaisesRegex(ValueError, "Task input, budget"):
            Runner(ACCOUNTS, jobs(1), self.output, 2, client=client).run()
        receipt = next(self.output.glob("receipt_*.json"))
        receipt.write_bytes(receipt.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Receipt missing or changed"):
            Runner(ACCOUNTS, jobs(1), self.output, 1, client=client).run()
        self.assertEqual(len(client.calls), 1)

    def test_redacts_all_configured_keys_from_response_files(self):
        client = Client(lambda a, b: response(200, {"text": ACCOUNTS[0].key + ACCOUNTS[1].key}))
        Runner(ACCOUNTS, jobs(1), self.output, 1, client=client).run()
        for path in self.output.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            self.assertTrue(all(a.key not in text for a in ACCOUNTS))

    def test_existing_process_lock_is_never_removed_or_used(self):
        self.output.mkdir()
        lock = self.output / "runner.lock"
        lock.write_text("123", encoding="utf-8")
        client = Client(lambda a, b: response())
        with self.assertRaisesRegex(ValueError, "Runner lock exists"):
            Runner(ACCOUNTS, jobs(1), self.output, 1, client=client).run()
        self.assertEqual(lock.read_text(), "123")
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
