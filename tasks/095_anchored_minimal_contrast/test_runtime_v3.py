import unittest,json
import pricing095_v3 as p
from run095_v3 import remaining_baseline
class Runtime(unittest.TestCase):
    def test_unknown_usage_never_releases(self):
        t=dict(http_status=0,outcome_unknown=True,started_utc='2026-09-27T15:00:00+00:00',ended_utc='2026-09-27T15:01:00+00:00',body_text=json.dumps(dict(model='deepseek-v4-flash-0731',usage=dict(prompt_tokens=1000,completion_tokens=100))))
        self.assertEqual(p.charge({'bound_cny':1},t),1)
        t['http_status']=500;t['outcome_unknown']=False;self.assertEqual(p.charge({'bound_cny':1},t),1)
        t['http_status']=200;self.assertAlmostEqual(p.charge({'bound_cny':1},t),.00195)
    def test_cross_phase_B_reuse(self):
        jobs=[dict(id='a',body_sha256='A'),dict(id='b',body_sha256='B'),dict(id='c',body_sha256='C')]
        succ={'different_rid':dict(job=dict(id='a',body_sha256='A',arm='B',phase='method')),'not_B':dict(job=dict(id='b',body_sha256='B',arm='C',phase='method')),'wrong_body':dict(job=dict(id='c',body_sha256='other',arm='B',phase='baseline'))}
        self.assertEqual([j['id'] for j in remaining_baseline(jobs,succ)],['b','c'])
if __name__=='__main__':unittest.main()
