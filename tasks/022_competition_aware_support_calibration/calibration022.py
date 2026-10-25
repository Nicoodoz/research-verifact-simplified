"""Fixed low-capacity calibrators and analytic convex NLL fitting."""
import numpy as np
from scipy.special import logsumexp,softmax
from scipy.optimize import minimize
import common022 as c

def scores_to_z(scores):
    for s in scores:
        c.require(set(s)==set(c.LABELS) and all(type(v) is int and 0<=v<=100 for v in s.values()) and sum(s.values())==100,'Invalid class scores')
    return np.log(np.maximum([[s[k]/100 for k in c.LABELS] for s in scores],1e-6))

def labels(logits):
    order=np.array([1,2,0]);return order[np.argmax(logits[:,order],axis=1)]

def features(z,kind):
    n=len(z);size={'G':1,'C':2,'M':2,'V':5,'T':1}[kind]
    x=np.zeros((n,3,size));base=z.copy();center=np.zeros(size);reg=np.zeros((size,size));bounds=[(-6,6)]*size
    if kind=='G':x[:,0,0]=1;reg[0,0]=.01
    elif kind=='C':
        r=softmax(z[:,1:],axis=1)[:,0];x[:,0,0]=r;x[:,0,1]=1-r
        reg=np.array([[.015,-.01],[-.01,.015]])
    elif kind=='M':x[:,0,0]=1;x[:,1,1]=1;reg=np.eye(2)*.005
    elif kind=='V':
        base=np.zeros_like(z)
        for k in range(3):x[:,k,k]=z[:,k]
        x[:,0,3]=1;x[:,1,4]=1;center[:3]=1
        reg=np.diag([.01/3]*3+[.005]*2);bounds=[(.05,5)]*3+[(-6,6)]*2
    else:
        base=np.zeros_like(z);x[:,:,0]=z;center[:]=1;reg[0,0]=.01;bounds=[(.05,5)]
    return base,x,center,reg,bounds

def transform(z,kind,theta=None):
    if kind=='U0':return z.copy()
    if kind=='U2':
        out=z.copy();out[:,0]+=2;return out
    base,x,_,_,_=features(z,kind);return base+np.einsum('nkp,p->nk',x,np.asarray(theta))

def objective(theta,base,x,y,center,reg):
    v=base+np.einsum('nkp,p->nk',x,theta);loss=np.mean(logsumexp(v,axis=1)-v[np.arange(len(y)),y])
    d=softmax(v,axis=1);d[np.arange(len(y)),y]-=1
    delta=theta-center
    return loss+delta@reg@delta,np.einsum('nk,nkp->p',d,x)/len(y)+2*reg@delta

def fit(z,y,kind):
    base,x,center,reg,bounds=features(z,kind)
    result=minimize(objective,center.copy(),args=(base,x,y,center,reg),method='L-BFGS-B',jac=True,bounds=bounds,options={'maxiter':2000,'ftol':1e-12,'gtol':1e-8})
    c.require(result.success,'Optimization failed: '+kind+' '+str(result.message))
    return dict(theta=result.x.tolist(),objective=float(result.fun),gradient_max=float(np.max(np.abs(result.jac))),iterations=int(result.nit),success=bool(result.success),message=str(result.message),boundary_hit=[i for i,(v,(lo,hi)) in enumerate(zip(result.x,bounds)) if min(v-lo,hi-v)<1e-7])

def split_indices(rows,fold):
    train=[i for i,r in enumerate(rows) if r['repeat']==0 and r['fold']!=fold]
    test=[i for i,r in enumerate(rows) if r['fold']==fold]
    c.require(not ({rows[i]['subject_id'] for i in train}&{rows[i]['subject_id'] for i in test}),'Patient leakage')
    c.require(len(train)==len({rows[i]['proposition_id'] for i in train}),'Duplicate training claim/repeat weight')
    return train,test
