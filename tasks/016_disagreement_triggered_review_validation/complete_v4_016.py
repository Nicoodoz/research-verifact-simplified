"""V4-first only, frozen missing jobs, carried task costs, no GT scoring or review."""
from pathlib import Path
from collections import Counter
from contextlib import contextmanager
import argparse
import common016 as c
import run016
import resume016
from budget016 import estimate

ORIGINAL=c.OUT
OUT=ORIGINAL/'v4_completion_001'

def require_v4_only(jobs,original_jobs,old_states):
    c.require(len(jobs)==len({j['request_id'] for j in jobs})==479,'Exactly479 never-sent V4 jobs required')
    expected={rid for rid,j in original_jobs.items() if j['role']=='v4_first' and old_states[rid]['status']=='pending' and old_states[rid]['attempts']==0}
    c.require({j['request_id'] for j in jobs}==expected,'Missing-job identity drift')
    for j in jobs:
        c.require(j['kind']=='chat' and j['role']=='v4_first' and j['body']['model']==c.V4,'Qwen/repeat/review disabled')
        c.require(j==original_jobs[j['request_id']],'Frozen request changed')

def pause_on_error(tr,attempts,unknowns,transient):
    if tr['http_status']==200:return 'received'
    # Existing account policy: only unanswered402 can move to the next account.
    if c.balance_exhausted(tr):return run016_next_status(tr,attempts,unknowns,transient)
    return 'configuration_pause'

run016_next_status=run016.next_status

def prepare():
    c.require(not OUT.exists(),'V4 completion already prepared')
    c.check_hashes(c.read(ORIGINAL/'handoff_001.json')['files_sha256'])
    c.check_hashes(c.read(resume016.RECOVERY/'handoff_001.json')['files_sha256'])
    recovered=resume016.current();c.require(recovered['new_valid']==0,'Unexpected new prior answers')
    original_jobs=c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl');lookup={j['request_id']:j for j in original_jobs}
    old=c.read(ORIGINAL/'interruption_001/reconciled_ledger.json');states=old['phases']['stage1_base_chat']['jobs']
    jobs=[j for j in original_jobs if j['role']=='v4_first' and states[j['request_id']]['status']!='received']
    require_v4_only(jobs,lookup,states)
    carry=recovered['task_total_cny'];cal=c.read(ORIGINAL/'token_calibration_001.json')
    estimates=[dict(request_id=j['request_id'],body_sha256=c.fingerprint(j['body']),**estimate(j['body'],cal)) for j in jobs]
    estimated=sum(e['cny'] for e in estimates);bound=sum(c.bound(j) for j in jobs)
    c.require(carry+bound<=40,'Even single-attempt conservative bound exceeds task cap')
    OUT.mkdir();prep=OUT/'stage1/base_preparation_001';prep.mkdir(parents=True)
    c.write_lines(prep/'jobs.jsonl',jobs)
    c.write_json(OUT/'protocol.json',dict(created_utc=c.now(),authorization='Latest user: disable all new Qwen requests/retries; fill V4 first Judge to601, then stop; no effects/repeat/independent-review',
        original_protocol_sha256=c.file_hash(ORIGINAL/'protocol_002.md'),original_V4_answers_retained=122,new_V4_jobs=479,target_V4_valid=601,
        same_patients_claims_C48_prompt_and_generation=True,all_new_jobs_never_sent_before=True,
        Qwen_new_calls_allowed=0,repeat_calls_allowed=0,independent_review_calls_allowed=0,GT_scoring_allowed=False,
        carry_cny=carry,task_cap_cny=40,remaining_V4_usage_estimate_cny=estimated,estimated_task_total_cny=carry+estimated,
        conservative_single_attempt_added_bound_cny=bound,conservative_task_total_bound_cny=carry+bound,
        fee_method='Same-body historical token calibration; also serialized UTF8 byte allowance plus full2048 output tokens per request at peak3/9 prices',
        error_policy='Stop new sends on network/service error, keep all receipts/reservations; no automatic unanswered retry except existing account rotation for402',
        original_and_recovery_records_and_locks_retained=True,stop_after_V4_complete=True,no_method_selection_or_new_patients=True))
    c.write_json(OUT/'prices_001.json',dict(checked_utc=c.now(),official_release_notes='https://docs.siliconflow.cn/docs/release-notes/overview',
        pricing_page='https://siliconflow.cn/pricing',pricing_page_refetch='Timed out; used freshly retrieved official release notes and same-day earlier successful pricing page',
        V4_peak_input_output=[3,9],V4_peak_cached_input=.3,off_peak_factor=.5,planning_uses_peak_no_cache=True,unit='CNY per million tokens'))
    (OUT/'token_calibration_001.json').write_bytes((ORIGINAL/'token_calibration_001.json').read_bytes())
    c.write_json(OUT/'carry.json',dict(task_total_cny=carry,original_cny=old['used_or_reserved_cny'],service_probe_additional_cny=recovered['recovery_cost_cny'],
        sources_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in [ORIGINAL/'interruption_001/reconciled_ledger.json',resume016.RECOVERY/'live/ledger.json',resume016.RECOVERY/'health_after_001.json']}))
    c.seal(prep,[ORIGINAL/'stage1/base_preparation_001/manifest.json',OUT/'protocol.json',OUT/'carry.json'],[Path(__file__)])
    code=c.execution_code()+[Path(__file__),c.TASK/'resume016.py']
    c.write_json(OUT/'authority_001.json',dict(approved=True,created_utc=c.now(),task_cap_cny=40,
        source='Latest user expressly authorizes V4-only completion from frozen checkpoint; original40 total cap unchanged',
        execution_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in code},scope_protocol_sha256=c.file_hash(OUT/'protocol.json')))
    (OUT/'live').mkdir()
    c.write_json(OUT/'live/ledger.json',dict(authority_sha256=c.file_hash(OUT/'authority_001.json'),cap_cny=40,used_or_reserved_cny=carry,
        carry_from_prior_cny=carry,carry_sha256=c.file_hash(OUT/'carry.json'),exhausted_accounts=old['exhausted_accounts'],phases={}))
    c.write_json(OUT/'budget_checks'/f'{c.file_hash(prep/"jobs.jsonl")}.json',dict(created_utc=c.now(),jobs_sha256=c.file_hash(prep/'jobs.jsonl'),within_cap=True,
        projected_task_total_cny=carry+bound,usage_based_expected_total_cny=carry+estimated,carry_cny=carry,request_token_estimates=estimates,
        price_snapshot_sha256=c.file_hash(OUT/'prices_001.json'),calibration_sha256=c.file_hash(OUT/'token_calibration_001.json'),scope='Only479 V4 first calls; no future Qwen/review pre-spending'))
    print(c.canonical(dict(old_V4=122,missing_V4=479,carry_cny=carry,usage_based_total_cny=carry+estimated,conservative_total_bound_cny=carry+bound,cap_cny=40)))

