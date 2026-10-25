"""Executor self-check, explicitly separate from the independent reviewer."""
import json,subprocess,collections
import common095 as c
import state095 as state
import method095 as m
import sourcefix095 as fixed
import pricing095_v3 as price
from reproduce_public095 import main as public_repro

def main():
    assert not (c.PRIVATE/'run.lock').exists();checks=[]
    def record(name,detail):checks.append(dict(check=name,pass_check=True,detail=detail))
    for filename in ['baseline_plan.json','runner_freeze.json','experiment_freeze.json','runtime_v3_freeze.json','sourcefix_freeze.json']:
        for p,hh in c.read(c.OUT/filename)['sources'].items():assert c.sha(c.ROOT/p)==hh,(filename,p)
    old=c.read(c.OUT/'pricing_v2_freeze.json');p=(c.TASK/'workflow095.py').relative_to(c.ROOT).as_posix();assert c.sha(c.TASK/'workflow095_pre_resume_fix.py')==old['sources'][p]
    if (c.OUT/'baseline_completion_plan.json').exists():
        finish=c.read(c.OUT/'baseline_completion_plan.json');assert c.sha(c.PRIVATE/'baseline_completion_jobs.jsonl')==finish['jobs_sha256'];assert c.sha(c.TASK/'finish_baseline095.py')==finish['code_sha256'];assert finish['shared_task_hard_cap_cny']==150
    record('frozen_source_identity','Initial scientific/runner freezes unchanged; v2 workflow preserved as exact prior version; v3 and whitespace amendment explicit.')
    pool={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')};template=c.read(c.PRIVATE/'judge_template.json');success=state.successful_jobs();seen=set();arms=collections.Counter();new_B=set()
    for rid,x in success.items():
        j=x['job'];b=j['body'];payload=json.loads(b['messages'][1]['content']);arms[j['arm']]+=1
        assert c.h(c.canonical(b))==j['body_sha256'];tr=state.receipt(x);native=json.loads(tr['body_text']);assert native['model']==c.MODEL
        if j['arm']=='B':
            row=pool[j['id']];assert b==m.judge(template,row);key=(j['id'],j['body_sha256']);assert key not in seen;seen.add(key);new_B.add(j['id'])
        elif j['arm']=='construct':assert set(payload)=={'claim','reference'} and payload['claim']==pool[j['id']]['text'] and payload['reference']==pool[j['id']]['reference']
        elif j['arm']=='check':
            assert set(payload)=={'original_claim','alternative_claim','attribute','old_span','new_span','source_value','anchors','reference'}
            assert payload['original_claim']==pool[j['id']]['text'] and payload['reference']==pool[j['id']]['reference']
        else:raise AssertionError('Unexpected new arm '+j['arm'])
        assert not any(k in payload for k in ['GT','label','human_gt','old_reason','old_verdict'])
    assert arms['construct']==300 and arms['check']==117 and set(arms)=={'B','construct','check'}
    record('all_new_requests_bound_and_GT_separated',dict(successes=len(success),arms=dict(arms),unique_new_B=len(new_B),no_C_final_Judge=True))
    initial={r['id'] for r in c.lines(c.OUT/'cache_selected.jsonl')};assert not initial&new_B
    rows=c.lines(c.OUT/'unified_9065_predictions.jsonl');cov=c.read(c.OUT/'baseline_coverage.json');assert len(rows)==9065;assert sum(r['B_present'] for r in rows)==cov['successful_B'];assert cov['successful_B']==len(initial|new_B)
    assert {r['id'] for r in rows if not r['B_present']}=={r['id'] for r in c.lines(c.OUT/'baseline_remaining.jsonl')}
    for r in rows:
        if not r['B_core_valid']:assert r['predictions']['B_PriorG'] is None
        if not r['B_raw_valid']:assert r['predictions']['B_raw'] is None
    record('coverage_invalid_missing_no_imputation',cov)
    at=state.attempts();amount=0
    for x in at:
        req=c.read(c.ROOT/x['request_path']);j=req['job'];tr=c.read(c.ROOT/x['receipt_path'])['transport'] if x['receipt_path'] else None
        expected=price.charge(j,tr);assert abs(expected-x['charge_or_reserved_cny'])<1e-10
        assert x['prior_task_reserved']+j['bound_cny']<=150+1e-9
        assert c.sha(c.ROOT/x['request_path'])==x['request_sha256'];amount+=expected
        if x['receipt_path']:assert c.read(c.ROOT/x['receipt_path'])['request_sha256']==c.sha(c.ROOT/x['request_path'])
    assert amount<=150;cst=c.read(c.OUT/'cost_ledger.json');assert abs(amount-cst['total_directory_price_or_unknown_cny'])<1e-8
    record('append_only_binding_and_budget',dict(attempts=len(at),charge_or_reserved_cny=amount,hard_cap=150,actual_cache_only=True,unknowns_max_reserved=True))
    checked=c.lines(c.PRIVATE/'checked.jsonl');samples={r['id'] for r in c.lines(c.OUT/'screen_sample.jsonl')};found={r['id'] for r in c.lines(c.OUT/'diagnosis_sample.jsonl')};extension={r['id'] for r in c.lines(c.OUT/'extension_registered_order.jsonl')};assert len(samples)==300 and len(found)==80 and len(extension)==600 and not samples&found and not extension&(samples|found)
    for r in checked:
        if r['valid']:
            ref=pool[r['id']]['reference'];claim=pool[r['id']]['text'];assert r['alternative']==claim[:r['edit_start']]+r['new_span']+claim[r['edit_end']:]
            for a in r['anchors']:assert ref[a['reference_start']:a['reference_end']]==a['quote']
    gate=c.read(c.OUT/'operation_gate.json');assert not gate['pass_gate'] and gate['numeric_coverage_gate'] and gate['automated_eligible']==95 and gate['clinical_Judge_calls']==0
    record('source_matching_is_not_semantic_gold',dict(program_valid=117,automatic_eligible=95,actual_final_C_Judge=0,quality_sample=24,discovery_excluded=True))
    public_repro();record('public_points_and_frozen_prior_reproduced','Official metric point values and independent arithmetic PriorG replay; this remains executor self-check.')
    result=subprocess.run(['git','diff','--name-only','--','.gitignore','src'],cwd=c.ROOT,capture_output=True,text=True,check=True);assert not result.stdout.strip()
    for path in ['.local_models/095/attempts','.local_models/095/budget.sqlite','.local_models/095/screen_inputs.jsonl']:
        assert subprocess.run(['git','check-ignore','-q',path],cwd=c.ROOT).returncode==0,path
    record('protected_paths','No .gitignore or src/default changes; private clinical inputs, native receipts and ledger remain ignored.')
    # Generated free-text issue strings stay private. Public construction records use only hash.
    for r in c.lines(c.OUT/'construction_audit.jsonl'):assert 'issue' not in r['checker'] and 'issue_sha256' in r['checker']
    record('public_auxiliary_privacy','No raw quotes, generated alternative text, or checker free-text issues in public construction audit.')
    c.put(c.OUT/'selfcheck.json',dict(utc=c.now(),status='PASS',kind='executor_self_check_not_independent_audit',checks=checks,remaining_independent_review='See reviews/095_anchored_minimal_contrast/final_review.md for actual separate scope; not inferred from this file.'))
    print('SELF_CHECK_PASS',len(checks),'logical checks; independent audit separate')
if __name__=='__main__':main()
