"""Fictional-only service, budget and resume regression tests; no real credentials."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tasks/004_event_alignment_pilot"))
import pilot
import live
import siliconflow as sf
import resume_balance


class SiliconFlowPilotTests(unittest.TestCase):
    def setUp(self):
        self.spec = live.settings()
        base = json.loads((pilot.TASK / "config.json").read_text(encoding="utf-8"))
        self.config = live.runtime_config(base, self.spec)
        self.config["live_policy"]["retry_delays_seconds"] = [0, 0, 0, 0]
        self.item = live.fictional_inputs()[0]
        self.request = pilot.make_request(self.item, "structured", self.config, pilot.templates())
        body = sf.api_body(self.request)
        self.job = dict(sequence=1, request=self.request, api_body=body,
            api_body_sha256=pilot.fingerprint(body), charge_bound_cny=.1)

    def transport(self, verdict="Supported", status=200):
        content = dict(verdict=verdict, reason="An invented record documents this.",
            checks=[dict(aspect=a, assessment="Invented evidence.", evidence_ids=[1]) for a in pilot.ASPECTS["structured"]])
        response = dict(model=sf.MODEL, id="fictional-response", system_fingerprint="", choices=[dict(
            finish_reason="stop", message=dict(content=pilot.canonical(content), reasoning_content=""))],
            usage=dict(prompt_tokens=1000, completion_tokens=100, total_tokens=1100,
                completion_tokens_details=dict(reasoning_tokens=0), prompt_cache_hit_tokens=500))
        return dict(started_utc="2026-09-13T13:00:00+00:00", ended_utc="2026-09-13T13:00:01+00:00",
            http_status=status, response_json=response if status == 200 else None,
            response_body_text=pilot.canonical(response) if status == 200 else "service unavailable",
            response_headers={}, service_retryable=status in sf.RETRYABLE or status == 0,
            outcome_unknown=status == 0, error_kind=None, elapsed_seconds=1)

    def normalize(self, t):
        return sf.normalize_result(self.request, self.item, t, self.config)

    def worker(self, path, client):
        return live.Execution(path, [self.job], self.config, {self.item["proposition_id"]: self.item}, client)

    def test_all_arms_share_native_settings_schema_and_full_input(self):
        bodies = [sf.api_body(pilot.make_request(self.item, a, self.config, pilot.templates())) for a in pilot.ARMS]
        self.assertEqual(len({pilot.canonical(b["messages"][1]) for b in bodies}), 1)
        self.assertEqual(len({pilot.canonical({k: v for k, v in b.items() if k != "messages"}) for b in bodies}), 1)
        self.assertEqual(bodies[0]["max_tokens"], 2048)
        self.assertIs(bodies[0]["enable_thinking"], False)
        bad = copy.deepcopy(self.request)
        bad["judge"]["model_id"] = "wrong-model"
        with self.assertRaises(ValueError):
            sf.api_body(bad)

    def test_thinking_truncation_model_and_token_violations_block_but_keep_cost(self):
        for field in ("thinking", "truncation", "model", "cap"):
            t = self.transport()
            r = t["response_json"]
            if field == "thinking":
                r["usage"]["completion_tokens_details"]["reasoning_tokens"] = 1
            elif field == "truncation":
                r["choices"][0]["finish_reason"] = "length"
            elif field == "model":
                r["model"] = "different"
            else:
                r["usage"]["completion_tokens"] = 2049
            result = self.normalize(t)
            self.assertEqual(result["status"], "failed", field)
            self.assertGreater(result["cost"]["cny"], 0)

    def test_word_or_checklist_deviation_keeps_original_valid_label(self):
        t = self.transport("Not Supported")
        answer = dict(verdict="Not Supported", reason="invented " * 201, checks=[])
        t["response_json"]["choices"][0]["message"]["content"] = pilot.canonical(answer)
        result = self.normalize(t)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["verdict"], "Not Supported")
        self.assertTrue(result["adherence_errors"])
        self.assertEqual(result["output_text"], pilot.canonical(answer))

    def test_invalid_or_ambiguous_label_is_not_repaired(self):
        for answer in ('{"verdict":"Supported","verdict":"Not Supported"}', '{"verdict":"S"}', 'bad json'):
            t = self.transport()
            t["response_json"]["choices"][0]["message"]["content"] = answer
            self.assertEqual(self.normalize(t)["status"], "failed")

    def test_missing_reasoning_counter_is_explicitly_distinguished(self):
        r = self.transport()["response_json"]
        del r["usage"]["completion_tokens_details"]
        self.assertIn("counter_absent", sf.normalize_usage(r)["reasoning_counter_basis"])
        r["choices"][0]["message"]["reasoning_content"] = "Unexpected thought"
        with self.assertRaises(ValueError):
            sf.normalize_usage(r)

    def test_cache_and_time_pricing_not_claimed_as_bill(self):
        u = sf.normalize_usage(self.transport()["response_json"])
        peak = sf.cost_estimate(u, "2026-09-13T13:00:00+00:00")
        valley = sf.cost_estimate(u, "2026-09-13T19:00:00+00:00")
        self.assertAlmostEqual(peak["cny"], .00255)
        self.assertAlmostEqual(valley["cny"], peak["cny"] / 2)
        self.assertFalse(peak["settlement_verified"])

    def test_service_retry_is_identical_and_resume_uses_first_terminal_answer(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            client = Mock()
            client.send.side_effect = [self.transport(status=429), self.transport("Not Addressed")]
            result = self.worker(path, client).one(self.job)
            self.assertEqual(result["verdict"], "Not Addressed")
            self.assertEqual(client.send.call_count, 2)
            self.assertEqual(client.send.call_args_list[0], client.send.call_args_list[1])
            never = Mock()
            self.assertEqual(self.worker(path, never).one(self.job), result)
            never.send.assert_not_called()
            self.assertEqual(len(list((path / "receipts").glob("*.json"))), 2)

    def test_content_failure_does_not_trigger_retry_even_after_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            client = Mock()
            client.send.return_value = self.transport("illegal")
            self.assertEqual(self.worker(path, client).one(self.job)["status"], "failed")
            self.assertEqual(self.worker(path, client).one(self.job)["status"], "failed")
            self.assertEqual(client.send.call_count, 1)

    def test_unknown_interruption_is_recorded_and_charged_conservatively(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            client = Mock()
            client.send.return_value = self.transport()
            first = self.worker(path, client)
            first.start(self.job, 1)  # emulate crash before response persistence
            resumed = self.worker(path, client)
            resumed.one(self.job)
            receipt = json.loads(resumed.receipt_path(1, 1).read_text())
            self.assertTrue(receipt["transport"]["outcome_unknown"])
            self.assertEqual(receipt["budget_charge_cny"], .1)
            self.assertEqual(client.send.call_count, 1)

    def test_complete_temporary_receipt_recovers_without_api_call(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            client = Mock()
            client.send.return_value = self.transport()
            worker = self.worker(path, client)
            worker.one(self.job)
            receipt = worker.receipt_path(1, 1)
            receipt.rename(receipt.with_suffix(".json.tmp"))
            never = Mock()
            self.assertEqual(self.worker(path, never).one(self.job)["status"], "success")
            never.send.assert_not_called()

    def test_execution_cap_prevents_sending(self):
        with tempfile.TemporaryDirectory() as d:
            client = Mock()
            self.config["live_policy"]["execution_cap_cny"] = .01
            with self.assertRaisesRegex(ValueError, "cap reached"):
                self.worker(Path(d), client).one(self.job)
            client.send.assert_not_called()

    def test_transport_redacts_key_and_does_not_log_exception_text(self):
        client = sf.Client(key="FICTIONAL-SECRET-NOT-A-REAL-KEY")
        fake = Mock()
        fake.status = 200
        fake.headers = {"x-siliconcloud-trace-id": "FICTIONAL-SECRET-NOT-A-REAL-KEY", "Authorization": "secret"}
        fake.read.return_value = b'{"echo":"FICTIONAL-SECRET-NOT-A-REAL-KEY"}'
        fake.__enter__ = Mock(return_value=fake)
        fake.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = fake
        with patch.object(sf.urllib.request, "build_opener", return_value=opener):
            result = client.send(self.job["api_body"])
        self.assertNotIn("FICTIONAL-SECRET-NOT-A-REAL-KEY", pilot.canonical(result))

        self.assertNotIn("authorization", result["response_headers"])
        opener.open.side_effect = urllib.error.URLError("FICTIONAL-SECRET-NOT-A-REAL-KEY")
        with patch.object(sf.urllib.request, "build_opener", return_value=opener):
            result = client.send(self.job["api_body"])
        self.assertTrue(result["service_retryable"])
        self.assertNotIn("FICTIONAL-SECRET-NOT-A-REAL-KEY", pilot.canonical(result))

    def billing_failure(self):
        t = self.transport(status=402)
        t["response_json"] = dict(code=30001, message="Insufficient balance (fictional)", data=None)
        t["response_body_text"] = pilot.canonical(t["response_json"])
        return t

    def test_billing_recovery_preserves_failure_and_does_not_regenerate_success(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            client = Mock()
            client.send.return_value = self.billing_failure()
            first = self.worker(path, client)
            self.assertEqual(first.one(self.job)["status"], "failed")
            original = first.receipt_path(1, 1).read_bytes()
            client.send.return_value = self.transport("Not Addressed")
            args = (path, [self.job], self.config, {self.item["proposition_id"]: self.item}, dict(target_sequences=[1]))
            result = resume_balance.Recovery(*args, client=client).one(self.job)
            self.assertEqual(result["verdict"], "Not Addressed")
            self.assertEqual(first.receipt_path(1, 1).read_bytes(), original)
            self.assertEqual(resume_balance.Recovery(*args, client=client).one(self.job), result)
            self.assertEqual(client.send.call_count, 2)

    def test_billing_recovery_stops_unsent_requests_on_another_402(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            client = Mock()
            client.send.return_value = self.billing_failure()
            self.worker(path, client).one(self.job)
            recovered = resume_balance.Recovery(path, [self.job], self.config, {self.item["proposition_id"]: self.item},
                dict(target_sequences=[1]), client=client)
            self.assertEqual(recovered.one(self.job)["status"], "failed")
            other = copy.deepcopy(self.job)
            other["sequence"] = 2
            self.assertEqual(recovered.one(other)["status"], "deferred_balance")
            self.assertEqual(client.send.call_count, 2)

    def test_balance_exception_requires_unambiguous_service_error_without_answer(self):
        self.assertTrue(resume_balance.balance_error(self.billing_failure()))
        bad = self.billing_failure()
        bad["response_json"]["choices"] = [{"message": "answer exists"}]
        self.assertFalse(resume_balance.balance_error(bad))
        self.assertFalse(resume_balance.balance_error(self.transport()))


if __name__ == "__main__":
    unittest.main()
