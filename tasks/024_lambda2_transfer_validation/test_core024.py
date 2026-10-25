import json,unittest
import core024 as c
def tr(s,finish='stop'):
    return dict(http_status=200,body_text=json.dumps(dict(model=c.MODELS['deepseek'],choices=[dict(finish_reason=finish,message=dict(content=s))])))
class Core(unittest.TestCase):
    def test_explanation_conflict_preserved(self):
        s='{"verdict":"Supported","reason":"a","reason":"b","checks":9}'
        t=tr(s);before=t.copy();r=c.parse(t,False)
        self.assertEqual(r['status'],'valid_with_format_anomaly');self.assertEqual(r['verdict'],'Supported');self.assertIsNone(r['parsed']['reason']);self.assertEqual(t,before)
    def test_score_core(self):
        for scores,valid in [({'Supported':80,'Not Supported':15,'Not Addressed':5},True),({'Supported':80,'Not Supported':15,'Not Addressed':4},False),({'Supported':80.0,'Not Supported':15,'Not Addressed':5},False)]:
            r=c.parse(tr(json.dumps(dict(verdict='Supported',label_scores=scores))),True)
            self.assertEqual(r['status'] in c.VALID,valid)
    def test_core_conflicts(self):
        for s in ['{"verdict":"Supported","verdict":"Not Supported"}','{"verdict":"Supported","label_scores":{"Supported":80,"Supported":70,"Not Supported":15,"Not Addressed":5}}']:
            self.assertEqual(c.parse(tr(s),'label_scores' in s)['status'],'invalid_core_fields')
    def test_identical_core_duplicates(self):
        self.assertIn(c.parse(tr('{"verdict":"Supported","verdict":"Supported"}'),False)['status'],c.VALID)
    def test_partial_core(self):
        self.assertIn(c.parse(tr('{"verdict":"Supported","reason":"unfinished','length'),False)['status'],c.VALID)
        self.assertEqual(c.parse(tr('{"verdict":"Supported","label_scores":','length'),True)['status'],'invalid_core_fields')
        self.assertEqual(c.parse(tr('{"verdict":"Supported","verdict":','length'),False)['status'],'invalid_core_fields')
    def test_checks_do_not_hide_core(self):
        s='{"verdict":"Supported","checks":{"verdict":"Supported","verdict":"Not Supported"}}'
        self.assertIn(c.parse(tr(s),False)['status'],c.VALID)
if __name__=='__main__':unittest.main()
