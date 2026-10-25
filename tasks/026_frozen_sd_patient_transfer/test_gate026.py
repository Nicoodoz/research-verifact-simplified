"""Frozen gate and conditional scope checks. No HTTP client calls."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import common026 as c
class Scope(unittest.TestCase):
    def test_final_fit_reproduces_from_development_only(self):
        gate=c.read(c.OUT/'gate_freeze/gate.json');train=[r for r in c.lines(c.ROOT/'outputs/025_lambda_flip_risk_separability/preparation_001/rows.jsonl') if r['group']=='024_D' and r['candidate']]
        predict,model=c.learning.fit(train,c.risk.METHODS['SD']);threshold,_=c.learning.training_threshold(train,c.risk.METHODS['SD'])
        self.assertEqual(gate['threshold'],threshold)
        for key in ('coef','mean','scale','intercept'):self.assertEqual(gate[key],model[key])
        validation=c.csvread(c.OUT/'preparation_001/cohort.csv');self.assertTrue(set(gate['training_patients']).isdisjoint(r['subject_id'] for r in validation))
        q={r['proposition_id']:r for r in c.lines(c.ROOT/'outputs/025_lambda_flip_risk_separability/preparation_001/rows.jsonl') if r['group']=='024_Q'}
        for r,p in zip(train,predict(train)):self.assertAlmostEqual(c.infer(gate,r['scores'],q[r['proposition_id']]['scores'])['prob'],p,places=12)
    def test_qwen_not_eligible_before_candidate_freeze(self):
        with tempfile.TemporaryDirectory() as td,patch.object(c,'OUT',Path(td)):
            with self.assertRaises(ValueError):c.eligible([], 'qwen')
    def test_scalar_tie_and_lambda_unchanged(self):
        for s in range(0,101,5):
            scores=dict(zip(c.LABELS,[s,100-s,0]))
            for lam in (0,2):
                expected=max((1,2,0),key=lambda i:c.math.log(max(scores[c.LABELS[i]]/100,1e-6))+(lam if i==0 else 0))
                self.assertEqual(c.risk.decode(c.risk.logs(scores),lam),expected)
if __name__=='__main__':unittest.main()
