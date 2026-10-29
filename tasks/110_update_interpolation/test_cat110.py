"""Tiny exact algebra checks, including unequal source scales and endpoints."""
import numpy as np
def main():
    rng=np.random.RandomState(110);a0=rng.randn(3,7);b0=rng.randn(5,3);a1=rng.randn(3,7);b1=rng.randn(5,3);s0,s1=2.,.7
    errors={}
    for alpha in [0.,.25,.5,1.]:
        a=np.concatenate([(1-alpha)*s0*a0,alpha*s1*a1],axis=0);b=np.concatenate([b0,b1],axis=1)
        expected=(1-alpha)*s0*(b0@a0)+alpha*s1*(b1@a1);error=float(np.max(np.abs(b@a-expected)))
        assert error<1e-12;errors[str(alpha)]=error
    alpha=.25;wrong=((1-alpha)*b0+alpha*b1)@((1-alpha)*s0*a0+alpha*s1*a1)
    assert not np.allclose(wrong,(1-alpha)*s0*(b0@a0)+alpha*s1*(b1@a1))
    print({'exact_cat_max_errors':errors,'factorwise_average_rejected':True,'GPU_used':False})
if __name__=='__main__':main()
