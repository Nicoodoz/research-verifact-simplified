"""Cross-implementation and failure-mode tests for the shared evaluator."""
import sys
import unittest
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
from irrCAC.raw import CAC
from sklearn.metrics import matthews_corrcoef

from verifact_research.evaluation import evaluate, paired_compare
from verifact_research.evaluation.core import cohort_digest
from verifact_research.evaluation.cli import validate_cohort
from verifact_research.evaluation.metrics import (LABELS, classification_metrics, clinician_metrics,
                                                encode, item_bootstrap, metrics_from_confusions, patient_bootstrap)


class MetricTests(unittest.TestCase):
    def test_hand_calculated_confusion_and_class_ratios(self):
        true = [LABELS[i] for i in [0, 0, 0, 1, 1, 2]]
        pred = [LABELS[i] for i in [0, 0, 1, 1, 2, 2]]
        m = classification_metrics(true, pred)
        self.assertEqual(m["confusion_matrix"], [[2, 1, 0], [0, 1, 1], [0, 0, 1]])
        self.assertAlmostEqual(m["percent_agreement"], 4 / 6)
        p = np.array([5, 4, 3]) / 12
        pe = sum(p * (1 - p)) / 2
        self.assertAlmostEqual(m["gwet_ac1"], (4 / 6 - pe) / (1 - pe))
        self.assertEqual(m["per_class"]["Not Supported"]["recall"], .5)

    def test_mcc_matches_sklearn_random_and_degenerate(self):
        rng = np.random.RandomState(2026)
        fixtures = [(rng.randint(0, 3, 97), rng.randint(0, 3, 97)) for _ in range(20)]
        fixtures += [(np.zeros(20, int), np.zeros(20, int)), (np.arange(20) % 3, np.zeros(20, int))]
        for true, pred in fixtures:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                reference = matthews_corrcoef(true, pred)
            result = classification_metrics([LABELS[x] for x in true], [LABELS[x] for x in pred])
            self.assertAlmostEqual(result["mcc"], reference, places=13)

    def test_ac1_matches_irrcac_three_label_two_rater(self):
        rng = np.random.RandomState(19)
        for n in [12, 100, 113]:
            v = rng.randint(0, 3, (n, 2))
            labels = np.array(LABELS)[v]
            reference = CAC(pd.DataFrame(labels), categories=list(LABELS)).gwet()["est"]["coefficient_value"]
            observed = classification_metrics(labels[:, 0], labels[:, 1])["gwet_ac1"]
            self.assertAlmostEqual(round(observed, 5), reference, places=5)

    def test_clinician_agreement_uses_pairs_not_majority(self):
        votes = np.array([[0, 0, 0], [0, 0, 1], [0, 1, 2]])
        self.assertAlmostEqual(clinician_metrics(votes)[0], 4 / 9)

    def test_ac1_matches_irrcac_with_rotating_sparse_clinicians(self):
        rng = np.random.RandomState(7)
        votes = rng.randint(0, 3, (73, 3))
        sparse = pd.DataFrame(np.nan, index=range(73), columns=range(25), dtype=object)
        for i, row in enumerate(votes):
            sparse.iloc[i, [(i + j) % 25 for j in range(3)]] = np.array(LABELS)[row]
        reference = CAC(sparse, categories=list(LABELS)).gwet()["est"]["coefficient_value"]
        self.assertAlmostEqual(round(clinician_metrics(votes)[1], 5), reference, places=5)

    def test_bootstrap_matches_pandas_resampling(self):
        codes = np.array([0, 0, 1, 4, 5, 8, 6, 0])
        draws = item_bootstrap(codes, 12)
        for i in range(12):
            sampled = pd.Series(codes).sample(frac=1., replace=True, random_state=i).to_numpy()
            cm = np.bincount(sampled, minlength=9).reshape(3, 3)
            np.testing.assert_allclose(draws[i], metrics_from_confusions(cm), atol=1e-14)

    def test_constant_prediction_and_absent_class_reported(self):
        m = classification_metrics([LABELS[0], LABELS[1]], [LABELS[0], LABELS[0]])
        self.assertEqual(m["mcc"], 0)
        self.assertTrue(m["mcc_denominator_zero"])
        self.assertIsNone(m["per_class"][LABELS[1]]["precision"])
        self.assertIsNone(m["per_class"][LABELS[2]]["recall"])

    def test_patient_sampling_retains_unequal_cluster_sizes(self):
        subjects = ["a", "a", "a", "b", "c", "c"]
        true = np.array([0, 1, 2, 0, 1, 2])
        pred = np.array([0, 0, 2, 1, 1, 0])
        draws = patient_bootstrap(3 * true + pred, subjects, 15)
        for seed in range(15):
            selected = np.random.RandomState(seed).choice(["a", "b", "c"], 3, replace=True)
            indices = [i for patient in selected for i, s in enumerate(subjects) if s == patient]
            self.assertAlmostEqual(draws[seed, 0], np.mean(true[indices] == pred[indices]))
            self.assertAlmostEqual(draws[seed, 2], matthews_corrcoef(true[indices], pred[indices]))


