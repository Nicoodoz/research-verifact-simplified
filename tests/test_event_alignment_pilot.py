"""Fictional-only tests of pilot isolation, controls, parsing and shared evaluation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tasks/004_event_alignment_pilot"))
import pilot


class EventAlignmentPilotTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((pilot.TASK / "config.json").read_text(encoding="utf-8"))
        self.config["judge"].update(model_id="fictional-test-model", provider="local_fixture")
        self.config["generation"].update(provider_parameter_mapping_verified=True, thinking_mode="disabled")
        self.prompts = pilot.templates()
        self.reference = "1. Date: 2000-01-01, Time: Unknown, Note Category: synthetic, Note Description: test | Text: Fictional procedure A was planned.\n"
        self.item = dict(proposition_id="fake-claim", subject_id="fake-patient", hadm_id="fake-admission", author_type="llm",
            text="Fictional procedure A was planned.", reference_id=pilot.digest_text(self.reference), reference=self.reference)

    def answer(self, arm):
        return dict(verdict="Supported", reason="The invented record documents the plan.",
            checks=[dict(aspect=a, assessment="Fictional check.", evidence_ids=[1]) for a in pilot.ASPECTS[arm]])

    def records(self):
        return [dict(request_id=q["request_id"], request_sha256=q["request_sha256"], judge=self.config["judge"],
            status="success", finish_reason="stop", usage=dict(input_tokens=100, output_tokens=100, reasoning_tokens=0),
            output_text=pilot.canonical(self.answer(a))) for a in pilot.ARMS for q in [pilot.make_request(self.item, a, self.config, self.prompts)]]

    def cohort(self):
        rows = []
        for i, label in enumerate(pilot.LABELS):
            for author in ("llm", "human"):
                rows.append(dict(proposition_id=f"fake-{author}-{i}", subject_id=f"fake-patient-{i}", hadm_id=f"fake-admission-{i}",
                    author_type=author, proposition_type="claim", invalid="False", human_gt=label,
                    time_metadata_conflict=str(i == 2), second_round_anomaly="False"))
        return rows

    def test_frozen_hash_order_is_not_display_order_and_rejects_overlap(self):
        split = dict(seed=pilot.SPLIT_SEED, groups=dict(development=[str(i) for i in range(1, 41)], exploration=["99"], reserved_test=["100"]))
        result = pilot.patients_in_order(split)
        self.assertNotEqual(result, split["groups"]["development"][:6])
        reverse = copy.deepcopy(split)
        reverse["groups"]["development"].reverse()
        self.assertEqual(result, pilot.patients_in_order(reverse))
        split["groups"]["reserved_test"] = [result[0]]
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            pilot.patients_in_order(split)

    def test_scope_keeps_all_selected_valid_claims_and_records_invalid(self):
        rows = self.cohort()
        invalid = dict(rows[0], proposition_id="fake-invalid", invalid="True")
        foreign = dict(rows[0], proposition_id="fake-held-out", subject_id="reserved-test")
        sentence = dict(rows[0], proposition_id="fake-sentence", proposition_type="sentence")
        chosen = list(dict.fromkeys(r["subject_id"] for r in rows))
        valid, excluded = pilot.select_cohort([*rows, invalid, foreign, sentence], chosen)
        self.assertEqual(valid, rows)
        self.assertEqual(excluded, [invalid])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            pilot.select_cohort([*rows, rows[0]], chosen)

    def test_input_evidence_and_generation_identical_no_label_or_metadata_leak(self):
        requests = [pilot.make_request(self.item, a, self.config, self.prompts) for a in pilot.ARMS]
        self.assertEqual(len({q["messages"][1]["content"] for q in requests}), 1)
        for q in requests:
            payload = json.loads(q["messages"][1]["content"])
            self.assertEqual(set(payload), {"proposition", "reference"})
            self.assertEqual(payload["reference"], self.reference)
            self.assertEqual(q["generation"], self.config["generation"])
        with self.assertRaisesRegex(ValueError, "Unexpected model input"):
            pilot.make_request(dict(self.item, human_gt="GOLD_CANARY"), "routine", self.config, self.prompts)

    def test_changed_reference_and_duplicate_number_rejected(self):
        with self.assertRaisesRegex(ValueError, "Changed reference"):
            pilot.validate_input(dict(self.item, reference=self.reference + "changed"))
        doubled = self.reference * 2
        with self.assertRaisesRegex(ValueError, "numbering"):
            pilot.validate_input(dict(self.item, reference=doubled, reference_id=pilot.digest_text(doubled)))

    def test_instruction_controls_and_schedule_are_fixed(self):
        pilot.check_config(self.config, self.prompts)
        items = [dict(self.item, proposition_id=f"fake-{i}") for i in range(6)]
        a = pilot.schedule(items, self.config, self.prompts)
        self.assertEqual(a, pilot.schedule(list(reversed(items)), self.config, self.prompts))
        self.assertEqual(len({q["request_id"] for q in a}), 18)
        first = [a[i]["arm"] for i in range(0, 18, 3)]
        self.assertEqual({arm: first.count(arm) for arm in pilot.ARMS}, {arm: 2 for arm in pilot.ARMS})

    def test_parser_rejects_invalid_labels_extra_json_and_duplicate_keys(self):
        for text in [pilot.canonical(dict(self.answer("routine"), verdict="S")),
                     pilot.canonical(self.answer("routine")) + " trailing answer",
                     '{"verdict":"Supported","verdict":"Not Supported","reason":"x","checks":[]}']:
            with self.assertRaises(ValueError):
                pilot.parse_answer(text, "routine", self.reference)

    def test_parser_rejects_wrong_aspects_invented_cites_and_word_overrun(self):
        valid = self.answer("event_alignment")
        for field, value in [("aspect", "ordinary_summary"), ("evidence_ids", [2]), ("evidence_ids", [True])]:
            bad = copy.deepcopy(valid)
            bad["checks"][0][field] = value
            with self.assertRaises(ValueError):
                pilot.parse_answer(pilot.canonical(bad), "event_alignment", self.reference)
        with self.assertRaisesRegex(ValueError, "word budget"):
            pilot.parse_answer(pilot.canonical(dict(valid, reason="word " * 201)), "event_alignment", self.reference)

    def test_complete_responses_use_request_identity_and_one_judge(self):
        predictions, errors = pilot.assess_responses([self.item], self.records(), self.config, self.prompts)
        self.assertFalse(errors)
        self.assertTrue(all(len(p) == 1 for p in predictions.values()))
        for field, value in [("request_sha256", "wrong"), ("judge", {"model_id": "different"}), ("finish_reason", "max_tokens")]:
            records = self.records()
            records[0][field] = value
            self.assertTrue(pilot.assess_responses([self.item], records, self.config, self.prompts)[1])

    def test_missing_duplicate_extra_and_failed_responses_never_silently_score(self):
        records = self.records()
        for bad in [records[:-1], [*records, records[0]], [*records, dict(records[0], request_id="unexpected")],
                    [dict(records[0], status="error"), *records[1:]]]:
            self.assertTrue(pilot.assess_responses([self.item], bad, self.config, self.prompts)[1])

    def test_usage_and_unbound_provider_prevent_scoring(self):
        for usage in [dict(input_tokens=100, output_tokens=2049, reasoning_tokens=0),
                      dict(input_tokens=100, output_tokens=100, reasoning_tokens=1),
                      dict(input_tokens=100, output_tokens=None, reasoning_tokens=0)]:
            records = self.records()
            records[0]["usage"] = usage
            self.assertTrue(pilot.assess_responses([self.item], records, self.config, self.prompts)[1])
        config = copy.deepcopy(self.config)
        config["judge"]["model_id"] = None
        self.assertTrue(pilot.assess_responses([self.item], self.records(), config, self.prompts)[1])

    def test_shared_evaluation_pairing_and_time_sensitivity(self):
        cohort = self.cohort()
        correct = [dict(proposition_id=r["proposition_id"], verdict=r["human_gt"]) for r in cohort]
        predictions = {a: copy.deepcopy(correct) for a in pilot.ARMS}
        predictions["routine"][2]["verdict"] = "Supported"
        result = pilot.evaluate_arms(cohort, predictions, iterations=20)
        for author in ("llm", "human"):
            part = [r for r in cohort if r["author_type"] == author]
            expected = pilot.evaluate(part, [r for r in correct if r["proposition_id"] in {c["proposition_id"] for c in part}], iterations=20)
            self.assertEqual(result[author]["primary"]["metrics"]["event_alignment"], expected)
            zero = result[author]["primary"]["contrasts"]["event_alignment_minus_structured"]
            self.assertEqual(zero["metrics"]["mcc"]["delta"], 0)
            self.assertEqual(zero["metrics"]["mcc"]["ci95"], [0.0, 0.0])
            self.assertEqual(len(result[author]["exclude_time_conflicts"]["excluded_ids"]), 1)
        self.assertEqual(result["llm"]["primary"]["contrasts"]["event_alignment_minus_routine"]["error_to_correct"], 1)
        with self.assertRaisesRegex(ValueError, "Out-of-cohort"):
            pilot.evaluate_arms(cohort, {**predictions, "routine": [*predictions["routine"], dict(proposition_id="foreign", verdict="Supported")]}, 5)

    def test_entire_synthetic_pipeline_runs_with_network_disabled_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as tmp, patch("socket.create_connection", side_effect=AssertionError("Network forbidden")), patch("socket.socket", side_effect=AssertionError("Network forbidden")):
            run = pilot.synthetic(Path(tmp))
            bundle = run / "bundle"
            manifest, config, prompts, cohort, inputs = pilot.load_bundle(bundle)
            self.assertEqual(manifest["data_kind"], "synthetic")
            status = json.loads((run / "scoring/run_001/status.json").read_text())
            self.assertEqual(status["status"], "synthetic_pipeline_pass")
            original = (bundle / "inputs.jsonl").read_bytes()
            (bundle / "inputs.jsonl").write_bytes(original + b" ")
            with self.assertRaisesRegex(ValueError, "Changed bundle"):
                pilot.load_bundle(bundle)
            (bundle / "inputs.jsonl").write_bytes(original)
            responses = pilot.jsonl(run / "mock_responses.jsonl")[:-1]
            pilot.write_jsonl(run / "incomplete.jsonl", responses)
            failed = pilot.score(bundle, run / "incomplete.jsonl", run / "scoring")
            self.assertFalse((failed / "metrics.json").exists())
            self.assertTrue((failed / "responses.original.jsonl").exists())
            self.assertTrue((run / "scoring/run_001/metrics.json").exists())
            with self.assertRaises(ValueError):
                pilot.new_run(pilot.RAW / "forbidden", "run_001", pilot.ROOT / "data/00_raw")


if __name__ == "__main__":
    unittest.main()
