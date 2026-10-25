import unittest,tempfile
from unittest.mock import patch
from engineering090 import synthetic_source
from normalize090 import *
import api090 as api
class Tests(unittest.TestCase):
    def setUp(self):
        self.src=synthetic_source(['The lamp might\n  be on.','On day 2 the lamp was off.','Unrelated wire.'])
        self.ex=dict(claim='The lamp was on on day 2.')
    def test_whitespace_unique_numeric_strict(self):
        z=locate('lamp might be on','The lamp might\n  be on.');self.assertTrue(z['valid']);self.assertEqual(z['original'],'lamp might\n  be on')
        self.assertFalse(locate('45 mm Hg','145 mm Hg')['valid']);self.assertFalse(locate('45 mm Hg','45 cm H2O')['valid'])
        self.assertFalse(locate('lamp','lamp and lamp')['valid'])
    def test_ID_objects_conflicts(self):
        z=ids([{'id':'U001','rank':2},{'unit_id':'U002','rank':1}],self.src);self.assertTrue(z['valid']);self.assertEqual(z['ids'],['U002','U001'])
        self.assertFalse(ids([{'id':'U001','unit_id':'U002'}],self.src)['valid']);self.assertFalse(ids(['U001','U001'],self.src)['valid'])
    def test_P_optional_ranking_no_fallback(self):
        o=dict(groups=[dict(claim_part='lamp',role='limitation',alternatives=[dict(unit_id='U001',quote='lamp might be on')],dependencies=[])],priority_ids=[{'id':'U001'}])
        p=select_p(self.ex,self.src,o,20);self.assertTrue(p['usable']);self.assertEqual(p['selected_ids'],['U001'])
        self.assertFalse(select_p(self.ex,self.src,dict(groups=[],selected_ids=['U001']),20)['usable'])
    def test_Q_no_padding_independent(self):
        q=select_q(self.ex,self.src,dict(selected_ids=['U001']),9999);self.assertEqual(q['selected_ids'],['U001'])
    def issue(self,uid='U002'):return dict(unit_id=uid,quote='On day 2 the lamp was off.',claim_part='on day 2',kind='limitation',relation='specific day status',why_not_covered='retained only says might',duplicate_of_retained=[],dependencies=[])
    def test_deleted_only_and_single_addition(self):
        p=repair(self.ex,self.src,['U001'],dict(issues=[self.issue()]));self.assertEqual(p['selected_ids'],['U001','U002'])
        p=repair(self.ex,self.src,['U001','U002'],dict(issues=[self.issue()]));self.assertFalse(p['accepted']);self.assertEqual(p['rejected'][0]['reason'],'not_deleted')
        p=repair(self.ex,self.src,['U001'],dict(issues=[self.issue('U999')]));self.assertFalse(p['accepted'])
    def test_duplicate_and_noop(self):
        src=synthetic_source(['On day 2 the lamp was off.','On day 2 the lamp was off.'])
        p=repair(self.ex,src,['U001'],dict(issues=[self.issue()]));self.assertFalse(p['accepted'])
        p=repair(self.ex,self.src,all_ids(self.src),dict(issues=[self.issue()]));self.assertFalse(p['accepted'])
    def test_conflicting_JSON_not_laundered(self):
        with self.assertRaises(ValueError):loads_unique('{"selected_ids":["U001"],"selected_ids":["U002"]}')
    def test_budget_and_finite_retry(self):
        j=dict(body={'model':MODEL,'max_tokens':8192,'messages':[]},request_id='new')
        self.assertFalse(api.can_dispatch([dict(request_id='old',cost_or_unknown_cny=40)],[],j,0,40))
        self.assertFalse(api.can_dispatch([dict(request_id='old',cost_or_unknown_cny=4)],[],j,0,4))
        with patch('api090.attempt',side_effect=[dict(http_status=503),dict(http_status=200)]) as m:
            api.process({},0,sleep=lambda _:None);self.assertEqual(m.call_count,2)
        with patch('api090.attempt',return_value=dict(http_status=200,body_text='invalid')) as m:
            api.process({},0,sleep=lambda _:None);self.assertEqual(m.call_count,1)
    def test_raw_survives_missing_scores(self):
        from analyze090 import native_fields
        raw,scores,_=native_fields('{"verdict":"Supported"}');self.assertEqual(raw,'Supported');self.assertIsNone(scores)
    def test_target_and_source_whole_units(self):
        b=make_body(dict(messages=[dict(role='system',content='old'),dict(role='user',content='old')]),'new','claim','source')
        self.assertEqual(json.loads(b['messages'][1]['content']),dict(proposition='claim',reference='source'))
        self.assertIn('might\n  be',render_reference(self.src,['U001']))
    def test_distinct_source_alternatives_are_not_exchangeable(self):
        from repair_construction_v2 import split_alternatives
        obj=dict(groups=[dict(claim_part='lamp',alternatives=[dict(unit_id='U001',quote='lamp might be on'),dict(unit_id='U002',quote='lamp was off')],dependencies=[])])
        fixed,audit=split_alternatives(self.src,obj);self.assertEqual(len(fixed['groups']),2)
        selected=select_p(self.ex,self.src,fixed,99);self.assertEqual(selected['selected_ids'],['U001','U002'])
if __name__=='__main__':unittest.main()
