"""Fit and freeze two G models on common calibration IDs, without evaluation GT."""
import sys,math
from collections import Counter
import numpy as np
import common079 as c
import run079
sys.path.insert(0,str(c.ROOT/'tasks/052_first_tier_validation'))
import fit_calibration052 as fit052

def main():
    run079.verify();attempts,answers=run079.state()
    assert len(answers)==len(c.lines(c.OUT/'main_jobs.jsonl'))
    f4={x['job']['id']:x for x in answers.values()}
    for z in c.lines(c.OUT/'reused_F4.jsonl'):
        assert z['job']['id'] not in f4;f4[z['job']['id']]=z
    cases=c.lines(c.OUT/'calibration_cases.jsonl');assert len(f4)==len(cases)==114
    valid=lambda p:p['status'] in c.c53.VALID and p.get('scores') is not None
    common=[x for x in cases if valid(x['B']['parsed']) and valid(f4[x['id']]['parsed'])]
    counts=dict(Counter(x['GT'] for x in common));assert set(counts)==set(c.c53.LABELS)
    excluded=[dict(id=x['id'],sid=x['sid'],GT=x['GT'],B_status=x['B']['parsed']['status'],F4_status=f4[x['id']]['parsed']['status']) for x in cases if x not in common]
    ref=c.read(c.OUT/'old_postprocessing.json')['reference_prior_counts']
    y=np.array([c.c53.LABELS.index(x['GT']) for x in common])
    models={}
    for arm in ['B','F4']:
        scores=[x['B']['parsed']['scores'] if arm=='B' else f4[x['id']]['parsed']['scores'] for x in common]
        z=fit052.z_from_scores(scores);fd=fit052.finite_diff(z,y,'G');m=fit052.fit(z,y,'G')
        assert fd<1e-6 and m['success'] and m['objective_monotone'] and not m['boundary_hit']
        factors={k:(ref[k]/sum(ref.values()))/(counts[k]/sum(counts.values()))*math.exp(m['theta'][0] if k=='Supported' else 0) for k in c.c53.LABELS}
        models[arm]=dict(fit=m,finite_difference_error=fd,effective_PriorG_multipliers=factors)
    records=[dict(id=x['id'],sid=x['sid'],GT=x['GT'],B=x['B'],F4=f4[x['id']]) for x in cases]
    c.jl(c.OUT/'calibration_predictions.jsonl',records)
    c.put(c.OUT/'fitted_models.json',dict(status='FROZEN_BEFORE_079_EVALUATION',created_utc=c.now(),
        common_ids=[x['id'] for x in common],common_patients=sorted({x['sid'] for x in common}),common_n=len(common),calibration_counts=counts,
        reference_prior_counts=ref,excluded=excluded,models=models,new_fits=2,evaluation_GT_used=False,
        fit_code_sha256=c.sha(c.TASK/'fit079.py'),fitter_sha256=c.sha(c.ROOT/'tasks/052_first_tier_validation/fit_calibration052.py'),
        calibration_predictions_sha256=c.sha(c.OUT/'calibration_predictions.jsonl')))
    print(c.canon(dict(common_n=len(common),counts=counts,excluded=excluded,models=models)),flush=True)

if __name__=='__main__':main()
