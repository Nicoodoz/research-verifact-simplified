import unittest,sys
import numpy as np
from scipy.optimize._numdiff import approx_derivative
import common022 as c
import calibration022 as k

class CalibrationTests(unittest.TestCase):
    def test_all_integer_scores_degenerate_exactly_to_U2(self):
        ss=[dict(zip(c.LABELS,(s,n,100-s-n))) for s in range(101) for n in range(101-s)]
        z=k.scores_to_z(ss)
        self.assertTrue(np.array_equal(k.labels(k.transform(z,'C',[2,2])),k.labels(k.transform(z,'U2'))))
        sys.path.insert(0,str(c.ROOT/'tasks/019_support_boundary_screen'));import common019
        self.assertEqual([c.LABELS[i] for i in k.labels(k.transform(z,'U2'))],[common019.decision(s,2) for s in ss])
    def test_zero_floor_and_ties(self):
        z=k.scores_to_z([dict(zip(c.LABELS,(0,50,50))),dict(zip(c.LABELS,(50,50,0))),dict(zip(c.LABELS,(50,0,50)))])
        self.assertAlmostEqual(z[0,0],np.log(1e-6));self.assertEqual(k.labels(z).tolist(),[1,1,2])
    def test_illegal_scores(self):
        for ss in ((True,49,50),(10,20,30),(-1,50,51),(1.,49,50)):
            with self.assertRaises(ValueError):k.scores_to_z([dict(zip(c.LABELS,ss))])
    def test_positive_temperature_same_argmax(self):
        z=np.array([[0.,0.,-1.],[-2.,0.,0.],[1.,0.,0.]])
        for a in (.05,1,5):self.assertTrue(np.array_equal(k.labels(z),k.labels(k.transform(z,'T',[a]))))
    def test_ns_na_order_preserved(self):
        z=np.random.RandomState(2).normal(size=(40,3));v=k.transform(z,'C',[-4,5])
        self.assertTrue(np.array_equal(z[:,1:],v[:,1:]))
    def test_analytic_gradient_all_methods(self):
        z=np.random.RandomState(4).normal(size=(30,3));y=np.arange(30)%3
        for kind in c.LEARNED:
            b,x,center,reg,bounds=k.features(z,kind);t=center+.1
            f=lambda a:k.objective(a,b,x,y,center,reg)[0]
            np.testing.assert_allclose(k.objective(t,b,x,y,center,reg)[1],approx_derivative(f,t).reshape(-1),atol=1e-7)
    def test_patient_isolation_and_repeat_weight(self):
        rows=c.jl(c.OUT/'preparation_001/rows.jsonl')
        for fold in range(4):
            train,test=k.split_indices(rows,fold)
            self.assertFalse({rows[i]['subject_id'] for i in train}&{rows[i]['subject_id'] for i in test})
            self.assertTrue(all(rows[i]['repeat']==0 for i in train))
            self.assertEqual(len(train),len({rows[i]['proposition_id'] for i in train}))
            self.assertEqual(sum(rows[i]['repeat']==0 for i in train+test),1529)
    def test_repeated_claim_rejected(self):
        rows=c.jl(c.OUT/'preparation_001/rows.jsonl');fold=(rows[0]['fold']+1)%4
        with self.assertRaises(ValueError):k.split_indices(rows+[rows[0]],fold)
    def test_input_not_mutated_or_method_specific(self):
        z=np.random.RandomState(7).normal(size=(25,3));y=np.arange(25)%3;original=z.copy()
        for kind in c.LEARNED:k.transform(z,kind,k.fit(z,y,kind)['theta'])
        np.testing.assert_array_equal(z,original)
    def test_uniform_probability_metrics(self):
        from analyze022 import quality
        v,b=quality(np.array([0,1,2]),np.zeros((3,3)))
        self.assertAlmostEqual(v['NLL'],np.log(3));self.assertAlmostEqual(v['Brier'],2/3)
        self.assertEqual(sum(x['n'] for x in b if x['class_name']=='top'),3)
    def test_budget_restore_dedup_and_unknown_retained(self):
        from budget022 import total
        a={'attempt_id':'mock-unknown','cost_or_reservation_cny':'.4'}
        b={'attempt_id':'mock-new-success','cost_or_reservation_cny':'.1'}
        self.assertEqual(str(total([a,a,b])),'0.5')
        self.assertEqual(str(total([])),'0')
        with self.assertRaises(ValueError):total([a,dict(a,cost_or_reservation_cny='.1')])
        with self.assertRaises(ValueError):total([{'attempt_id':'mock','cost_or_reservation_cny':'80.1'}])
    def test_evaluation_patient_labels_cannot_change_training_fit(self):
        rows=c.jl(c.OUT/'preparation_001/rows.jsonl');train,test=k.split_indices(rows,0)
        z=k.scores_to_z([r['scores'] for r in rows]);y=np.array([c.LABELS.index(r['human_gt']) for r in rows]);modified=y.copy();modified[test]=(modified[test]+1)%3
        self.assertEqual(k.fit(z[train],y[train],'C')['theta'],k.fit(z[train],modified[train],'C')['theta'])

if __name__=='__main__':unittest.main()
