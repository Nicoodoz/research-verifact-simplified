import copy,math,unittest
import numpy as np
import common025 as c
import frontier025 as f
import learning025 as l
class RiskStudy(unittest.TestCase):
    def test_exact_breakpoint_and_tie(self):
        for sc in ({'Supported':20,'Not Supported':70,'Not Addressed':10},{'Supported':0,'Not Supported':100,'Not Addressed':0},{'Supported':50,'Not Supported':50,'Not Addressed':0}):
            z=c.logs(sc);t=c.first_switch(z);self.assertEqual(c.decode(z,t),0);self.assertNotEqual(c.decode(z,np.nextafter(t,-np.inf)),0)
        self.assertEqual(c.decode(c.logs({'Supported':0,'Not Supported':50,'Not Addressed':50}),0),1)
    def test_global_complete_not_limited_to_two(self):
        r=dict(scores={'Supported':0,'Not Supported':100,'Not Addressed':0},u0=1,human_gt='Supported')
        times,p=f.global_states([r]);self.assertGreater(max(times),4);self.assertEqual(p[-1,0],0)
    def test_mixture_removes_discrete_false_advantage(self):
        v=f.matched([0,10,20],[0,10,30],10,12)
        self.assertEqual(v['R_gain_vs_global'],2);self.assertEqual(v['R_gain_vs_mixture'],-3)
    def test_zero_cost_plateau(self):
        v=f.matched([0,0,1,2],[0,3,3,5],0,2)
        self.assertEqual(v['global_R_at_risk'],3);self.assertEqual(v['R_gain_vs_mixture'],-1)
    def test_outer_patient_label_invariance(self):
        rows=[]
        for sid in range(4):
            for j in range(6):
                rows.append(dict(subject_id=str(sid),proposition_id=f'{sid}-{j}',candidate=True,human_gt='Supported' if j%2 else 'Not Supported',features={'s':j/10+sid/100}))
        original,audit=l.oof(rows,rows,['s']);changed=copy.deepcopy(rows)
        for r in changed:
            if r['subject_id']=='0':r['human_gt']='Not Addressed'
        rerun,_=l.oof(changed,changed,['s'])
        for r in rows:
            if r['subject_id']=='0':self.assertEqual(original[r['proposition_id']],rerun[r['proposition_id']])
        for fold in audit:
            self.assertNotIn(fold['held_patient'],fold['training_patients'])
            for inner in fold['inner_folds']:self.assertNotIn(inner['held_patient'],inner['training_patients']);self.assertNotIn(fold['held_patient'],inner['training_patients'])
    def test_feature_whitelist_and_metadata_exclusion(self):
        m=dict(text='No fever 12',reference='Header\n1. Date: 2000-01-01, Note ID: 123 | Text: No fever. Value 12.')
        x=c.evidence_features(m);m.update(subject_id='secret',author_type='human',human_gt='Supported')
        self.assertEqual(x,c.evidence_features(m));self.assertEqual(set(x),set(c.E_NAMES))
        self.assertFalse({'author_type','subject_id','human_gt'}&set(sum(c.METHODS.values(),[])))
    def test_single_class_fallback(self):
        rr=[dict(subject_id='x',proposition_id='a',human_gt='Supported',features={'s':.5})]
        predict,meta=l.fit(rr,['s']);self.assertTrue(meta['constant_fallback']);self.assertAlmostEqual(predict(rr)[0],2/3)
if __name__=='__main__':unittest.main()
