"""Synthetic checks for patient isolation, error sampling and exact evidence provenance."""
from __future__ import annotations

import csv
import copy
from pathlib import Path
import sys
import tempfile
import unittest

TASK = Path(__file__).resolve().parents[1] / "tasks/003_error_analysis"
sys.path.insert(0, str(TASK))
from analyze import LABELS, select_cases, split_patients, subset_csv
from build_review import final_answer_comparison, reference_comparison, render_full_output, resolve_evidence, span, verify_evidence
from verifact_research.audit.common import digest_text


class ErrorAnalysisTests(unittest.TestCase):
    def test_partition_is_exhaustive_disjoint_order_independent_and_exposure_safe(self):
        subjects = [str(i) for i in range(1, 101)]
        a = split_patients(subjects, ["99", "100"])
        b = split_patients(list(reversed(subjects)), ["100", "99"])
        self.assertEqual(a, b)
        self.assertEqual([len(g) for g in a.values()], [20, 40, 40])
        self.assertEqual(set.union(*(set(g) for g in a.values())), set(subjects))
        self.assertEqual(sum(len(g) for g in a.values()), len(set.union(*(set(g) for g in a.values()))))
        self.assertTrue({"99", "100"} <= set(a["exploration"]))

    def test_partition_rejects_bad_exposure(self):
        subjects = [str(i) for i in range(1, 101)]
        for bad in (["101"], ["1", "1"], [str(i) for i in range(1, 22)]):
            with self.assertRaises(ValueError):
                split_patients(subjects, bad)

    def test_selection_covers_error_cells_and_keeps_correct_controls(self):
        rows = []
        for i, a in enumerate(LABELS):
            for j, b in enumerate(LABELS):
                for k in range(4):
                    rows.append(dict(author_type="llm", proposition_id=f"id-{i}-{j}-{k}",
                                     subject_id=f"patient-{i}-{j}-{k}", human_gt=a, baseline_verdict=b))
        selected = select_cases(rows, "llm")
        self.assertEqual(len(selected), 12)
        self.assertEqual({(r["human_gt"], r["baseline_verdict"]) for r in selected}, {(a, b) for a in LABELS for b in LABELS})
        self.assertEqual(sum(r["human_gt"] == r["baseline_verdict"] for r in selected), 3)
        self.assertEqual(selected, select_cases(list(reversed(rows)), "llm"))

    def test_stream_filter_never_exports_other_patient(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["SUBJECT_ID", "TEXT"])
                w.writeheader()
                w.writerows([dict(SUBJECT_ID="1.0", TEXT="allowed synthetic record"),
                             dict(SUBJECT_ID="2", TEXT="held-out synthetic record")])
            self.assertEqual([r["TEXT"] for r in subset_csv(path, "SUBJECT_ID", {"1"}, numeric=True)], ["allowed synthetic record"])

    def fixtures(self):
        reference = "1. Date: 2000-01-01, Time: Unknown, Note Category: synthetic, Note Description: test | Text: value A\n"
        case = dict(selection=dict(subject_id="1", hadm_id="10"), models={m: dict(reference=reference, reference_id=digest_text(reference)) for m in ("R1-70B", "Qwen-3-30B-A3B-Thinking")})
        notes = {"n1": dict(ROW_ID="n1", SUBJECT_ID="1", HADM_ID="10", CHARTDATE="2000-01-01", CHARTTIME="", STORETIME="", CATEGORY="synthetic", DESCRIPTION="test", TEXT="synthetic value A")}
        return case, notes

    def test_evidence_rejects_other_patient_and_invalid_offsets(self):
        c, notes = self.fixtures()
        notes["n1"]["SUBJECT_ID"] = "2"
        with self.assertRaises(ValueError):
            resolve_evidence(c, notes, dict(source="ehr", row_id="n1", start=0, end=8))
        for lo, hi in [(-1, 3), (3, 3), (0, 100)]:
            with self.assertRaises(ValueError):
                span("synthetic", lo, hi)

    def test_evidence_detects_altered_quote_or_admission(self):
        c, notes = self.fixtures()
        e = resolve_evidence(c, notes, dict(source="ehr", row_id="n1", start=0, end=8))
        verify_evidence(c, notes, e)
        for key, wrong in [("quote", "altered"), ("hadm_id", "20"), ("chartdate", "2001-01-01")]:
            changed = copy.deepcopy(e)
            changed[key] = wrong
            with self.assertRaises(ValueError):
                verify_evidence(c, notes, changed)

    def test_reference_comparison_preserves_time_and_content_distinctions(self):
        c, _ = self.fixtures()
        c["models"]["Qwen-3-30B-A3B-Thinking"]["reference"] = c["models"]["R1-70B"]["reference"].replace("2000-01-01", "2000-01-02")
        d = reference_comparison(c)
        self.assertFalse(d["exact_equal"])
        self.assertFalse(d["normalized_block_multiset_equal"])
        self.assertTrue(d["normalized_text_multiset_equal"])
        c["models"]["Qwen-3-30B-A3B-Thinking"]["reference"] = c["models"]["Qwen-3-30B-A3B-Thinking"]["reference"].replace("value A", "value B")
        self.assertFalse(reference_comparison(c)["normalized_text_multiset_equal"])

    def output_fixture(self):
        c, notes = self.fixtures()
        c["selection"]["proposition_id"] = "synthetic-claim"
        for i, value in enumerate(c["models"].values()):
            value.update(proposition_id="synthetic-claim", rater_alias=f"synthetic-rater-{i}",
                         reason="The event is documented.",
                         reasoning_chain="I considered the qualifier. It may not be sufficient.\n```example```",
                         reasoning_final_answer='```json\n{"verdict": "Supported"}\n```')
        text = c["models"]["R1-70B"]["reasoning_chain"]
        spec = dict(source="model_output", model="R1-70B", field="reasoning_chain",
                    start=0, end=len(text), quote=text)
        return c, notes, spec

    def test_output_anchor_rejects_identity_and_content_changes(self):
        c, notes, spec = self.output_fixture()
        e = resolve_evidence(c, notes, spec)
        verify_evidence(c, notes, e)
        for key, wrong in [("quote", "altered"), ("proposition_id", "other-claim"),
                           ("rater_alias", "other-rater"), ("field", "reason"),
                           ("model", "Qwen-3-30B-A3B-Thinking")]:
            changed = dict(e, **{key: wrong})
            with self.assertRaises(ValueError):
                verify_evidence(c, notes, changed)

    def test_output_source_rejects_cross_proposition_and_stale_quote(self):
        c, notes, spec = self.output_fixture()
        with self.assertRaises(ValueError):
            resolve_evidence(c, notes, dict(spec, quote="stale reading note"))
        c["models"]["R1-70B"]["proposition_id"] = "other-claim"
        with self.assertRaises(ValueError):
            resolve_evidence(c, notes, spec)

    def test_output_render_keeps_full_chain_and_final_payload(self):
        c, _, _ = self.output_fixture()
        text = render_full_output(c, "R1-70B")
        for field in ("reasoning_chain", "reasoning_final_answer"):
            self.assertIn(c["models"]["R1-70B"][field], text)
            self.assertIn(digest_text(c["models"]["R1-70B"][field]), text)
        self.assertIn("````text", text)
        self.assertIn("非内部因果机制证明", text)

    def test_output_render_distinguishes_empty_from_missing(self):
        c, _, _ = self.output_fixture()
        c["models"]["R1-70B"]["reasoning_chain"] = ""
        self.assertIn("发布字段为空", render_full_output(c, "R1-70B"))
        del c["models"]["R1-70B"]["reasoning_chain"]
        with self.assertRaises(ValueError):
            render_full_output(c, "R1-70B")

    def test_final_answer_comparison_reports_different_or_ambiguous_output(self):
        c, _, _ = self.output_fixture()
        v = c["models"]["R1-70B"]
        v["verdict"] = "Supported"
        v["reasoning_final_answer"] = 'Summary.\n```json\n{"verdict":"Supported","reason":"different explanation"}\n```'
        d = final_answer_comparison(c, "R1-70B")
        self.assertEqual(d["json_object_count"], 1)
        self.assertTrue(d["verdict_equal"])
        self.assertFalse(d["reason_equal"])
        v["reasoning_final_answer"] *= 2
        d = final_answer_comparison(c, "R1-70B")
        self.assertEqual(d["json_object_count"], 2)
        self.assertIsNone(d["verdict_equal"])
        self.assertEqual(v["reason"], "The event is documented.")


if __name__ == "__main__":
    unittest.main()
