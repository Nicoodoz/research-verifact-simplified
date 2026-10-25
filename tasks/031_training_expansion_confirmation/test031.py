import copy,json,unittest
import common031 as c
import api031 as a
class Tests(unittest.TestCase):
    def test_split_blind_and_disjoint(self):
        s=c.read(c.OUT/'planning_001/split.json');remain=sorted(s['expansion12']+s['confirmation12'],key=c.rank);self.assertEqual(remain[:12],s['expansion12']);self.assertEqual(len(set(s['original16']+remain)),40)
    def test_role_settings_and_payload(self):
        for role in ('score','peer','repeat','trace'):
            body=a.body('A proposition','1. Date: date | Text: evidence',role);self.assertEqual(json.loads(body['messages'][1]['content']),{'proposition':'A proposition','reference':'1. Date: date | Text: evidence'});self.assertEqual(body['max_tokens'],4096 if role in ('repeat','trace') else 2048);self.assertEqual(body['model'],'qwen3.8-27b' if role=='peer' else 'deepseek-v4-flash-0731')
    def test_score_duplicate_core_rules(self):
        content='{"verdict":"Supported","verdict":"Not Supported","label_scores":{"Supported":30,"Not Supported":60,"Not Addressed":10}}';tr=dict(http_status=200,body_text=json.dumps(dict(model='deepseek-v4-flash-0731',choices=[dict(message=dict(content=content),finish_reason='stop')])));j=dict(kind='chat',role='score',body=a.body('x','y','score'));self.assertEqual(a.parse(j,tr)['status'],'invalid_core_fields')
    def test_no_GT_in_metadata_material(self):
        rows=c.lines(c.OUT/'materials_001/inputs.jsonl');self.assertEqual(len(rows),2146);self.assertTrue(all(not set(r)&{'GT','human_gt','verdict','source_text','bhc'} for r in rows))
    def test_cost_reservation(self):
        j=dict(kind='chat',role='trace',body=a.body('x','y','trace'));tr=dict(http_status=200,body_text=json.dumps({'usage':{'prompt_tokens':400,'completion_tokens':200,'total_tokens':600}}));self.assertAlmostEqual(a.charge(j,tr)[0],.003);self.assertGreater(a.bound(j),a.charge(j,tr)[0]);self.assertEqual(a.charge(j,dict(http_status=0,body_text=''))[0],a.bound(j))
if __name__=='__main__':unittest.main()
