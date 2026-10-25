"""Offline checks for skipping a terminal transport failure without resending it."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tasks/006_source_context_feasibility"))
from continue_unsent import ContinueUnsentRunner
from run_context_pilot import MeteredRunner
from verifact_research.inference.siliconflow_pool import Account


class ContinuationTests(unittest.TestCase):
    def test_all_remaining_jobs_finish_without_retrying_unknown_or_received(self):
        calls = []
        class Client:
            def send(self, account, body):
                calls.append(body["messages"][0]["content"])
                return dict(http_status=0 if len(calls) == 2 else 200, body_text="{}", headers={},
                    outcome_unknown=len(calls) == 2)
        jobs = [dict(request_id=f"fictional-{i}", body=dict(model="fictional",
            messages=[dict(role="user", content=str(i))]), max_cost_cny=.05) for i in range(4)]
        with tempfile.TemporaryDirectory() as tmp:
            args = ([Account("fictional", "FICTIONAL-KEY")], jobs, Path(tmp) / "run", .3, "fictional-prep")
            first = MeteredRunner(*args, client=Client())
            self.assertEqual(first.run()["completed"], 1)
            frozen = copy.deepcopy(first.state["jobs"]["fictional-1"])
            resumed = ContinueUnsentRunner(*args, client=Client(), terminal_unknown={"fictional-1": frozen})
            self.assertEqual(resumed.run()["completed"], 3)
            self.assertEqual(calls, ["0", "1", "2", "3"])
            self.assertEqual(resumed.state["jobs"]["fictional-1"], frozen)
            self.assertAlmostEqual(resumed.state["reserved_budget_cny"], .2)
            self.assertEqual(resumed.run()["completed"], 3)
            self.assertEqual(len(calls), 4)

    def test_a_new_unknown_stops_execution_and_cannot_use_old_registration(self):
        calls = []
        class Client:
            def send(self, account, body):
                calls.append(body)
                return dict(http_status=0, body_text="", headers={}, outcome_unknown=True)
        jobs = [dict(request_id=f"fictional-{i}", body=dict(model="fictional",
            messages=[dict(role="user", content=str(i))]), max_cost_cny=.05) for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp:
            args = ([Account("fictional", "FICTIONAL-KEY")], jobs, Path(tmp) / "run", .3, "fictional-prep")
            first = MeteredRunner(*args, client=Client())
            first.run()
            terminal = {"fictional-0": copy.deepcopy(first.state["jobs"]["fictional-0"])}
            resumed = ContinueUnsentRunner(*args, client=Client(), terminal_unknown=terminal)
            self.assertEqual(resumed.run()["pause_reason"], "unknown")
            self.assertEqual(len(calls), 2)
            self.assertEqual(resumed.state["jobs"]["fictional-2"]["attempts"], 0)
            with self.assertRaisesRegex(ValueError, "Unregistered"):
                ContinueUnsentRunner(*args, client=Client(), terminal_unknown=terminal).run()

    def test_unknown_is_immutable_and_not_resent_and_pending_respects_cap(self):
        calls = []
        unknown = dict(http_status=0, body_text="", headers={}, outcome_unknown=True)
        good = dict(http_status=200, body_text=json.dumps(dict(usage=dict(prompt_tokens=1000,
            completion_tokens=100, total_tokens=1100), choices=[dict(message=dict(content="Fictional"))])), headers={}, outcome_unknown=False,
            ended_utc="2026-09-14T10:00:00+00:00")
        class Client:
            def send(self, account, body):
                calls.append(body["messages"][0]["content"])
                return copy.deepcopy(unknown if len(calls) == 1 else good)
        jobs = [dict(request_id=f"fictional-{i}", body=dict(model="fictional",
            messages=[dict(role="user", content=str(i))]), max_cost_cny=.05) for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp, patch("socket.create_connection", side_effect=AssertionError("No network")):
            output = Path(tmp) / "run"
            args = ([Account("fictional", "FICTIONAL-KEY")], jobs, output, .1, "fictional-prep")
            first = MeteredRunner(*args, client=Client())
            self.assertEqual(first.run()["completed"], 0)
            frozen = copy.deepcopy(first.state["jobs"]["fictional-0"])
            receipt = (output / frozen["receipts"][0]["file"]).read_bytes()
            resumed = ContinueUnsentRunner(*args, client=Client(), terminal_unknown={"fictional-0": frozen})
            self.assertEqual(resumed.run()["completed"], 1)
            resumed = ContinueUnsentRunner(*args, client=Client(), terminal_unknown={"fictional-0": frozen})
            # The cap is 0.1, so 0.05 unknown + 0.0039 settled + next 0.05 exceeds it.
            self.assertEqual(resumed.run()["completed"], 1)
            self.assertEqual(calls, ["0", "1"])
            self.assertEqual(resumed.state["jobs"]["fictional-0"], frozen)
            self.assertEqual((output / frozen["receipts"][0]["file"]).read_bytes(), receipt)
            self.assertAlmostEqual(resumed.state["reserved_budget_cny"], .0539)
            bad = ContinueUnsentRunner(*args, client=Client(), terminal_unknown={})
            with self.assertRaisesRegex(ValueError, "Unregistered"):
                bad.run()


if __name__ == "__main__":
    unittest.main()
