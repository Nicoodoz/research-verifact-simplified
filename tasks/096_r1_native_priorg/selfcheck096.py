"""Offline preparation audit by executor; not an independent audit."""
import json,sys,subprocess,socket
from collections import Counter
from unittest.mock import patch
import common096 as c
from calibration096 import decode
def main():
    checks=[]
    def ok(name,detail):checks.append(dict(check=name,pass_check=True,detail=detail))
    base=c.lines(c.ROOT/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl');by={r['id']:r for r in base};recipe=c.read(c.OUT/'calibration_recipe.json');cal=c.lines(c.OUT/'calibration_manifest.jsonl');calids={r['id'] for r in cal};calp=set(recipe['patients'])
    assert len(cal)==143 and len(calp)==16 and calids<=set(by)
    counts=dict(Counter(r['GT'] for r in base if r['sid'] in calp));assert counts==recipe['reference_counts']
    assert dict(Counter(r['GT'] for r in cal))==recipe['calibration_counts']
    ok('exact_calibration_and_reference_prior',dict(N=143,patients=16,reference_N=sum(counts.values()),reference_counts=counts,training_counts=recipe['calibration_counts']))
    old=recipe['old_theta'];new=recipe['reproduced_model']['theta'][0];core=[r for r in base if r['B_core_valid']];dif=0
    for r in core:
        s=r['B']['parsed']['scores'];d=decode(s,old,counts,recipe['calibration_counts']);assert d==r['predictions']['B_PriorG'];dif+=d!=decode(s,new,counts,recipe['calibration_counts'])
    assert dif==0;ok('V4_recipe_reproduction',dict(old_theta=old,refit_theta=new,absolute_parameter_difference=abs(old-new),labels_unchanged_on143=True,labels_unchanged_on8997=True,old_literal_preserved=True))
    old085={r['id'] for r in c.lines(c.ROOT/'.local_models/085_valdemardi_private/jobs.jsonl')};ledger=c.lines(c.OUT/'candidate_ledger.jsonl');main=c.lines(c.OUT/'main_panel.jsonl');stress=c.lines(c.OUT/'stress_panel.jsonl');mids={r['id'] for r in main};sids={r['id'] for r in stress}
    assert len(ledger)==9065 and len(mids)==800 and len(sids)==200 and not mids&sids and not (mids|sids)&old085
    assert all(r['sid'] not in calp for r in main+stress) and sum(not r['B_core_valid'] for r in main)==8
    from prepare096 import strata_sample
    replay,q=strata_sample([r for r in ledger if r['eligible']],800,'096/main/v1/');assert replay==main
    ok('sampling_replay_no_core_or_correctness_filter',dict(eligible=7507,main=800,stress=200,main_noncore=8,main_patients=len({r['sid'] for r in main}),mutually_exclusive=True,near_self_weighted=True))
    jobs=c.lines(c.PRIVATE/'jobs.jsonl');manifest={r['request_id']:r for r in c.lines(c.OUT/'request_manifest.jsonl')};freeze=c.read(c.OUT/'data_freeze.json');assert c.sha(c.PRIVATE/'jobs.jsonl')==freeze['jobs_sha256'];assert len(jobs)==len(manifest)==1143
    template=c.read(c.PRIVATE/'template.json');pool={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')};calmap={r['id']:r for r in cal}
    for j in jobs:
        assert c.digest(j['body'])==j['body_sha256']==manifest[j['request_id']]['body_sha256'];b=j['body'];assert b['model']==c.MODEL and (b['temperature'],b['top_p'],b['max_tokens'],b['stream'])==(0,1,8192,False)
        assert b['messages'][0]==template['messages'][0] and not set(b)&{'enable_thinking','reasoning_effort'}
        p=json.loads(b['messages'][1]['content']);assert set(p)=={'proposition','reference'}
        if j['stage']=='calibration':
            cm=calmap[j['id']];assert c.key('',p['proposition'])==cm['claim_sha256'] and c.key('',p['reference'])==cm['reference_sha256']
        else:assert p['proposition']==pool[j['id']]['text'] and p['reference']==pool[j['id']]['reference']
    ok('all1143_requests_exact_bound_GT_excluded',dict(calibration=143,main=800,stress=200,system_matches085=True,no_V4_only_parameters=True))
    lengths=c.lines(c.OUT/'local_token_lengths.jsonl');assert len(lengths)==1144 and all(r['total_reserved_context']<=20000 for r in lengths)
    tp=c.read(c.OUT/'technical_preflight_plan.json');assert len(tp['calibration_request_ids'])==3 and set(tp['calibration_request_ids'])<={j['request_id'] for j in jobs if j['stage']=='calibration'}
    ok('local_tokenizer_and_technical_reuse',dict(max_input=max(r['input_tokens'] for r in lengths),max_total=max(r['total_reserved_context'] for r in lengths),remote_not_verified=True,technical_calibration_successes_reused=True))
    import runner096 as run
    try:run.validate_runtime(c.TASK/'runtime.template.json');raise AssertionError('template unexpectedly authorized')
    except AssertionError as e:assert 'WAIT_FOR_USER_SERVICE_READY' in str(e)
    assert not list((c.PRIVATE/'attempts').glob('*/*/request.json')) and not (c.PRIVATE/'service_probes').exists() and not (c.PRIVATE/'api_budget.sqlite').exists()
    ok('no_network_no_spending',dict(new_R1_requests=0,R1_endpoint_probes=0,new_metered_API_requests=0,metered_API_cost_cny=0,GPU_bill_unknown=True,budgets_not_confirmed=True))
    assert not subprocess.check_output(['git','diff','--name-only','--','.gitignore','src','tasks/051_thinking_mode_validation','tasks/052_first_tier_validation','tasks/053_thinking_prior_validation','tasks/085_r1_70b_valdemardi','outputs/095_anchored_minimal_contrast'],cwd=c.ROOT,text=True).strip()
    assert subprocess.run(['git','check-ignore','-q',str((c.PRIVATE/'jobs.jsonl').relative_to(c.ROOT))],cwd=c.ROOT).returncode==0
    ok('historical_and_private_boundaries','No historical051–095/default/.gitignore changes; clinical requests private; stopped old096 not restored.')
    c.put(c.OUT/'offline_selfcheck.json',dict(status='PASS',kind='executor_offline_selfcheck_not_independent_audit',checks=checks,scope='Preparation and mocked safety behavior only; no remote server or medical performance validated.'))
    print('OFFLINE_SELF_CHECK_PASS',len(checks))
if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('offline self-check forbids network')):main()