class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.cohort = [dict(proposition_id=str(i), subject_id=str(i // 2), human_gt=LABELS[i % 3]) for i in range(8)]
        self.pred = [dict(proposition_id=r["proposition_id"], verdict=r["human_gt"]) for r in self.cohort]

    def test_ordered_id_alignment(self):
        self.assertEqual(evaluate(self.cohort, self.pred[::-1], profile="none")["percent_agreement"], 1.)

    def test_missing_requires_explicit_opt_in_and_preserves_denominator(self):
        with self.assertRaisesRegex(ValueError, "Missing predictions"):
            evaluate(self.cohort, self.pred[:-1], profile="none")
        result = evaluate(self.cohort, self.pred[:-1], profile="none", missing="available")
        self.assertEqual(result["coverage"]["expected_n"], 8)
        self.assertEqual(result["coverage"]["evaluated_n"], 7)
        self.assertEqual(result["coverage"]["missing_ids"], ["7"])
        self.assertEqual(result["percent_agreement_full_cohort_bounds"], [7 / 8, 1.])

    def test_extra_duplicate_and_invalid_label_rejected(self):
        for pred in [self.pred + [self.pred[0]], self.pred + [dict(proposition_id="x", verdict=LABELS[0])],
                     [dict(proposition_id=r["proposition_id"], verdict="S") for r in self.cohort]]:
            with self.assertRaises(ValueError):
                evaluate(self.cohort, pred, profile="none")

    def test_cohort_hash_detects_gt_or_order_change(self):
        self.assertNotEqual(cohort_digest(self.cohort), cohort_digest(self.cohort[::-1]))
        changed = [dict(r) for r in self.cohort]
        changed[0]["human_gt"] = LABELS[1]
        self.assertNotEqual(cohort_digest(changed), cohort_digest(self.cohort))

    def test_paired_identical_methods_have_zero_delta_interval(self):
        result = paired_compare(self.cohort, self.pred, self.pred[::-1], iterations=40)
        for metric in result["metrics"].values():
            self.assertEqual(metric, dict(delta=0., ci95=[0., 0.]))

    def test_patient_bootstrap_is_row_order_invariant(self):
        pred = [dict(r) for r in self.pred]
        pred[0]["verdict"] = LABELS[2]
        a = evaluate(self.cohort, pred, iterations=30)
        b = evaluate(self.cohort[::-1], pred, iterations=30)
        self.assertEqual(a["confidence_intervals"], b["confidence_intervals"])

    def test_external_cohort_cannot_change_release_labels_or_validity(self):
        raw = [dict(r, hadm_id="101", author_type="llm", proposition_type="claim", invalid="False") for r in self.cohort]
        validate_cohort(raw, raw, "valid_only")
        changed = [dict(r) for r in raw]
        changed[0]["human_gt"] = LABELS[2]
        with self.assertRaisesRegex(ValueError, "human_gt disagrees"):
            validate_cohort(changed, raw, "all")
        raw[0]["invalid"] = "True"
        with self.assertRaisesRegex(ValueError, "contains invalid"):
            validate_cohort(raw, raw, "valid_only")


if __name__ == "__main__":
    unittest.main()
