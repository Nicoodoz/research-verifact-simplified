"""Full exact global-lambda states and matched-risk upper envelopes."""
import numpy as np
import common025 as c
def global_states(rows):
    z=np.array([c.logs(r['scores']) for r in rows]);times=sorted({0.,.5,1.,1.5,2.,3.,4.,16.,*[t for zz in z if (t:=c.first_switch(zz)) is not None]})
    preds=np.array([c.decode(z,t) for t in times]);c.require(np.all(preds[-1]==0),'Global frontier incomplete')
    return times,preds
def pareto(risks,rescues):
    byx={}
    for x,y in zip(risks,rescues):byx[float(x)]=max(float(y),byx.get(float(x),-1))
    points=[];best=-1
    for x,y in sorted(byx.items()):
        if y>best:points.append((x,y));best=y
    return points
def hull(points):
    out=[]
    for x,y in points:
        while len(out)>1:
            a,b=out[-2],out[-1]
            if (b[1]-a[1])*(x-b[0])<=(y-b[1])*(b[0]-a[0])+1e-12:out.pop()
            else:break
        out.append((x,y))
    return out
def matched(risks,rescues,risk,rescue):
    pts=pareto(risks,rescues);hh=hull(pts);x,y=np.array(hh).T
    deterministic=max((r for f,r in pts if f<=risk+1e-10),default=0.)
    envelope=float(np.interp(risk,x,y))
    det_min=min((f for f,r in pts if r>=rescue-1e-10),default=None)
    mix_min=float(np.interp(rescue,y,x)) if rescue<=max(y)+1e-10 else None
    return dict(global_R_at_risk=deterministic,global_mixture_R_at_risk=envelope,R_gain_vs_global=rescue-deterministic,R_gain_vs_mixture=rescue-envelope,global_min_risk_at_R=det_min,global_mixture_min_risk_at_R=mix_min,risk_saved_vs_global=None if det_min is None else det_min-risk,risk_saved_vs_mixture=None if mix_min is None else mix_min-risk)
def counts(rows,predictions,weights=None):
    pp=np.atleast_2d(predictions);gt=np.array([r['human_gt']=='Supported' for r in rows]);u0=np.array([r['u0'] for r in rows]);w=np.ones(len(rows)) if weights is None else np.asarray(weights,dtype=float)
    changed=(pp==0)&(u0[None,:]!=0)
    return changed@(w*gt),changed@(w*(~gt))
