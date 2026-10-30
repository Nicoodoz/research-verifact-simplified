"""Checks the two nontrivial source-association cases, without patient data."""
import unittest
from source_context131 import match_fragment


class SourceMatchTest(unittest.TestCase):
    def test_chartdate_differs_from_charttime_date(self):
        fragment = dict(date='2100-02-02', time='19:09:00', category='Nursing',
                        description='Transfer', source_text='alpha beta')
        note = dict(ROW_ID='1', CHARTDATE='2100-02-02', CHARTTIME='2100-02-01 19:09:00',
                    CATEGORY='Nursing', DESCRIPTION='Transfer', TEXT='prefix alpha\n beta suffix')
        self.assertEqual(match_fragment(fragment, [note])['exact_whitespace_normalized_matches'], ['1'])

    def test_duplicate_source_match_is_preserved(self):
        fragment = dict(date='2100-02-02', time='Unknown', category='ECG',
                        description='Report', source_text='alpha beta')
        note = dict(ROW_ID='1', CHARTDATE='2100-02-02', CHARTTIME='', CATEGORY='ECG',
                    DESCRIPTION='Report', TEXT='alpha beta')
        self.assertEqual(match_fragment(fragment, [note, dict(note, ROW_ID='2')])['exact_whitespace_normalized_matches'], ['1', '2'])


if __name__ == '__main__':
    unittest.main()