def send(limit=None):
    jobs=c.jsonlines(OUT/'stage1/base_preparation_001/jobs.jsonl')
    original_jobs={j['request_id']:j for j in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl')}
    states=c.read(ORIGINAL/'interruption_001/reconciled_ledger.json')['phases']['stage1_base_chat']['jobs']
    require_v4_only(jobs,original_jobs,states);c.check_hashes(c.read(OUT/'carry.json')['sources_sha256'])
    c.require(not (OUT/'completion_001').exists(),'V4-only scope already finished')
    c.OUT=OUT;run016.next_status=pause_on_error
    try:run016.execute(OUT/'stage1/base_preparation_001/jobs.jsonl',workers=4,limit=limit)
    finally:c.OUT=ORIGINAL;run016.next_status=run016_next_status

def collect_new():
    c.require(not (OUT/'task_api.lock').exists(),'V4 client still active')
    ledger=c.read(OUT/'live/ledger.json');carry=c.read(OUT/'carry.json');c.check_hashes(carry['sources_sha256'])
    c.require(ledger['carry_sha256']==c.file_hash(OUT/'carry.json') and ledger['carry_from_prior_cny']==carry['task_total_cny'],'Carry mismatch')
    phase='stage1_base_chat';folder=OUT/'live'/phase;spec=c.read(folder/'manifest.json');state=ledger['phases'][phase]
    c.require(state['run_id']==c.fingerprint(spec),'Run identity')
    jobs=c.jsonlines(OUT/'stage1/base_preparation_001/jobs.jsonl');total=carry['task_total_cny'];answers=[];attempts=[];seen=set()
    for j in jobs:
        p=state['jobs'][j['request_id']];successful=[]
        for ptr in p['receipts']:
            path=folder/ptr['file'];seen.add(path.name);c.require(c.file_hash(path)==ptr['sha256'],'Receipt changed');r=c.read(path);tr=r['transport']
            c.require(r['job_sha256']==c.fingerprint(j) and r['request_id']==j['request_id'] and r['run_id']==state['run_id'],'Receipt/request mismatch')
            fee,basis=c.cost(j,tr);c.require(abs(fee-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Fee mismatch');total+=fee
            attempts.append(dict(request_id=j['request_id'],proposition_id=j['proposition_id'],role=j['role'],attempt=r['attempt'],account=r['account'],http_status=tr['http_status'],
                charge_cny=fee,charge_basis=basis,started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],receipt=path.relative_to(c.ROOT).as_posix(),sha256=ptr['sha256']))
            if tr['http_status']==200:successful.append(r)
        c.require(len(successful)<=1,'Successful answer regenerated')
        for u in p.get('unreceipted',[]):
            total+=u['reservation'];attempts.append(dict(request_id=j['request_id'],proposition_id=j['proposition_id'],role=j['role'],attempt=u['attempt'],account=p.get('account',''),http_status=0,
                charge_cny=u['reservation'],charge_basis='unreceipted_unknown',started_utc='',ended_utc='',receipt='',sha256=''))
        if successful:answers.append(dict(c.normalize(j,successful[0]),role=j['role'],receipt=next(a['receipt'] for a in reversed(attempts) if a['http_status']==200)))
    c.require(seen=={p.name for p in folder.glob('receipt_*.json')},'Unbound receipts')
    c.require(abs(total-ledger['used_or_reserved_cny'])<1e-8 and total<=40,'Whole-task budget mismatch')
    return ledger,answers,attempts

def export(target=None):
    target=target or OUT/'completion_001';c.require(not target.exists(),'Completion export exists')
    c.check_hashes(c.read(ORIGINAL/'handoff_001.json')['files_sha256']);c.check_hashes(c.read(resume016.RECOVERY/'handoff_001.json')['files_sha256'])
    c.check_hashes(c.read(OUT/'authority_001.json')['execution_sha256']);c.check_manifest(OUT/'stage1/base_preparation_001')
    ledger,answers,attempts=collect_new();target.mkdir(parents=True)
    old=[r for r in c.jsonlines(ORIGINAL/'interruption_001/partial_normalized_responses.jsonl') if r['role']=='v4_first']
    c.require(len(old)==122 and all(r['status']=='success' for r in old),'Old122 labels invalid')
    valid=[a for a in answers if a['status']=='success'];allanswers=old+valid
    pids=[r['proposition_id'] for r in allanswers];c.require(len(set(pids))==len(pids),'Old/new prediction overlap')
    # Identity/coverage only; no GT values are read or evaluated.
    expected={r['proposition_id'] for r in c.jsonlines(ORIGINAL/'stage1/preparation_002/inputs.jsonl')}
    complete=len(valid)==479 and set(pids)==expected and len(pids)==601
    c.write_lines(target/'new_normalized_responses.jsonl',answers)
    c.write_csv(target/'attempts.csv',attempts)
    c.write_csv(target/'predictions_v4.csv',sorted([dict(proposition_id=r['proposition_id'],verdict=r['verdict']) for r in allanswers],key=lambda r:r['proposition_id']))
    c.write_csv(target/'provenance.csv',sorted([dict(proposition_id=r['proposition_id'],request_id=r['request_id'],source='original' if r in old else 'v4_completion_001') for r in allanswers],key=lambda r:r['proposition_id']))
    prior=c.read(OUT/'carry.json');new_cost=sum(a['charge_cny'] for a in attempts)
    summary=dict(status='V4_complete_stop_pending_Qwen' if complete else 'V4_incomplete_paused',complete=complete,original_V4_retained=122,new_V4_valid=len(valid),V4_total_valid=len(allanswers),expected_V4=601,
        prior_cost_or_reserved_cny=prior['task_total_cny'],new_V4_cost_or_reserved_cny=new_cost,task_total_cost_or_reserved_cny=ledger['used_or_reserved_cny'],task_cap_cny=40,
        new_http_attempts=len(attempts),new_http_statuses=dict(Counter(a['http_status'] for a in attempts)),accounts=dict(Counter(a['account'] for a in attempts)),
        new_usage={k:sum(a.get('usage',{}).get(k,0) for a in valid) for k in ('input_tokens','output_tokens','reasoning_tokens')},
        Qwen_new_calls=0,Qwen_retries=0,Qwen_valid_retained=124,repeat_calls=0,independent_review_calls=0,GT_effects_calculated=False,
        remaining_development_or_reserved_test_used=False,independent_audit=False,
        started_utc=min(a['started_utc'] for a in attempts if a['started_utc']),ended_utc=max(a['ended_utc'] for a in attempts if a['ended_utc']),
        baseline_spans_pre_and_post_pause=True,invalid_answers=[dict(request_id=a['request_id'],errors=a['structural_errors']) for a in answers if a['status']!='success'])
    c.write_json(target/'summary.json',summary)
    c.seal(target,[OUT/'live/ledger.json',OUT/'stage1/base_preparation_001/manifest.json',OUT/'carry.json'],[Path(__file__)])
    print(c.canonical(summary));return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','send','export'));p.add_argument('--limit',type=int);a=p.parse_args()
    if a.action=='send':send(a.limit)
    else:globals()[a.action]()
