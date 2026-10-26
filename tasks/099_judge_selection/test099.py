"""Offline checks for generation cost ceilings, parsing and model-only contrasts."""
import json
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
import common099 as c
import runtime099 as r
from verifact_research.inference.aliyun import Config

class Tests(unittest.TestCase):
    def tr(self,model,content,inp=1000,out=500,cached=200):
        return dict(http_status=200,outcome_unknown=False,body_text=json.dumps(dict(model=model,choices=[dict(finish_reason='stop',message=dict(content=content))],usage=dict(prompt_tokens=inp,completion_tokens=out,prompt_tokens_details=dict(cached_tokens=cached)))))
    def test_thinking_and_answer_both_charged(self):
        tr=self.tr('qwen3.8-27b','{}')
        amount,basis=r.charge(dict(model='qwen3.8-27b'),tr,.1)
        self.assertAlmostEqual(amount,(800*3+200*.6+500*12)/1e6);self.assertEqual(basis,'verified_usage')
    def test_unknown_and_model_mismatch_keep_reservation(self):
        self.assertEqual(r.charge(dict(model=c.MODELS[0]),dict(http_status=0),.12)[0],.12)
        self.assertEqual(r.charge(dict(model=c.MODELS[0]),self.tr(c.MODELS[1],'{}'),.12)[0],.12)
    def test_tier_boundary(self):
        self.assertEqual(r.price('qwen3.5-27b',128000)[:2],(.6,4.8))
        self.assertEqual(r.price('qwen3.5-27b',128001)[:2],(1.8,14.4))
    def test_direct_verdict_without_scores(self):
        p=c.parse(self.tr(c.MODELS[0],'{"verdict":"Not Supported","reason":"Different event."}'))
        self.assertTrue(p['valid']);self.assertEqual(p['verdict'],'Not Supported')
        self.assertFalse(c.parse(self.tr(c.MODELS[0],'{"verdict":"Supported","verdict":"Not Supported"}'))['valid'])
    def test_budget_stop_no_call(self):
        with tempfile.TemporaryDirectory(dir=c.PRIVATE) as tmp:
            with patch.object(c,'PRIVATE',Path(tmp)),patch.object(r,'load_config',return_value=Config('fixture')),patch.object(r.DirectClient,'send',side_effect=AssertionError('must not send')):
                con=r.db();con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',('old',1,c.MODELS[0],19.99,0,''));con.commit();con.close()
                j=dict(request_id='new',model=c.MODELS[0],body=dict(model=c.MODELS[0],messages=[],max_tokens=512))
                self.assertEqual(r.process(j,operating=20),'budget_stop')
    def test_scientific_freeze(self):
        f=c.read(c.OUT/'execution_freeze.json')
        for rel,d in f['files'].items():self.assertEqual(c.sha(c.ROOT/rel),d)
        jobs=c.lines(c.PRIVATE/'jobs.jsonl');self.assertEqual(len(jobs),len({j['request_id'] for j in jobs}))
        groups={}
        for j in jobs:groups.setdefault((j['id'],j['context'],j['repeat']),[]).append(j)
        for group in groups.values():
            self.assertEqual({j['model'] for j in group},set(c.MODELS))
            bodies=[{k:v for k,v in j['body'].items() if k!='model'} for j in group]
            self.assertTrue(all(b==bodies[0] for b in bodies))
            for j in group:
                self.assertEqual(j['body']['thinking_budget'],2048);self.assertEqual(j['body']['max_tokens'],512)
                self.assertNotIn('response_format',j['body']);self.assertNotIn('reasoning_effort',j['body'])
        for rel,d in f['unchanged_098_fingerprints'].items():self.assertEqual(c.sha(c.ROOT/rel),d)

if __name__=='__main__':unittest.main()
