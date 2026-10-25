"""Calibration-only numerical diagnostic; no evaluation GT."""
import numpy as np
import common096 as c
import marlin096 as m
from calibration096 import fit,z_from_scores,obj_grad_hess
def main():
    m.activate();gt={x['id']:x for x in c.lines(c.PRIVATE/'calibration_supervision.jsonl')};rr=[]
    for j in m.r.jobs():
        if j['stage']!='calibration':continue
        p=m.r.parsed(j)
        if p['valid'] and p['label_scores'] is not None:rr.append(dict(id=j['id'],GT=gt[j['id']]['GT'],scores=p['label_scores']))
    z=z_from_scores([x['scores'] for x in rr]);y=np.array([c.LABELS.index(x['GT']) for x in rr]);a=fit(z,y,'G')
    from scipy.optimize import minimize_scalar,brentq
    b=minimize_scalar(lambda v:obj_grad_hess([v],z,y,'G')[0],bounds=(-6,6),method='bounded',options={'xatol':1e-12})
    lo=obj_grad_hess([-6],z,y,'G')[1][0];hi=obj_grad_hess([6],z,y,'G')[1][0]
    theta=float(brentq(lambda v:obj_grad_hess([v],z,y,'G')[1][0],-6,6,xtol=1e-14)) if lo<0<hi else -6. if lo>=0 else 6.
    out=dict(N=len(rr),original052_solver=a,scipy_theta=float(b.x),scipy_loss=float(b.fun),scipy_success=bool(b.success),derivative_root_theta=theta,root_loss=obj_grad_hess([theta],z,y,'G')[0],boundary_gradients=[float(lo),float(hi)],evaluation_GT_read=False)
    c.put(m.O/'calibration_numerical_diagnostic.json',out);print(out)
if __name__=='__main__':main()
