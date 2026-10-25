"""Accept verified bound optima from the unchanged052 solver; no new recipe."""
import numpy as np
import common096 as c
from calibration096 import fit,z_from_scores,obj_grad_hess
def fit_g(rows):
    z=z_from_scores([r['scores'] for r in rows]);y=np.array([c.LABELS.index(r['GT']) for r in rows],int)
    result=fit(z,y,'G');theta=float(result['theta'][0]);loss,g,h=obj_grad_hess([theta],z,y,'G');gradient=float(g[0])
    # Original052 uses unconstrained |gradient| even when clip reaches a bound.
    # At lower bound, a nonnegative derivative is the constrained KKT condition.
    projected=abs(min(gradient,0.)) if theta<=-6+1e-12 else abs(max(gradient,0.)) if theta>=6-1e-12 else abs(gradient)
    assert -6<=theta<=6 and result['objective_monotone'] and projected<1e-7 and h[0,0]>0
    from scipy.optimize import minimize_scalar
    check=minimize_scalar(lambda t:obj_grad_hess([t],z,y,'G')[0],bounds=(-6,6),method='bounded',options={'xatol':1e-12})
    assert check.success and abs(float(check.x)-theta)<1e-5 and abs(float(check.fun)-loss)<1e-6
    result.update(constrained_optimum_verified=True,projected_gradient=projected,signed_gradient=gradient,original052_success_flag_preserved=True,theta_changed_from_original052_solver=False,convergence_note='Original success flag is unconstrained; bound solution accepted only by KKT, strict convexity and same-objective independent check.')
    return result,dict(theta=float(check.x),objective=float(check.fun),same_objective_only=True,not_used_to_replace_theta=True)
