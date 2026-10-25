"""Synthetic preflight only; no patient data or outcome-based selection."""
import unittest
import numpy as np
import torch
import learning032 as l
from nli032 import pieces
class Test032(unittest.TestCase):
    def test_ties(self):
        self.assertEqual(l.decode(np.array([[0,0,-1],[0,-1,0],[-1,0,0]])).tolist(),[1,2,1])
    def test_zero_residual(self):
        for family in ['score','fixed','attention','attention_single','attention_no_lambda']:
            n=l.Head(family,16,4);s=torch.zeros(2,6);x=torch.randn(2,4,40);mask=torch.tensor([[1,1,0,0],[1,1,1,1]],dtype=torch.bool);kind=torch.tensor([[0,1,0,0],[0,0,1,1]])
            self.assertTrue(torch.equal(n(s,x,mask,kind),torch.zeros(2,3)))
    def test_padding_invariance(self):
        n=l.Head('attention',16,4);torch.nn.init.normal_(n.head[-1].weight)
        s=torch.zeros(1,6);x=torch.randn(1,3,40);mask=torch.tensor([[1,1,0]],dtype=torch.bool);kind=torch.tensor([[0,1,0]])
        y=n(s,x,mask,kind);x[:,2]=999;self.assertTrue(torch.allclose(y,n(s,x,mask,kind)))
    def test_stats_train_only(self):
        d=dict(s=np.array([[0]*6,[2]*6,[100]*6],dtype=np.float32),x=np.ones((3,1,40),dtype=np.float32),mask=np.ones((3,1),dtype=bool))
        self.assertEqual(l.statistics(d,np.array([0,1]))['smean'].tolist(),[1]*6)
    def test_record_binding(self):
        r='Hospital Admission Start: 2000-01-01\nHospital Admission End: 2000-01-02\n1. Date: 2000-01-01, Time: 12:00, Note Category: Test, Note ID: 123, Raw characters: [0,4) | Text: abc\n2. Date: 2000-01-01, Time: 12:00, Note Category: Test, Note ID: 123, Raw characters: [5,9) | Text: def'
        a,p=pieces(r);self.assertEqual(len(p),2);self.assertEqual(p[0]['body'],'abc');self.assertNotIn('123',p[0]['header']);self.assertEqual(p[0]['note'],p[1]['note'])
if __name__=='__main__':unittest.main()
