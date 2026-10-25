import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tasks/015_disagreement_adjudication'))
import common015 as c
from run015 import next_status

class DisagreementTests(unittest.TestCase):
    def setUp(self):
        self.body=dict(model=c.MODEL,messages=[dict(role='system',content='Original definitions'),
            dict(role='user',content=c.canonical(dict(proposition='A claim',reference='[1] frozen evidence')))],
            temperature=0,max_tokens=2048,enable_thinking=False,n=1,stream=False,response_format={'type':'json_schema'})
        self.v=c.canonical(dict(verdict='Supported',summary='Reason one',checks=[]))
        self.q=c.canonical(dict(verdict='Not Addressed',summary='Reason two',checks=[]))

    def test_only_candidate_payload_differs(self):
        before=copy.deepcopy(self.body)
        a=c.build_body(self.body,'p',self.v,self.q,'adjudication')
        b=c.build_body(self.body,'p',self.v,self.q,'evidence_only')
        x=json.loads(a['messages'][1]['content']);y=json.loads(b['messages'][1]['content'])
        candidates=x.pop('candidate_judgments');self.assertEqual(x,y)
        a['messages'][1]['content']=c.canonical(x);self.assertEqual(a,b);self.assertEqual(self.body,before)
        self.assertEqual({c.canonical(k['judgment']) for k in candidates},{self.v,self.q})

    def test_hidden_fields_rejected(self):
        payload=json.loads(self.body['messages'][1]['content']);payload['human_gt']='Supported'
        self.body['messages'][1]['content']=c.canonical(payload)
        with self.assertRaises(ValueError):c.build_body(self.body,'p',self.v,self.q,'adjudication')

    def test_order_depends_on_id_only(self):
        self.assertEqual(c.candidate_order('p'),c.candidate_order('p'))
        self.assertEqual(set(c.candidate_order('p')),{'v4','qwen'})

    def test_bucket_agreement_not_called(self):
        self.assertEqual(c.bucket(dict(baseline='Supported',qwen='Supported',human_gt='Not Addressed')),'agreement')
        self.assertEqual(c.bucket(dict(baseline='Supported',qwen='Not Supported',human_gt='Not Addressed')),'both_wrong_disagreement')

    def test_usage_rate_and_discount(self):
        job={'body':self.body};usage=dict(prompt_tokens=1000,completion_tokens=200,total_tokens=1200)
        tr=dict(http_status=200,ended_utc='2026-09-15T04:00:00+00:00',body_text=c.canonical(dict(usage=usage,choices=[dict(message={})])))
        self.assertAlmostEqual(c.cost(job,tr)[0],.0048)
        tr['ended_utc']='2026-09-15T20:00:00+00:00'
        self.assertAlmostEqual(c.cost(job,tr)[0],.0024)

    def test_unknown_usage_reserve_and_no_200_retry(self):
        job={'body':self.body};tr=dict(http_status=0,body_text='')
        self.assertEqual(c.cost(job,tr)[0],c.bound(job))
        self.assertEqual(next_status(dict(http_status=200,body_text='invalid'),1,0,0),'received')
        self.assertEqual(next_status(dict(http_status=0,body_text=''),2,2,0),'failed_unknown')

if __name__=='__main__':unittest.main()
