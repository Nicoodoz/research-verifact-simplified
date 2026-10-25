"""Invariants for retrospective selection and evidence/source identity."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "tasks/005_pilot_effect_analysis"
sys.path.insert(0, str(TASK))
import effect_analysis as effects
import build_effect_review as review


def fixture():
    rows = []
    for author in ("llm", "human"):
        for kind in ("improved", "degraded", "both_correct_S", "both_correct_NA", "both_wrong"):
            for i in range(6):
                pid = f"fictional-{author}-{kind}-{i}"
                gt = "Not Addressed" if kind.endswith("NA") or (kind in ("improved","degraded") and i == 5) else "Supported"
                s, e = ("Not Supported", gt) if kind == "improved" else (gt, "Not Supported") if kind == "degraded" else (gt,gt) if kind.startswith("both_correct") else ("Not Supported", "Not Supported")
                rows.append(dict(proposition_id=pid, subject_id=f"p{i}", author_type=author, human_gt=gt, structured=s,
                    event_alignment=e, outcome=effects.outcome(gt,s,e), selection_hash=effects.pilot.digest_text(effects.SEED+pid)))
    for i in range(3):
        rows.append(dict(proposition_id=f"fictional-w{i}", subject_id=f"p{i}", author_type="human", human_gt="Not Addressed",
            structured="Supported", event_alignment="Not Supported", outcome="wrong_changed", selection_hash=f"w{i}"))
    return rows


def packet():
    return dict(case_id="fictional-C01", input=dict(proposition_id="fictional-p1", reference_id="fictional-reference",
        reference="Header\n1. Date: 2000-01-01 | Text: α evidence.\n2. Date: 2000-01-02 | Text: Other evidence.\n"),
        outputs={"structured":dict(output_text='{"checks":[{"aspect":"x","assessment":"Invented assessment","evidence_ids":[1]}],"verdict":"Supported","reason":"Invented"}')})


class PilotEffectAnalysisTests(unittest.TestCase):
    def test_transition_partition_does_not_count_wrong_to_wrong_as_improvement(self):
        self.assertEqual(effects.outcome("Supported","Not Supported","Not Addressed"), "wrong_changed")
        self.assertEqual(effects.outcome("Supported","Not Supported","Supported"), "improved")
        self.assertEqual(effects.outcome("Supported","Supported","Not Supported"), "degraded")
        self.assertEqual(effects.outcome("Supported","Supported","Supported"), "both_correct")
        self.assertEqual(effects.outcome("Supported","Not Supported","Not Supported"), "both_wrong")

    def test_selection_is_order_invariant_and_balances_gains_losses_controls(self):
        rows = fixture()
        a, b = effects.select_cases(rows), effects.select_cases(list(reversed(rows)))
        self.assertEqual([r["proposition_id"] for r in a], [r["proposition_id"] for r in b])
        self.assertEqual(len(a),25)
        self.assertEqual(len({r["proposition_id"] for r in a}),25)
        self.assertEqual(sum(r["outcome"] == "improved" for r in a),8)
        self.assertEqual(sum(r["outcome"] == "degraded" for r in a),8)
        self.assertEqual(sum(r["outcome"] == "wrong_changed" for r in a),3)
        for author in ("llm","human"):
            for kind in ("improved","degraded"):
                self.assertEqual(len({r["human_gt"] for r in a if r["author_type"]==author and r["outcome"]==kind}),2)

    def test_reference_anchor_uses_unicode_offsets_and_rejects_text_changes(self):
        p = packet()
        a = review.reference_anchor(p,1)
        self.assertEqual(p["input"]["reference"][a["start"]:a["end_exclusive"]],a["quote"])
        review.verify_anchor(a,p)
        a["quote"] += "changed"
        with self.assertRaisesRegex(ValueError,"Reference anchor changed"):
            review.verify_anchor(a,p)

    def test_anchor_cannot_be_attached_to_another_proposition(self):
        p = packet()
        a = review.reference_anchor(p,1)
        p["input"]["proposition_id"] = "different-patient-claim"
        with self.assertRaisesRegex(ValueError,"identity"):
            review.verify_anchor(a,p)

    def test_output_anchor_checks_full_source_hash_and_field(self):
        p = packet()
        a = review.output_anchor(p,"structured",0)
        review.verify_anchor(a,p)
        p["outputs"]["structured"]["output_text"] = p["outputs"]["structured"]["output_text"].replace("Invented assessment","Changed")
        with self.assertRaisesRegex(ValueError,"Output anchor changed"):
            review.verify_anchor(a,p)

    def test_unknown_reference_number_is_not_invented(self):
        with self.assertRaisesRegex(ValueError,"Unknown reference"):
            review.reference_anchor(packet(),99)


if __name__ == "__main__":
    unittest.main()
