"""Prospective inference/evaluation contract tests using old training data or synthetic rows."""
import json,unittest
import numpy as np
import common031 as c
import api031 as a
from fit_predict031 import infer
from analyze031 import states,ci
class Tests(unittest.TestCase):
    def test_existing_feature_parity(self):
        source=c.lines(c.ROOT/'outputs/028_traceable_claim_evidence_verification/analysis_001/normalized.jsonl');roles={(r['proposition_id'],r['arm']):r for r in source};old={r['proposition_id']:r for r in c.read(c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/analysis_002/candidates.json')}
        for row in c.lines(c.base.PREP/'features.jsonl'):
            pid=row['proposition_id'];scores=old[pid];f=c.base.score_features(scores['D_scores'],scores['Q_scores']);f.update(c.base.new_features(roles[pid,'repeat'],roles[pid,'trace']))
            for method in 'ABCD':np.testing.assert_allclose([f[k] for k in c.base.FEATURES[method]],[row['features'][k] for k in c.base.FEATURES[method]],rtol=0,atol=1e-12)
            trace=roles[pid,'trace'];left=c.base.new_features(dict(status='valid',verdict='Supported'),trace);right=c.base.new_features(dict(status='valid',verdict='Not Addressed'),trace)
            self.assertEqual([left[k] for k in c.base.SEMANTIC+c.base.QUALITY],[right[k] for k in c.base.SEMANTIC+c.base.QUALITY])
    def test_before_models_training_isolation_and_inference(self):
        forbidden=set(c.read(c.OUT/'planning_001/split.json')['confirmation12']);features=c.lines(c.base.PREP/'features.jsonl')
        for method in 'ABCD':
            model=c.read(c.OUT/'before_models'/f'{method}.json');self.assertTrue(forbidden.isdisjoint(model['final_fit']['training_patients']));self.assertEqual(model['final_fit']['training_ids'],[r['proposition_id'] for r in features]);v=infer(model,features[0]['features']);self.assertEqual(v['keep'],v['probability']>=model['threshold'])
    def test_fallback_remains_U0_at_every_curve_point(self):
        rows=[dict(proposition_id='missing',candidate=True,u0=1),dict(proposition_id='ok',candidate=True,u0=2),dict(proposition_id='notcandidate',candidate=False,u0=0)];source={'missing':dict(methods={'m':dict(prediction=1,status='fallback_U0_missing_aux')}),'ok':dict(methods={'m':dict(prediction=0,probability=.7)}),'notcandidate':dict(methods={'m':dict(prediction=0)})};_,pp=states(rows,source,'m');self.assertTrue(np.all(pp[:,0]==1));self.assertTrue(np.all(pp[:,2]==0))
    def test_primary_multiplicity_interval(self):
        z=ci(np.arange(1000),True);self.assertLess(z['ci97_5_Bonferroni2'][0],z['ci95'][0]);self.assertGreater(z['ci97_5_Bonferroni2'][1],z['ci95'][1])
if __name__=='__main__':unittest.main()
