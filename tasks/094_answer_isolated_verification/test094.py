import json,unittest
import common094 as c
import method094 as m
class Checks(unittest.TestCase):
    def test_input_isolation(self):
        row={'text':'The line was removed on day two.','reference':'record'};q={'question':'What is documented about line status?','claimed_value':'removed'}
        v=m.qa_body(row,q,'V');b=m.qa_body(row,q,'Q');vp=json.loads(v['messages'][1]['content']);qp=json.loads(b['messages'][1]['content'])
        self.assertEqual(set(qp),{'question','reference'});self.assertEqual(vp.pop('unverified_claim'),row['text']);self.assertEqual(vp,qp)
        v['messages'][1]=b['messages'][1];self.assertEqual(v,b)
    def test_answer_leak_rejected(self):
        def tr(q):return {'body_text':json.dumps({'choices':[{'message':{'content':json.dumps(q)}}]})}
        q=dict(applicable=True,question='Was the line removed?',answer_span='removed',claimed_value='removed',target='status')
        self.assertFalse(m.parse_question(tr(q),'The line was removed.')['valid'])
        q['question']='What is documented about line status, if anything?'
        self.assertTrue(m.parse_question(tr(q),'The line was removed.')['valid'])
    def test_source_binding(self):
        ref='1. Date: today | Text: Line remained.\n2. Date: yesterday | Text: Removal planned.'
        o=dict(status='answered',candidates=[dict(answer='in place',time='today',state='observed',evidence=[dict(reference_id=1,quote='Line remained.')])])
        def tr():return {'body_text':json.dumps({'choices':[{'message':{'content':json.dumps(o)}}]})}
        self.assertTrue(m.parse_qa(tr(),ref)['valid']);o['candidates'][0]['evidence'][0]['reference_id']=2
        self.assertFalse(m.parse_qa(tr(),ref)['valid'])
    def test_final_preserves_C48(self):
        t=c.read(c.PRIVATE/'judge_template.json');r=c.lines(c.PRIVATE/'inputs.jsonl')[0]
        b=m.judge_body(t,r);v=m.judge_body(t,r,dict(question='neutral',claimed_value='hypothesis'),dict(status='insufficient',candidates=[]))
        self.assertEqual(json.loads(b['messages'][1]['content'])['reference'],json.loads(v['messages'][1]['content'])['reference'])
        for key in ['response_format','model','max_tokens','temperature','enable_thinking','reasoning_effort']:self.assertEqual(b[key],v[key])
    def test_full_budget(self):
        f=c.read(c.OUT/'design_freeze.json');self.assertLess(f['main_all_stage_upper_cny']+f['preflight_upper_cny']+2,20)
if __name__=='__main__':unittest.main()
