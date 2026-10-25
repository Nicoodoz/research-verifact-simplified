"""Meaningful offline tests for intervention isolation, attribution, recovery, cap."""
import tempfile, unittest
from unittest.mock import patch
import common087 as c
import run087 as r

class Tests(unittest.TestCase):
    def setUp(self):
        self.ex=[dict(claim=f'claim{i}',reference=f'ref{i}',physician_label=k) for i,k in enumerate(('Supported','Not Supported','Supported','Not Addressed'))]
        self.header='\nEach example contains a proposition, EHR reference, and physician label.\n'
    def test_render_preserves_target_and_original_material(self):
        template={'model':c.MODEL,'messages':[{'role':'system','content':'base'},{'role':'user','content':'old'}],'response_format':{'type':'json_object'}}
        bodies={a:c.make_body(template,c.render('base',self.header,self.ex,a),'target claim','target reference') for a in c.ARMS}
        self.assertEqual(len({b['messages'][1]['content'] for b in bodies.values()}),1)
        self.assertEqual(template['messages'][1]['content'],'old')
        for a in ('F4','X4','CL4'):
            docs=[c.json.loads(s) for s in bodies[a]['messages'][0]['content'].splitlines() if s.startswith('{')]
            self.assertEqual([x['proposition'] for x in docs],[x['claim'] for x in self.ex])
            self.assertEqual([x['physician_label'] for x in docs],[x['physician_label'] for x in self.ex])
            if a=='CL4':self.assertTrue(all('reference' not in x for x in docs))
            else:self.assertCountEqual([x['reference'] for x in docs],[x['reference'] for x in self.ex])
            if a=='X4':self.assertEqual([x['reference'] for x in docs],['ref2','ref3','ref0','ref1'])
    def test_fallback_precedes_score_boundary(self):
        b=dict(valid=False,raw_verdict=None,final='Not Supported')
        n=dict(valid=True,raw_verdict='Not Supported',final='Supported')
        x=c.attribution(b,n,'Supported');self.assertEqual(x['kind'],'invalid_or_fallback_related');self.assertTrue(x['rescue']);self.assertIsNone(x['raw_rescue'])
        b.update(valid=True,raw_verdict='Not Supported')
        self.assertEqual(c.attribution(b,n,'Supported')['kind'],'valid_score_boundary_change')
        n['raw_verdict']='Supported'
        self.assertEqual(c.attribution(b,n,'Supported')['kind'],'raw_correctness_change')
    def test_retries_only_no_success(self):
        job={'request_id':'x','body':{'max_tokens':8192}}
        with patch.object(r,'attempt',side_effect=[{'http_status':0},{'http_status':503},{'http_status':200}]) as f:
            r.process(job,0,cli=object(),sleep=lambda _:None);self.assertEqual(f.call_count,3)
        with patch.object(r,'attempt',return_value={'http_status':200,'body_text':'invalid JSON'}) as f:
            r.process(job,0,cli=object(),sleep=lambda _:None);self.assertEqual(f.call_count,1)
        with patch.object(r,'attempt',return_value={'http_status':401}) as f:
            with self.assertRaises(RuntimeError):r.process(job,0,cli=object(),sleep=lambda _:None)
            self.assertEqual(f.call_count,1)
    def test_budget_includes_active_past_and_unknown(self):
        a=dict(request_id='active',body={'max_tokens':8192});b=dict(request_id='new',body={'max_tokens':8192})
        bound=r.reservation(a)
        rows=[dict(request_id='done',cost_or_unknown_cny=20-6*bound+.0001),dict(request_id='active',cost_or_unknown_cny=bound)]
        self.assertFalse(r.can_dispatch(rows,[a],b,0))
        rows[0]['cost_or_unknown_cny']-=.0002
        self.assertTrue(r.can_dispatch(rows,[a],b,0))
        req=dict(reservation_cny=.2,job=a)
        self.assertEqual(r.charge(req,None),.2);self.assertEqual(r.charge(req,{'http_status':0}),.2)
        self.assertEqual(r.charge(req,{'http_status':200,'body_text':'{}'}),.2)
    def test_success_resume_and_append_only(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'OUT',c.Path(tmp)),patch.object(r,'ROOT',c.Path(tmp)):
            p=c.Path(tmp)/'attempts'/'x';p.mkdir(parents=True)
            j=dict(request_id='x',id='id',sid='sid',arm='B',body={'max_tokens':8192})
            req=dict(job=j,attempt_no=1,created_utc='t',reservation_cny=.2)
            c.put(p/'request.json',req)
            tr=dict(http_status=200,body_text=c.canonical(dict(usage=dict(prompt_tokens=10,completion_tokens=20))))
            c.put(p/'receipt.json',dict(request_sha256=c.sha(p/'request.json'),transport=tr))
            rows,success,count=r.state();self.assertEqual(set(success),{'x'});self.assertEqual(count['x'],1)
            self.assertAlmostEqual(rows[0]['cost_or_unknown_cny'],.00021)
            with self.assertRaises(FileExistsError):c.put(p/'request.json',req)

if __name__=='__main__':unittest.main(verbosity=2)
