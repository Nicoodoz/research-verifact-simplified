"""Tiny CPU-only observer checks; no torch, model, baseline or GPU execution."""
import copy
import unittest

from capture_native_score import NativeBranchCapture, CANONICAL_PREFIX, BRANCH_TOKENS


class Matrix:
    def __init__(self, rows):
        self.rows = rows
        self.shape = (len(rows), len(rows[0]))

    def __getitem__(self, key):
        first, second = key
        chosen = self.rows[first]
        return Matrix([row[second] if isinstance(second, slice) else [row[i] for i in second] for row in chosen])

    def detach(self): return self
    def cpu(self): return self
    def tolist(self): return copy.deepcopy(self.rows)


class CaptureTests(unittest.TestCase):
    def test_exact_prefix_and_identical_scores_object(self):
        tokens = Matrix([[0, 0, 77] + list(CANONICAL_PREFIX), [0, 88, 99] + list(CANONICAL_PREFIX)])
        values = [[0.0] * (max(BRANCH_TOKENS)+1) for _ in range(2)]
        values[0][BRANCH_TOKENS[0]], values[0][BRANCH_TOKENS[1]] = 2.5, -0.5
        scores = Matrix(values)
        before = copy.deepcopy(values)
        observer = NativeBranchCapture(3, ['a', 'b'])
        self.assertIs(observer(tokens, scores), scores)
        self.assertEqual(values, before)
        self.assertEqual(observer.records()[0]['logit_S_minus_Not'], 3.0)
        self.assertFalse(observer.records()[0]['raw_logits_verified'])

    def test_mismatch_and_early_stop_remain_missing(self):
        scores = Matrix([[0.0] * (max(BRANCH_TOKENS)+1)])
        wrong = NativeBranchCapture(1, ['a'])
        self.assertIs(wrong(Matrix([[77, 1, 2, 3, 4]]), scores), scores)
        self.assertEqual(wrong.records()[0]['status'], 'missing_prefix_mismatch')
        early = NativeBranchCapture(1, ['a'])
        self.assertIs(early(Matrix([[77, 4754, 415]]), scores), scores)
        self.assertEqual(early.records()[0]['status'], 'missing_prefix_step_not_reached')

    def test_later_matching_suffix_is_not_a_generation_prefix(self):
        observer = NativeBranchCapture(1, ['a'])
        scores = Matrix([[0.0] * (max(BRANCH_TOKENS)+1)])
        self.assertIs(observer(Matrix([[77, 999] + list(CANONICAL_PREFIX)]), scores), scores)
        self.assertEqual(observer.records()[0]['status'], 'missing_prefix_step_not_reached')


if __name__ == '__main__': unittest.main()
