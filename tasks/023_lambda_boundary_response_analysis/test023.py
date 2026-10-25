import sys,math,unittest
import numpy as np
import common023 as c

class ResponseTests(unittest.TestCase):
    def test_all_legacy_grid_labels(self):
        sys.path.insert(0,str(c.ROOT/'tasks/019_support_boundary_screen'));import common019 as old
        scores=[dict(zip(c.LABELS,(s,n,100-s-n))) for s in range(101) for n in range(101-s)];z=c.logs(scores)
        for lam in c.ANCHORS:self.assertEqual([c.LABELS[i] for i in c.decode(z,lam)],[old.decision(s,lam) for s in scores])
    def test_zero_floor_and_tie(self):
        z=c.logs([dict(zip(c.LABELS,(0,50,50))),dict(zip(c.LABELS,(50,50,0))),dict(zip(c.LABELS,(50,0,50)))])
        self.assertEqual(z[0,0],math.log(1e-6));self.assertEqual(c.decode(z,0).tolist(),[1,1,2])
    def test_first_float_switch_and_predecessor(self):
        for scores in ((50,50,0),(10,80,10),(20,0,80),(100,0,0),(0,100,0)):
            z=c.logs([dict(zip(c.LABELS,scores))])[0];s=c.switching(z)
            if s['status']=='switch_in_0_4':
                self.assertFalse(c.is_S(z,s['previous_nonS_lambda']));self.assertTrue(c.is_S(z,s['first_S_lambda']));self.assertEqual(c.bits(s['first_S_lambda'])-c.bits(s['previous_nonS_lambda']),1)
    def test_switch_prediction_exhaustive(self):
        scores=[dict(zip(c.LABELS,(s,n,100-s-n))) for s in range(101) for n in range(101-s)];z=c.logs(scores)
        for row in z:
            sw=c.switching(row)
            for lam in (0,.01,1.99,2,2.01,4):
                expected=sw['status']=='already_S_at_0' or (sw['first_S_lambda'] is not None and lam>=sw['first_S_lambda'])
                self.assertEqual(c.is_S(row,lam),expected)
    def test_grid_and_domain(self):
        self.assertEqual(len(c.GRID),401);self.assertTrue(all(a in c.GRID for a in c.ANCHORS))
        for x in (-.01,4.1,float('nan')):
            with self.assertRaises(ValueError):c.decode(np.zeros((1,3)),x)
    def test_illegal_scores(self):
        for ss in ((True,49,50),(1.,49,50),(10,20,30),(-1,51,50)):
            with self.assertRaises(ValueError):c.logs([dict(zip(c.LABELS,ss))])
    def test_RHW_not_all_falseS_are_harms(self):
        rows=[dict(proposition_id=str(i),subject_id='mock',human_gt=label) for i,label in enumerate(c.LABELS)]
        result=c.point(rows,np.array([0,0,0]),np.array([1,1,1]),np.array([1,1,1]))
        self.assertEqual((result['rescue'],result['harm'],result['wrong_to_falseS'],result['delta_correct_U0']),(1,1,1,0))
    def test_author_patient_cohort_repeat_isolation(self):
        rows=c.jl(c.OUT/'preparation_001/scores.jsonl')
        a=c.subset(rows,'019');r0=c.subset(rows,'020_R0');r1=c.subset(rows,'020_R1');pooled=c.subset(rows,'pooled_R0')
        self.assertEqual((len(a),len(r0),len(r1),len(pooled)),(650,879,879,1529))
        self.assertEqual({r['proposition_id'] for r in r0},{r['proposition_id'] for r in r1})
        self.assertFalse({r['subject_id'] for r in a}&{r['subject_id'] for r in r0})
        self.assertTrue(all(r['repeat']==0 for r in pooled))
    def test_replay_output_safety(self):
        from verify023 import safe_output
        for p in (c.OUT/'analysis_001',c.ROOT/'outputs/020_lambda2_patient_validation/not_allowed',c.ROOT/'data/not_allowed'):
            with self.assertRaises(ValueError):safe_output(p)
    def test_fixed_grid_remains_diagnostic(self):
        obj=c.read(c.OUT/'analysis_001/execution.json')
        self.assertEqual(obj['fixed_lambda'],2);self.assertFalse(obj['lambda_reselected']);self.assertEqual(obj['new_API_calls'],0)

if __name__=='__main__':unittest.main()
