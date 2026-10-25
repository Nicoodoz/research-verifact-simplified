"""Offline safeguards for 014; synthetic fixtures are never experimental answers."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tasks/014_qwen27b_baseline_comparison'))
import common014 as c
from run014 import next_status

class Qwen014Tests(unittest.TestCase):
    def fixture(self):
        job=dict(request_id='synthetic',proposition_id='synthetic',body=dict(model=c.MODEL,max_tokens=2048,
            messages=[dict(role='system',content='synthetic'),dict(role='user',content=c.canonical(dict(reference='1. synthetic')))]))
        response=dict(model=c.MODEL,choices=[dict(finish_reason='stop',message=dict(content=c.canonical(dict(verdict=c.LABELS[0],reason='test',checks=[])),reasoning_content=None))],
            usage=dict(prompt_tokens=100,completion_tokens=20,total_tokens=120))
        tr=dict(http_status=200,body_text=c.canonical(response),started_utc='2026-09-15T00:00:00+00:00',ended_utc='2026-09-15T00:00:01+00:00')
        return job,response,tr
    def test_qwen_cost_not_deepseek(self):
        j,r,t=self.fixture();self.assertAlmostEqual(c.cost(j,t)[0],.00054)
    def test_valid_label_kept_despite_checks(self):
        j,r,t=self.fixture();v=c.normalize(j,dict(transport=t));self.assertEqual(v['status'],'success');self.assertTrue(v['adherence_errors'])
    def test_truncated_never_scored_or_retried(self):
        j,r,t=self.fixture();r['choices'][0]['finish_reason']='length';t['body_text']=c.canonical(r)
        self.assertEqual(c.normalize(j,dict(transport=t))['status'],'failed');self.assertEqual(next_status(t,1,0,0),'received')
    def test_wrong_model_rejected(self):
        j,r,t=self.fixture();r['model']=c.V4;t['body_text']=c.canonical(r)
        self.assertEqual(c.normalize(j,dict(transport=t))['status'],'failed')
    def test_thinking_rejected(self):
        j,r,t=self.fixture();r['choices'][0]['message']['reasoning_content']='synthetic';t['body_text']=c.canonical(r)
        self.assertEqual(c.normalize(j,dict(transport=t))['status'],'failed')
    def test_unknown_reserved_and_limited(self):
        j,r,t=self.fixture();t.update(http_status=0,body_text='')
        self.assertEqual(c.cost(j,t)[0],c.bound(j));self.assertEqual(next_status(t,2,2,0),'failed_unknown')
    def test_balance_only_unanswered(self):
        j,r,t=self.fixture();t.update(http_status=402,body_text=c.canonical(dict(code=30001,data=None)))
        self.assertEqual(c.cost(j,t)[0],0);self.assertEqual(next_status(t,1,0,0),'pending')
        t['body_text']=c.canonical(dict(code=30001,data=None,usage={'prompt_tokens':1}))
        self.assertEqual(next_status(t,1,0,0),'configuration_pause')
    def test_configuration_pause_and_retries(self):
        self.assertEqual(next_status(dict(http_status=400,body_text=''),1,0,0),'configuration_pause')
        self.assertEqual(next_status(dict(http_status=429,body_text=''),3,0,3),'failed_service')
    def test_duplicate_json_label_rejected(self):
        j,r,t=self.fixture();r['choices'][0]['message']['content']='{"verdict":"Supported","verdict":"Not Supported"}';t['body_text']=c.canonical(r)
        self.assertEqual(c.normalize(j,dict(transport=t))['status'],'failed')

if __name__=='__main__':unittest.main()
