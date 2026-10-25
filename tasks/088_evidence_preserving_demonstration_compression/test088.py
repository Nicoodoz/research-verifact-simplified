import tempfile,unittest
from unittest.mock import patch
import common088 as c
import api088 as api
import construct088 as b

class Tests(unittest.TestCase):
    def setUp(self):
        self.reference='Hospital Admission Start: 2000-01-01\n'+''.join(f'{i}. Date: 2000-01-0{i}, Time: 01:00:00, Note Category: Nursing, Note ID: {i}, Raw characters: [0,40) | Text: If pain persists, do not stop therapy {i}.\n' for i in range(1,5))
        self.src=c.unitize(self.reference)
    def test_units_preserve_full_passage_qualifiers_metadata(self):
        self.assertEqual(c.render_reference(self.src,b.all_ids(self.src)),self.reference)
        s=c.render_reference(self.src,['U003','U001'])
        self.assertLess(s.index('Note ID: 1'),s.index('Note ID: 3'))
        self.assertIn('If pain persists, do not stop therapy 1.',s)
        self.assertNotIn('Note ID: 2',s)
        self.assertTrue(c.source_check(self.reference,self.src,['U001','U003'],s))
        with self.assertRaises(AssertionError):c.source_check(self.reference,self.src,['U001','U003'],s.replace('do not','do'))
        with self.assertRaises(ValueError):c.render_reference(self.src,['invented'])
    def test_only_example_reference_changes(self):
        examples=[dict(claim=str(i),reference=self.reference,physician_label=x) for i,x in enumerate(('Supported','Not Supported','Supported','Not Addressed'))]
        base=c.render_system('base','head',examples);changed=c.copy.deepcopy(examples);changed[1]['reference']=c.render_reference(self.src,['U001'])
        template=dict(model=c.MODEL,messages=[dict(role='system',content=base),dict(role='user',content='')],temperature=0,max_tokens=8192)
        x=c.make_body(template,base,'target','target reference');y=c.make_body(template,c.render_system('base','head',changed),'target','target reference')
        self.assertEqual(x['messages'][1],y['messages'][1]);self.assertEqual(x['max_tokens'],y['max_tokens'])
        self.assertEqual([(v['claim'],v['physician_label']) for v in changed],[(v['claim'],v['physician_label']) for v in examples])
    def test_label_blind_review_adds_source_only_once(self):
        ex=dict(claim='pain',physician_label='Not Supported',reference=self.reference,proposition_id='synthetic',sid='synthetic')
        replies=[({'selected_ids':['U001'],'priority_ids':b.all_ids(self.src),'preserve_full':False,'notes':''},'construct'),
                 ({'missing_ids':['U002'],'distorted_ids':[],'uncertain_after_adding_missing_ids':False,'issues':'source U002'},'review')]
        bodies=[]
        def job(phase,arm,pid,sid,body):bodies.append(body);return dict(body=body)
        with patch.object(api,'freeze_job',side_effect=job),patch.object(api,'call_json',side_effect=replies) as calls:
            z=b.construct(ex,self.src,'P4',100)
        self.assertEqual(calls.call_count,2);self.assertEqual(z['selected_ids'],['U001','U002'])
        payload=c.json.loads(bodies[1]['messages'][1]['content'])
        self.assertNotIn('physician_label',payload);self.assertNotIn('arm',payload)
    def test_uncertainty_retains_original_not_label_search(self):
        ex=dict(claim='pain',physician_label='Supported',reference=self.reference,proposition_id='synthetic',sid='synthetic')
        with patch.object(api,'freeze_job',return_value={}),patch.object(api,'call_json',return_value=({'selected_ids':['U001'],'priority_ids':b.all_ids(self.src),'preserve_full':True},'r')) as calls:
            z=b.construct(ex,self.src,'P4',100)
        self.assertEqual(z['selected_ids'],b.all_ids(self.src));self.assertEqual(calls.call_count,1)
    def test_length_matching_uses_whole_units(self):
        target=c.token_proxy(c.render_reference(self.src,['U001','U002']))
        ids=b.match_budget(self.src,['U001'],b.all_ids(self.src),target)
        self.assertEqual(ids,['U001','U002'])
    def test_budget_includes_all_phase_costs(self):
        j=dict(request_id='x',body=dict(model=c.MODEL,max_tokens=8192));q=dict(request_id='q',body=dict(model=c.BUILDER,max_tokens=3000))
        self.assertGreater(api.bound(j),api.bound(q))
        rows=[dict(request_id='previous_construct',cost_or_unknown_cny=19.99)]
        self.assertFalse(api.can_dispatch(rows,[],j,0,20))
        self.assertEqual(api.charge(dict(reserved_cny=.2),{'http_status':0}),.2)
    def test_finite_retry_and_success_not_repeated(self):
        with patch.object(api,'attempt',side_effect=[{'http_status':503},{'http_status':200}]) as call:
            api.process({},0,sleep=lambda _:None);self.assertEqual(call.call_count,2)
        with patch.object(api,'attempt',return_value={'http_status':200,'body_text':'invalid content'}) as call:
            api.process({},0,sleep=lambda _:None);self.assertEqual(call.call_count,1)
    def test_invalid_before_attribution(self):
        x=c.attribution(dict(valid=False,raw_verdict='Supported',final='Not Supported'),dict(valid=True,raw_verdict='Supported',final='Supported'),'Supported')
        self.assertEqual(x['kind'],'invalid_or_fallback_related');self.assertIsNone(x['raw_rescue'])

if __name__=='__main__':unittest.main(verbosity=2)
