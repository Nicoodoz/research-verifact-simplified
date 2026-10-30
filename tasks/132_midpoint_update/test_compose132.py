import unittest
import torch
from compose132 import combine


class EffectiveUpdateTest(unittest.TestCase):
    def test_exact_endpoints_and_midpoint(self):
        a0=torch.tensor([[1.,2.,3.],[2.,-1.,1.]])
        a1=torch.tensor([[4.,-1.,2.],[-2.,3.,1.]])
        b0=torch.tensor([[2.,1.],[-1.,3.]])
        b1=torch.tensor([[1.,-2.],[4.,1.]])
        for alpha in (0.,.5,1.):
            a,b=combine(a0,b0,2.,a1,b1,3.,alpha)
            torch.testing.assert_close(b@a,(1-alpha)*2.*(b0@a0)+alpha*3.*(b1@a1),rtol=0,atol=0)


if __name__=='__main__':unittest.main()
