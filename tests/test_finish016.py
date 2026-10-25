"""Offline guards for completing existing016 without replacing successful answers."""
from pathlib import Path
import sys
import unittest
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tasks/016_disagreement_triggered_review_validation'))
import common016 as c
from finish016 import assert_jobs
from finish_io016 import collect,base_labels,ORIGINAL,FINAL

class Finish016Tests(unittest.TestCase):
    def test_prior_receipts_cost_and_coverage(self):
        values,attempts,total=collect(False)
        labels,provenance=base_labels(values)
        self.assertEqual(sum('v4_first' in v for v in labels.values()),601)
        self.assertEqual(sum('qwen' in v for v in labels.values()),125)
        self.assertAlmostEqual(total,11.38592123,places=8)
        jobs=c.jsonlines(FINAL/'stage1/base_preparation_001/jobs.jsonl')
        self.assertEqual(len(jobs),476)
        assert_jobs(jobs,{'qwen'},values)
        old={j['request_id']:j for j in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl')}
        self.assertTrue(all(j==old[j['request_id']] for j in jobs))
        self.assertGreater(sum('unknown' in a['charge_basis'] for a in attempts),0)

    def test_success_requeue_and_hidden_input_rejected(self):
        job=c.jsonlines(FINAL/'stage1/base_preparation_001/jobs.jsonl')[0]
        with self.assertRaises(ValueError):assert_jobs([job],{'qwen'},[job['request_id']])
        bad=deepcopy(job)
        payload=c.pilot.strict_json(bad['body']['messages'][1]['content']);payload['human_gt']='Supported'
        bad['body']['messages'][1]['content']=c.canonical(payload)
        with self.assertRaises(ValueError):assert_jobs([bad],{'qwen'})

if __name__=='__main__':unittest.main()
