import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import common096 as c
import live_run096 as r
class Tests(unittest.TestCase):
    def test_invalid_http200_never_resent(self):
        with tempfile.TemporaryDirectory() as td,patch.object(r,'P',Path(td)),patch.object(r,'request',return_value=(b'{}',dict(http_status=200,outcome_unknown=False,started_utc=c.now(),ended_utc=c.now(),elapsed_seconds=1))) as req:
            j=dict(id='test',request_id='test',body={},body_sha256=c.digest({}))
            with self.assertRaisesRegex(RuntimeError,'MODEL_MISMATCH'):r.invoke(j,'test')
            self.assertEqual(r.invoke(j,'test')[1],200);self.assertEqual(req.call_count,1)
    def test_frozen_requests_and_nested_panels(self):
        jj=r.jobs();self.assertEqual(len(jj),1143);self.assertEqual(len({j['request_id'] for j in jj}),1143)
        ns=[{x['id'] for x in c.lines(r.O/f'natural{n}.jsonl')} for n in [400,600,800]]
        self.assertTrue(ns[0]<=ns[1]<=ns[2]);bs=c.read(r.O/'benchmark_plan.json');ids=[i for s in bs.values() for i in s['ids']]
        self.assertEqual(len(ids),len(set(ids)));self.assertTrue(set(ids)<=ns[0])
        self.assertTrue(all(x['B_raw_valid'] for x in c.lines(r.O/'natural800.jsonl')))
        self.assertFalse(ns[2]&{x['id'] for x in c.lines(r.O/'diagnostic200.jsonl')})
        old={j['id']:j for j in c.lines(c.PRIVATE/'jobs.jsonl') if j['stage']=='calibration'}
        for j in jj:
            if j['stage']=='calibration':self.assertEqual(j,old[j['id']])
            self.assertEqual(set(json.loads(j['body']['messages'][1]['content'])),{'proposition','reference'})
    def test_unknown_retry_requires_idle(self):
        with patch.object(r,'probe',return_value=(b'vllm:num_requests_running 1\nvllm:num_requests_waiting 0\n',dict(http_status=200))):self.assertFalse(r.idle())
if __name__=='__main__':unittest.main()
