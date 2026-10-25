"""Low-dimensional fitting; all callers must pass training patients only."""
import numpy as np
from scipy.special import logsumexp, softmax
from scipy.optimize import brentq
import common as c

def logprob(v):return v-logsumexp(v,axis=1,keepdims=True)
def nll(v,y):return float(np.mean(logsumexp(v,axis=1)-v[np.arange(len(y)),y]))
def temperature(z,y,lam):
    v=z.copy();v[:,0]+=lam
    def derivative(beta):return float(np.mean(np.sum(softmax(beta*v,axis=1)*v,axis=1)-v[np.arange(len(y)),y]))
    lo,hi=.05,5.;dl,dh=derivative(lo),derivative(hi)
    beta=lo if dl>=0 else hi if dh<=0 else brentq(derivative,lo,hi,xtol=1e-12)
    assert nll(beta*v,y)<=nll(v,y)+1e-10
    return dict(kind='boundary_temperature',lam=float(lam),beta=float(beta),T=float(1/beta),
      train_nll=nll(beta*v,y),boundary=bool(beta in (lo,hi)),gradient=derivative(beta))

def joint_objective(theta,z,y):
    a,b=theta
    v=a*z.copy();v[:,0]+=b
    d=softmax(v,axis=1);d[np.arange(len(y)),y]-=1
    grad_a=np.mean(np.sum(d*z,axis=1))
    grad_b=np.mean(d[:,0])
    return nll(v,y),np.array([grad_a,grad_b])

def _bounded_root(grad,lo,hi):
    glo,ghi=float(grad(lo)),float(grad(hi))
    if glo>=0:return float(lo)
    if ghi<=0:return float(hi)
    return float(brentq(grad,lo,hi,xtol=1e-12))

def joint(z,y):
    solutions=[]
    for lam0 in (0.,1.,2.,3.,4.):
        a=float(temperature(z,y,lam0)['beta']);b=a*lam0
        for iteration in range(200):
            old=np.array([a,b])
            def gb(x):
                v=a*z.copy();v[:,0]+=x
                d=softmax(v,axis=1);d[np.arange(len(y)),y]-=1
                return float(np.mean(d[:,0]))
            b=_bounded_root(gb,0.,4*a)
            alo=max(.05,b/4)
            def ga(x):
                v=x*z.copy();v[:,0]+=b
                d=softmax(v,axis=1);d[np.arange(len(y)),y]-=1
                return float(np.mean(np.sum(d*z,axis=1)))
            a=_bounded_root(ga,alo,5.)
            if np.max(np.abs(np.array([a,b])-old))<1e-10:break
        value=nll(a*z+np.c_[np.full(len(z),b),np.zeros((len(z),2))],y)
        solutions.append((value,a,b,iteration+1))
    value,a,b,iterations=min(solutions,key=lambda t:(t[0],t[2]/t[1],t[1]))
    lam=b/a
    anchor=temperature(z,y,2.)
    if value>anchor['train_nll']+1e-9:
        a=anchor['beta'];lam=2.;b=2*a;value=anchor['train_nll'];iterations=0
    return dict(kind='joint',a=float(a),b=float(b),lam=float(lam),beta=float(a),T=float(1/a),
      train_nll=float(value),iterations=int(iterations),starts=5,
      boundary=bool(min(a-.05,5-a,b,4*a-b)<1e-7))

def states(z,y,sids):
    cuts=np.unique(np.r_[0.,4.,(z[:,1:].max(1)-z[:,0])]);cuts=cuts[(cuts>=0)&(cuts<=4)]
    values=np.r_[0.,2.,4.,(cuts[:-1]+cuts[1:])/2]
    bylabels={}
    for lam in sorted(set(values),key=lambda v:(v!=2.,abs(v-2.),v)):
        v=z.copy();v[:,0]+=lam;p=c.decode(v)
        bylabels.setdefault(p.tobytes(),(float(lam),p))
    ordered=sorted(bylabels.values(),key=lambda a:a[0]);patients=sorted(set(sids))
    gi=np.array([patients.index(s) for s in sids]);conf=[];table=[]
    for lam,p in ordered:
        counts=np.zeros((len(patients),3,3),dtype=int);np.add.at(counts,(gi,y,p),1);conf.append(counts)
        tot=counts.sum(0);pa,ac1,mcc=c.metrics_from_confusions(tot)
        table.append(dict(lam=lam,correct=int(np.trace(tot)),PA=float(pa),MCC=float(mcc),
          false_S=int(tot[1:,0].sum()),n=int(tot.sum())))
    conf=np.stack(conf);anchor=next(i for i,r in enumerate(table) if r['lam']==2.)
    draws=np.stack([np.bincount(np.random.RandomState(35035+i).choice(len(patients),len(patients)),minlength=len(patients)) for i in range(256)])
    bc=np.einsum('bg,kgrs->kbrs',draws,conf,optimize=True)
    bm=c.metrics_from_confusions(bc)[:,:,2];q=np.quantile(bm-bm[anchor],.1,axis=1)
    for i,r in enumerate(table):
        r['q10_delta_MCC']=float(q[i]);r['eligible']=bool(r['correct']>=table[anchor]['correct'] and r['false_S']<=table[anchor]['false_S'])
    valid=[r for r in table if r['eligible']]
    common=lambda r:(-r['MCC'],r['false_S'],abs(r['lam']-2),r['lam'])
    task=min(valid,key=common)
    robust=min(valid,key=lambda r:(-r['q10_delta_MCC'],*common(r)))
    return task['lam'],robust['lam'],table

def fit_all(rows):
    z,y=c.arrays(rows);task,robust,table=states(z,y,[r['sid'] for r in rows])
    mcc_best=min(table,key=lambda r:(-r['MCC'],r['false_S'],abs(r['lam']-2),r['lam']))['lam']
    models={'U0':dict(kind='boundary_temperature',lam=0.,beta=1.,T=1.),
      'U2':dict(kind='boundary_temperature',lam=2.,beta=1.,T=1.),
      'U2_T':temperature(z,y,2.),'Joint_NLL':joint(z,y),
      'Task_T':temperature(z,y,task),'Robust_T':temperature(z,y,robust),
      'MCC_T':temperature(z,y,mcc_best)}
    return models,table

def infer(rows,models):
    z,_=c.arrays(rows);out={}
    for name,m in models.items():
        if m['kind']=='joint':
            v=z*m['a'];v=v.copy();v[:,0]+=m['b'];p=c.decode(v)
        else:
            raw=z.copy();raw[:,0]+=m['lam'];p=c.decode(raw);v=raw*m['beta']
            assert np.array_equal(p,c.decode(v)), 'Temperature changed labels'
        lp=logprob(v);assert np.array_equal(p,c.decode(lp)), 'Probability/label mismatch'
        out[name]=(p,lp)
    assert np.array_equal(out['U2'][0],out['U2_T'][0])
    return out
