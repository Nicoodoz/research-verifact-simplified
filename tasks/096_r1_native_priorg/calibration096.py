"""Original052 objective and053 tie-break. CPU-only, no evaluation labels."""
import sys,math
from collections import Counter
import numpy as np
import common096 as c
sys.path.insert(0,str(c.ROOT/'tasks/052_first_tier_validation'))
from fit_calibration052 import fit,z_from_scores,obj_grad_hess
sys.path.insert(0,str(c.ROOT/'tasks/053_thinking_prior_validation'))
from common053 import decode_logits,log_scores,prior_adjust

def decode(scores,theta=0.,reference_counts=None,calibration_counts=None):
    v=log_scores(scores);v['Supported']+=theta
    if reference_counts is not None:v=prior_adjust(v,reference_counts,calibration_counts)
    return decode_logits(v)

def fit_g(rr):
    z=z_from_scores([r['scores'] for r in rr]);y=np.array([c.LABELS.index(r['GT']) for r in rr],int)
    result=fit(z,y,'G');assert result['success'] and result['objective_monotone']
    # Separate scalar SciPy optimization checks the frozen objective, not a new
    # recipe or parameter search. Its theta never replaces the052 solver output.
    from scipy.optimize import minimize_scalar
    check=minimize_scalar(lambda t:obj_grad_hess([t],z,y,'G')[0],bounds=(-6,6),method='bounded',options={'xatol':1e-12})
    assert check.success and abs(check.x-result['theta'][0])<1e-5
    return result,dict(theta=float(check.x),objective=float(check.fun),same_objective_only=True)

def adapt():
    # This function reads calibration supervision ONLY; it must run before any
    # evaluator is allowed to join held evaluation GT.
    import runner096 as run
    profile=c.read(c.OUT/'live_parser_profile.json');from parse_r1 import ParserProfile,parse
    pp=ParserProfile.from_json(profile);jobs=[j for j in c.lines(c.PRIVATE/'jobs.jsonl') if j['stage']=='calibration'];truth={r['id']:r for r in c.lines(c.PRIVATE/'calibration_supervision.jsonl')};r1=[];invalid=[]
    for j in jobs:
        s=run.success(j)
        if s is None:raise RuntimeError('Calibration calls incomplete')
        p=parse((s/'response.raw').read_bytes(),pp)
        if p['valid'] and p['label_scores'] is not None:r1.append(dict(id=j['id'],sid=j['sid'],GT=truth[j['id']]['GT'],scores=p['label_scores']))
        else:invalid.append(j['id'])
    counts=dict(Counter(r['GT'] for r in r1));assert set(counts)==set(c.LABELS),'Calibration intersection lost a class; no evaluation-label replacement'
    ids={r['id'] for r in r1};v4=[truth[i] for i in sorted(ids)];rmodel,rcheck=fit_g(r1);vmodel,vcheck=fit_g(v4)
    frozen=c.read(c.OUT/'calibration_recipe.json');ref=frozen['reference_counts'];models=dict(R1_adapted=rmodel,V4_matched_supervision=vmodel)
    data=dict(status='FROZEN_BEFORE_EVALUATION_GT_JOIN',calibration_ids=sorted(ids),invalid_ids=invalid,counts=counts,reference_counts=ref,models=models,optimizer_checks=dict(R1=rcheck,V4=vcheck),old_V4_theta=frozen['old_theta'],old_calibration_counts=frozen['calibration_counts'],evaluation_GT_read=False,recipe_sha256=c.sha(c.OUT/'calibration_recipe.json'),parser_sha256=c.sha(c.OUT/'live_parser_profile.json'))
    c.put(c.OUT/'adapted_parameters.json',data);print('ADAPTED_PARAMETERS_FROZEN',len(ids),'invalid',len(invalid))
if __name__=='__main__':adapt()
