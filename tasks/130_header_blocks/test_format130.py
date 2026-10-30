import unittest
from format130 import group_reference


class FormatTest(unittest.TestCase):
    def test_preserves_fragments_and_separated_headers(self):
        h='Date: 2020-01-01, Time: Unknown, Note Category: Test, Note Description: Example | Text: '
        k=h.replace('2020-01-01','2020-01-02')
        s='Preamble\n1. '+h+'one\n\n2. '+h+'two\n3. '+k+'three\n4. '+h+'four'
        out,parts,m=group_reference(s)
        self.assertEqual(m['header_groups'],3)
        self.assertEqual([r['text'] for r in parts],['one\n\n','two\n','three\n','four'])
        self.assertEqual('Preamble\n'+''.join(r['original_header']+r['text'] for r in parts),s)
        self.assertTrue(all('[Fragment '+str(i)+']' in out for i in range(1,5)))

    def test_unknown_format_is_not_silently_dropped(self):
        with self.assertRaises(ValueError):group_reference('unstructured text')


if __name__=='__main__':unittest.main()
