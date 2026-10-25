import unittest
import numpy as np
import common027 as x
from analyze027 import conflicts
class Diagnostics(unittest.TestCase):
    def test_ties_never_split(self):
        _,states=x.ranking_states([.2,.2,.8]);self.assertTrue(np.all(states[:,0]==states[:,1]));self.assertFalse(states[0].any());self.assertTrue(states[-1].all())
    def test_target_uses_actual_recalled_count(self):
        self.assertEqual(x.first_target(np.array([0,1,4]),np.array([0,1,3]),3),2)
    def test_exact_conflict_bound(self):
        f=dict(zip(x.c.METHODS['SD'],[0.]*12));scores=dict(zip(x.LABELS,[20,70,10]));rows=[dict(features=f,kind=k,proposition_id=str(i),subject_id=str(i),D_scores=scores,Q_scores=scores) for i,k in enumerate(['R','R','H'])]
        r=conflicts(rows);self.assertEqual(r['mixed_claims'],3);self.assertEqual(r['unavoidable_binary_errors'],1);self.assertEqual(r['oracle_min_risk_at_retention']['0.8'],1)
    def test_patient_auc_ignores_cross_patient_pairs(self):
        y=np.array([1,0,1,0]);s=np.array([.4,.2,.9,.8]);self.assertEqual(x.patient_auc(y,s,np.ones(4),['a','a','b','b']),1.)
    def test_no_two_class_auc_is_unknown(self):
        from analyze027 import auc
        self.assertIsNone(auc(np.array([1,1]),np.array([.2,.7])))
    def test_network_and_training_blocked(self):
        x.offline();import socket
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        with self.assertRaises(RuntimeError):socket.create_connection(('example.com',443))
        with self.assertRaises(RuntimeError):LogisticRegression().fit([[0],[1]],[0,1])
        with self.assertRaises(RuntimeError):StandardScaler().fit([[0],[1]])
if __name__=='__main__':unittest.main()
