import unittest
from unittest.mock import patch
from construct089 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.src=dict(prefix='',units=[dict(id='U001',text='Patient may have fever.\n',proxy_tokens=6),dict(id='U002',text='No fever on day two.\n',proxy_tokens=6),dict(id='U003',text='Unrelated dressing.\n',proxy_tokens=3)])
        self.ex=dict(claim='Patient had fever.')
    def issue(self):return dict(unit_id='U002',quote='No fever on day two.',claim_part='fever',relation='Later negation limits event timing',why_not_covered='U001 gives possibility only, no later status',kind='limitation',duplicate_of_retained=[],dependencies=[])
    def test_whole_units(self):
        s=render_reference(self.src,['U001','U002']);self.assertIn('may have',s);self.assertIn('No fever',s)
        with self.assertRaises(ValueError):render_reference(self.src,['bad'])
    def test_unlocated_does_not_veto(self):
        out,acc,rej=repair(self.ex,self.src,['U001'],dict(issues=[dict(unit_id='U002',quote='may need background')],reminders=['preserve full']))
        self.assertEqual(out,['U001']);self.assertFalse(acc);self.assertEqual(len(rej),1)
    def test_concrete_add_once(self):
        out,acc,rej=repair(self.ex,self.src,['U001'],dict(issues=[self.issue()]));self.assertEqual(out,['U001','U002'])
        out2,acc2,rej2=repair(self.ex,self.src,out,dict(issues=[self.issue()]));self.assertEqual(out,out2);self.assertFalse(acc2)
    def test_duplicate_rejected(self):
        x=self.issue();x['duplicate_of_retained']=['U001'];self.assertEqual(repair(self.ex,self.src,['U001'],dict(issues=[x]))[0],['U001'])
    def test_coverage_preserves_counter(self):
        o=dict(information=[dict(claim_part='fever',relation='later negation',alternatives=[dict(unit_id='U002',quote='No fever')],dependencies=[])],selected_ids=['U001'],priority_ids=all_ids(self.src))
        self.assertEqual(coverage_select(self.ex,self.src,o,2)[0],['U002'])
    def test_Q_not_tied(self):
        ex=dict(self.ex,reference='a'*1300)
        with patch('construct089.construct',side_effect=[dict(selected_ids=all_ids(self.src),added_ids=[]),dict(selected_ids=['U001'],added_ids=[])] ) as mock:
            z=pair(ex,self.src,'synthetic');self.assertEqual(mock.call_count,2);self.assertEqual(z['Q4']['selected_ids'],['U001'])
    def test_budget(self):
        j=dict(body=body('test',{}),request_id='new')
        self.assertFalse(api.can_dispatch([dict(request_id='old',cost_or_unknown_cny=20)],[],j,0,20))
        self.assertFalse(api.can_dispatch([],[],j,0,0))
    def test_finite_recovery_and_invalid200(self):
        with patch('api089.attempt',side_effect=[dict(http_status=503),dict(http_status=200)]) as m:
            api.process({},0,sleep=lambda _:None);self.assertEqual(m.call_count,2)
        with patch('api089.attempt',return_value=dict(http_status=200,body_text='bad')) as m:
            api.process({},0,sleep=lambda _:None);self.assertEqual(m.call_count,1)
    def test_target_unchanged(self):
        t=dict(messages=[dict(role='system',content='old'),dict(role='user',content='')],model=MODEL,max_tokens=8192)
        b=make_body(t,'new','claim','evidence');self.assertEqual(json.loads(b['messages'][1]['content']),dict(proposition='claim',reference='evidence'));self.assertEqual(t['messages'][0]['content'],'old')
    def test_invalid_first(self):
        a=dict(valid=False,raw_verdict=None,final='Not Supported');b=dict(valid=True,raw_verdict='Supported',final='Supported')
        self.assertEqual(attribution(a,b,'Supported')['kind'],'invalid_or_fallback_related')
    def test_native_raw_survives_missing_scores(self):
        from analyze089 import native_fields
        raw,scores,errors=native_fields('{"verdict":"Supported","reason":"test"}')
        self.assertEqual(raw,'Supported');self.assertIsNone(scores)
        raw,scores,errors=native_fields('{"verdict":"Supported","verdict":"Not Supported"}')
        self.assertIsNone(raw)
if __name__=='__main__':unittest.main()
