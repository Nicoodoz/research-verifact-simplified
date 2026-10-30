"""Synthetic structural readback tests; no model or clinical text."""
import unittest
from parse127 import inspect_output


class Checks(unittest.TestCase):
    def test_optional_reason_and_separate_label_validity(self):
        row = inspect_output('{"verdict":"Supported"}')
        self.assertTrue(row['classification']['valid'])
        self.assertTrue(row['reason_structure_valid'])
        row = inspect_output('{"verdict":"Supported"}', require_reason=True)
        self.assertTrue(row['classification']['valid'])
        self.assertFalse(row['reason_structure_valid'])

    def test_text_does_not_rewrite_or_certify_label(self):
        row = inspect_output('{"verdict":"Not Supported","reason":"Synthetic fixture says Supported."}', require_reason=True)
        self.assertEqual(row['classification']['verdict'], 'Not Supported')
        self.assertTrue(row['reason_structure_valid'])
        self.assertTrue(row['semantic_review_required'])
        self.assertFalse(row['sentence_count_verified'])
        self.assertFalse(row['label_rewritten'])

    def test_bad_reason_is_not_hidden_as_bad_classification(self):
        for value in ('null', '17', '[]', '" "'):
            row = inspect_output('{"verdict":"Not Addressed","reason":'+value+'}')
            self.assertTrue(row['classification']['valid'])
            self.assertFalse(row['reason_structure_valid'])

    def test_first_receipt_boundaries(self):
        for text, finish in [('{"verdict":"Supported","verdict":"Not Supported"}', 'stop'),
                             ('{"verdict":"Supported","reason":"A', 'length'),
                             ('prefix {"verdict":"Supported"}', 'stop')]:
            row = inspect_output(text, finish)
            self.assertFalse(row['classification']['valid'])
            self.assertIsNone(row['reason'])
        row = inspect_output('```json\n{"verdict":"Supported","reason":"A synthetic sentence."}\n```')
        self.assertTrue(row['classification']['valid'])
        self.assertTrue(row['reason_structure_valid'])


if __name__ == '__main__':
    unittest.main()
