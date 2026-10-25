"""Synthetic invariants for the numerical extension; no evaluation-set model selection."""
import unittest
import numpy as np
import common as c
import learning as l

class Tests(unittest.TestCase):
    def setUp(self):
        rng=np.random.RandomState(35);self.z=np.log(rng.dirichlet([2,1,1],60));self.y=np.arange(60)%3
    def test_positive_temperature_preserves_labels(self):
        for lam in (0,1.3,2,4):
            v=self.z.copy();v[:,0]+=lam
            for beta in (.05,.3,1,5):np.testing.assert_array_equal(c.decode(v),c.decode(beta*v))
    def test_ties(self):
        np.testing.assert_array_equal(c.decode(np.array([[1,1,0],[1,0,1],[0,1,1],[0,0,0]],float)),[1,2,1,1])
    def test_temperature_objective(self):
        m=l.temperature(self.z,self.y,2);v=self.z.copy();v[:,0]+=2
        self.assertLessEqual(l.nll(v*m['beta'],self.y),l.nll(v,self.y)+1e-9)
    def test_joint_gradient(self):
        x=np.array([.4,.7]);_,g=l.joint_objective(x,self.z,self.y);fd=[]
        for j in range(2):
            d=np.zeros(2);d[j]=1e-6
            fd.append((l.joint_objective(x+d,self.z,self.y)[0]-l.joint_objective(x-d,self.z,self.y)[0])/2e-6)
        np.testing.assert_allclose(g,fd,atol=1e-7)
    def test_joint_feasible_and_improves(self):
        m=l.joint(self.z,self.y);t=l.temperature(self.z,self.y,2)
        self.assertGreaterEqual(m['lam'],-1e-6);self.assertLessEqual(m['lam'],4+1e-6)
        self.assertLessEqual(m['train_nll'],t['train_nll']+1e-7)
    def test_candidate_constraints(self):
        task,robust,table=l.states(self.z,self.y,[str(i//10) for i in range(60)])
        anchor=next(r for r in table if r['lam']==2)
        for lam in (task,robust):
            r=next(r for r in table if r['lam']==lam)
            self.assertGreaterEqual(r['correct'],anchor['correct']);self.assertLessEqual(r['false_S'],anchor['false_S'])
    def test_probability_normalization(self):
        np.testing.assert_allclose(np.exp(l.logprob(self.z)).sum(1),1,atol=1e-12)
    def test_socket_blocked(self):
        import socket
        with self.assertRaises(RuntimeError):socket.create_connection(('example.com',443))
    def test_logit_ratio_equivalence_away_ties(self):
        lam=2.;v=self.z.copy();v[:,0]+=lam
        np.testing.assert_array_equal(c.decode(v)==0,lam>self.z[:,1:].max(1)-self.z[:,0])

if __name__=='__main__':unittest.main(verbosity=2)
