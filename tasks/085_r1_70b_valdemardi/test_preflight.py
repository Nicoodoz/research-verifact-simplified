"""Offline guards for the Valdemardi A/B profile."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight as p


class ProfileTests(unittest.TestCase):
    def test_old_messages_and_request_settings_preserved(self):
        old = p.rows(p.AUTODL / "jobs.jsonl")
        new = p.jobs()
        self.assertEqual(len(new), 360)
        for a, b in zip(old, new):
            self.assertEqual(a["body"]["messages"], b["body"]["messages"])
            self.assertEqual({k: v for k, v in a["body"].items() if k != "model"},
                             {k: v for k, v in b["body"].items() if k != "model"})
            self.assertEqual(b["body"]["model"], p.MODEL)

    def test_selection_is_original(self):
        expected = p.read(p.OLD / "preflight_selection.json")["cases"]
        selected = p.selected_jobs()
        self.assertEqual([(x["role"], x["id"], x["arm"]) for x in expected],
                         [(role, job["id"], job["arm"]) for role, job in selected])

    def test_loopback_model_guard(self):
        good = {"R1_BASE_URL": "http://127.0.0.1:8000/v1", "R1_MODEL": p.MODEL, "R1_API_KEY": "EMPTY"}
        with patch.dict(os.environ, good):
            self.assertEqual(p.endpoint(), good["R1_BASE_URL"])
        for url in ("https://127.0.0.1:8000/v1", "http://example.com/v1", "http://127.0.0.1:8000/v1?q=1"):
            with patch.dict(os.environ, {**good, "R1_BASE_URL": url}):
                with self.assertRaises(ValueError):
                    p.endpoint()
        with patch.dict(os.environ, {**good, "R1_MODEL": "wrong"}):
            with self.assertRaises(ValueError):
                p.endpoint()

    def test_raw_and_scores_separate(self):
        profile = p.ParserProfile(content_path=["choices", 0, "message", "content"],
                                  reasoning_path=["choices", 0, "message", "reasoning_content"],
                                  finish_path=["choices", 0, "finish_reason"], usage_path=["usage"])
        answer = {"verdict": "Supported", "label_scores": {"Supported": 99}}
        envelope = {"choices": [{"message": {"reasoning_content": "not for classification",
                                              "content": json.dumps(answer)}, "finish_reason": "stop"}], "usage": {}}
        parsed = p.parse(envelope, profile)
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["verdict"], "Supported")
        self.assertIsNone(parsed["label_scores"])

    def test_context_and_profile_privacy(self):
        manifest = p.read(p.PUBLIC / "profile.json")
        self.assertEqual(len(manifest["jobs"]), 360)
        self.assertTrue(manifest["full_360_local_context_fit"])
        self.assertTrue(all(x["local_input_tokens"] + 8192 <= 20000 for x in manifest["jobs"]))
        self.assertNotIn("reference", (p.PUBLIC / "profile.json").read_text(encoding="utf-8"))
        self.assertNotIn("formal", p.main.__code__.co_consts)


if __name__ == "__main__":
    unittest.main()
