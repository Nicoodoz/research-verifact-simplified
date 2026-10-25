"""Offline safeguards for 012's provenance and diagnostic boundaries."""
import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tasks/012_comparative_error_diagnosis'))
import study012 as s
from evidence012 import trace
from diagnose012 import locate

class Diagnosis012Tests(unittest.TestCase):
    def test_full_final_not_short_reason(self):
        text='Analysis says Supported tentatively.\n```json\n{"verdict":"Not Supported","reason":"contradicted"}\n```'
        values=s.final_json(text)
        self.assertEqual(len(values),1)
        self.assertEqual(values[0]['value']['verdict'],'Not Supported')
        self.assertEqual(text[values[0]['start']:values[0]['end']][0],'{')

    def test_quote_must_not_erase_negation_or_case(self):
        self.assertEqual(locate('No nausea','no nausea'),[])
        self.assertEqual(locate('No nausea; No nausea','No nausea'),[0,11])

    def test_cross_patient_trace_rejected(self):
        with self.assertRaises(AssertionError):
            trace({'subject_id':'A'},[],{'SUBJECT_ID':'B','TEXT':'X'},0,1)

    def test_frozen_source_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as tmp:
            base=Path(tmp);out=base/'out';out.mkdir();source=base/'frozen.txt';source.write_text('original',encoding='utf-8')
            (out/'value.json').write_text('{}',encoding='utf-8');s.seal(out,[source],[]);s.check(out)
            (base/'audit.md').write_text('normal later audit update',encoding='utf-8');s.check(out)
            source.write_text('changed',encoding='utf-8')
            with self.assertRaises(AssertionError):s.check(out)

    def test_error_union_includes_middle_system_only_error(self):
        self.assertEqual(s.direction('Supported','Supported','Supported'),'both_correct')
        self.assertTrue(any(v!='Supported' for v in ('Supported','Not Supported','Supported')))

if __name__=='__main__':unittest.main()
