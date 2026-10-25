"""Synthetic tests: no clinical rows are read."""
import unittest
import numpy as np
import core037 as c
class Tests(unittest.TestCase):
    def test_vm_rule(self):
        np.testing.assert_array_equal(c.vm_switch(np.array([0,1,2,2]),np.array([1,2,1,0])),[0,1,1,2])
    def test_support_and_existing_NS(self):
        v=np.array([0,1,2,2]);s=np.array([1.,0.,.3,.8])
        for t in [0.,.5,1.1]:
            p=c.restore(v,s,t);np.testing.assert_array_equal(p==0,v==0);self.assertEqual(p[1],1)
    def test_ties_not_split(self):
        np.testing.assert_array_equal(c.restore(np.array([2,2,2]),np.array([.2,.2,.3]),.2),[1,1,1])
    def test_selection(self):
        y=np.array([0,1,1,2,2,0]);v=np.array([0,1,2,2,2,2]);m=np.array([0,1,1,2,2,2])
        r=c.select_threshold(y,v,m,np.array([.1,.8,.4,.1,.2,.3]),'ratio')
        self.assertEqual(r['target_NS_tp'],2);self.assertEqual(r['selected']['correct'],5)
        self.assertAlmostEqual(r['selected']['threshold'],.4)
    def test_zero_target(self):
        y=np.array([1,2]);v=np.array([2,2]);m=np.array([2,2]);s=np.array([.1,.2])
        self.assertTrue(c.select_threshold(y,v,m,s,'ratio')['selected']['eligible'])
    def test_patient_overlap(self):
        with self.assertRaises(AssertionError):c.split_meta([dict(id='a',sid='p')],[dict(id='b',sid='p')])
    def test_reserved_read_blocked(self):
        with self.assertRaises(RuntimeError):(c.ROOT/'outputs/036_final_validation/analysis_001/R0/predictions.csv').read_text()
    def test_network_blocked(self):
        with self.assertRaises(RuntimeError):c.socket.create_connection(('example.com',443))
    def test_correctness_identity(self):
        from analyze037 import transition
        d=transition([dict(y=t) for t in [0,1,2,1]],np.array([2,2,2,1]),np.array([1,1,1,1]))
        self.assertEqual(d['delta_correct'],d['NS_rescued']-d['NA_harmed']);self.assertEqual(d['delta_false_S'],0)
    def test_likelihood_vs_decision(self):
        q=np.array([[.1,.3,.6],[.7,.2,.1]]);p=c.cal.labels(np.log(q))
        new=c.restore(p,np.array([.4,.2]),.3)
        self.assertFalse(np.array_equal(p,new))
        self.assertEqual(c.probability_point(np.array([1,0]),np.log(q)),c.probability_point(np.array([1,0]),np.log(q).copy()))
if __name__=='__main__':unittest.main(verbosity=2)
