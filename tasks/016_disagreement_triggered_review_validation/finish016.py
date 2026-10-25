"""Complete the existing016 protocol with immutable prior runs and a carried40 CNY cap."""
from pathlib import Path
from collections import Counter
import argparse
import common016 as c
import run016
from budget016 import estimate
from finish_io016 import ORIGINAL,FINAL,collect,base_labels

def assert_jobs(jobs,role_set,excluded=()):
    c.require(len(jobs)==len({j['request_id'] for j in jobs}),'Duplicate jobs')
    c.require(not set(excluded)&{j['request_id'] for j in jobs},'Successful answer scheduled again')
    for j in jobs:
        c.require(j['kind']=='chat' and j['role'] in role_set,'Unexpected role')
        c.require(j['body']['model']==(c.QWEN if j['role']=='qwen' else c.V4),'Unexpected model')
        c.require(set(c.pilot.strict_json(j['body']['messages'][1]['content']))=={'proposition','reference'},'Judge metadata leakage')

def prepare():
    c.require(not FINAL.exists(),'Existing016 finalization already prepared')
    for name in ('handoff_001.json','recovery_001/handoff_001.json','v4_completion_001/handoff_001.json'):
        c.check_hashes(c.read(ORIGINAL/name)['files_sha256'])
    values,attempts,carry=collect(False);labels,provenance=base_labels(values)
    counts=Counter(p['role'] for p in provenance);c.require(counts=={'v4_first':601,'qwen':125},'Checkpoint counts drift')
    original_jobs=c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl')
    jobs=[j for j in original_jobs if j['role']=='qwen' and j['request_id'] not in values]
    c.require(len(jobs)==476,'Unexpected missing Qwen');assert_jobs(jobs,{'qwen'},values)
    FINAL.mkdir();prep=FINAL/'stage1/base_preparation_001';prep.mkdir(parents=True)
    c.write_lines(prep/'jobs.jsonl',jobs);c.write_csv(prep/'retained_base_answers.csv',provenance)
    c.write_json(FINAL/'continuation_protocol.json',dict(created_utc=c.now(),authorization='User explicitly authorizes completing existing016: Qwen, disagreement-only repeat/review,002 evaluation; total cap40; no expansion',
        original_protocol_sha256=c.file_hash(ORIGINAL/'protocol_002.md'),gate_code_sha256=c.file_hash(c.TASK/'decisions016.py'),
        same601_claims_and_C48=True,V4_retained=601,Qwen_retained=125,Qwen_missing=476,carry_cny=carry,task_cap_cny=40,
        historical_answers_failures_unknowns_and_locks_unchanged=True,successful200_answers_never_regenerated=True,
        prior_unanswered_jobs_may_be_completed=True,latest_instruction_reopens_previously_paused_Qwen_and_review_only=True,
        normal_batches_max_attempts=48,first_batch_attempts=8,workers=4,reestimate_after_each_batch=True,
        no_prompt_trigger_retrieval_optimization=True,no_remaining_development_or_reserved_test=True,
        run_timing_deviation='Original interleaved contemporaneous baseline plan was interrupted. User-directed V4-only completion and later Qwen continuation span periods. Disclose this; do not regenerate successes to restore simultaneity.',
        research_gate_unchanged='All original protocol002 and decisions016 conditions; no post-result lowering; pass only merits future confirmation, no automatic expansion'))
    c.write_json(FINAL/'prices_001.json',dict(checked_utc=c.now(),source='https://siliconflow.cn/pricing',official_live_page_read=True,
        V4_peak_input_output=[3,9],V4_peak_cache=.3,Qwen_input_output=[3,12],unit='CNY per million tokens',planning_uses_peak_no_cache=True))
    (FINAL/'token_calibration_001.json').write_bytes((ORIGINAL/'token_calibration_001.json').read_bytes())
    c.write_json(FINAL/'carry.json',dict(total_cny=carry,all_prior_attempts=len(attempts),
        checkpoint_sha256=c.file_hash(ORIGINAL/'current_checkpoint_003.json'),all_prior_request_receipts_retained=True))
    c.write_csv(FINAL/'prior_attempts.csv',attempts)
    c.seal(prep,[ORIGINAL/'stage1/base_preparation_001/manifest.json',FINAL/'continuation_protocol.json',FINAL/'carry.json'],[Path(__file__),c.TASK/'finish_io016.py'])
    code=c.execution_code()+[Path(__file__),c.TASK/'finish_io016.py']
    c.write_json(FINAL/'authority_001.json',dict(approved=True,created_utc=c.now(),task_cap_cny=40,
        source='Latest explicit user continuation instruction; existing task total budget remains40',
        execution_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in code},protocol_sha256=c.file_hash(FINAL/'continuation_protocol.json')))
    (FINAL/'live').mkdir()
    c.write_json(FINAL/'live/ledger.json',dict(authority_sha256=c.file_hash(FINAL/'authority_001.json'),cap_cny=40,used_or_reserved_cny=carry,
        carry_from_prior_cny=carry,carry_sha256=c.file_hash(FINAL/'carry.json'),exhausted_accounts=c.read(ORIGINAL/'v4_completion_001/live/ledger.json')['exhausted_accounts'],phases={}))
    print(c.canonical(dict(V4_retained=601,Qwen_retained=125,Qwen_to_send=476,carry_cny=carry,cap_cny=40)))

def forecast(part):
    values,attempts,total=collect();base_labels(values)
    path=FINAL/'stage1'/('base_preparation_001' if part=='base' else 'review_preparation_001')/'jobs.jsonl'
    jobs=c.jsonlines(path);cal=c.read(FINAL/'token_calibration_001.json')
    pending=[j for j in jobs if j['request_id'] not in values]
    expected=sum(estimate(j['body'],cal)['cny'] for j in pending)
    if part=='base':
        review_est=sum(estimate(j['body'],cal)['cny'] for j in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl') if j['role']=='v4_first')*.30*2*1.10
    else:review_est=0.
    recent=[a for a in attempts if a['epoch']=='finalization_001' and a['phase']==f'stage1_{part}_chat'][-48:]
    good=sum(a['http_status']==200 for a in recent);bad=[a for a in recent if a['http_status'] not in (200,402)]
    uncertain=bool(bad and good==0)
    margin=max(2.,sum(a['charge_cny'] for a in bad)/max(1,good)*len(pending))
    projected=total+expected+review_est+margin
    folder=FINAL/'budget_history';folder.mkdir(exist_ok=True);number=len(list(folder.glob('*.json')))+1
    record=dict(created_utc=c.now(),part=part,jobs_sha256=c.file_hash(path),used_or_reserved_cny=total,remaining_jobs=len(pending),
        expected_remaining_cny=expected,future_disagreement_allowance_cny=review_est,failure_margin_cny=margin,
        recent_successes=good,recent_failures=len(bad),projected_task_total_cny=projected,cap_cny=40,within_cap=projected<=40 and not uncertain,
        price_snapshot_sha256=c.file_hash(FINAL/'prices_001.json'),calibration_sha256=c.file_hash(FINAL/'token_calibration_001.json'))
    c.write_json(folder/f'estimate_{number:03d}.json',record)
    # This is a mutable prospective control pointer; every version is saved above, raw runs remain immutable.
    control=FINAL/'budget_checks'/f'{c.file_hash(path)}.json';control.parent.mkdir(exist_ok=True)
    c.save(control,record)
    c.require(record['within_cap'],'Whole016 forecast exceeds40 or new service cannot be reasonably estimated')
    print(c.canonical(record));return path,pending

def send(part,limit):
    c.require(1<=limit<=48,'Bounded batches only')
    c.require(not (FINAL/'analysis_001').exists(),'Analysis begun; no further sends')
    path,pending=forecast(part)
    if not pending:print('No pending jobs');return
    values,_,_=collect()
    assert_jobs(pending,{'qwen'} if part=='base' else {'v4_repeat','independent_review'},values)
    if part=='base':
        original={j['request_id']:j for j in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl')}
        c.require(all(j==original[j['request_id']] for j in pending),'Qwen body changed')
    else:
        allowed={r['proposition_id'] for r in c.csvrows(path.parent/'trigger.csv') if r['disagreement']=='True'}
        c.require(all(j['proposition_id'] in allowed for j in pending),'Review outside disagreement set')
    c.OUT=FINAL
    try:run016.execute(path,workers=4,limit=limit)
    finally:c.OUT=ORIGINAL
    vv,aa,total=collect();base_labels(vv)
    new=[a for a in aa if a['epoch']=='finalization_001'];print(c.canonical(dict(whole_task_cny=total,new_attempts=len(new),new_successes=sum(a['http_status']==200 for a in new))))

def review():
    values,attempts,total=collect();labels,provenance=base_labels(values,True)
    target=FINAL/'canonical_base_001';c.require(not target.exists(),'Canonical base already frozen');target.mkdir()
    c.write_csv(target/'provenance.csv',provenance)
    for role in ('v4_first','qwen'):c.write_csv(target/f'predictions_{role}.csv',[dict(proposition_id=pid,verdict=labels[pid][role]) for pid in sorted(labels)])
    c.write_json(target/'summary.json',dict(claims=601,V4=601,Qwen=601,task_used_or_reserved_cny=total,no_GT_used_for_trigger=True))
    c.write_json(target/'base_ledger_snapshot.json',c.read(FINAL/'live/ledger.json'))
    c.seal(target,[ORIGINAL/'stage1/base_preparation_001/manifest.json'],[Path(__file__),c.TASK/'finish_io016.py'])
    prompts=c.read(ORIGINAL/'stage1/preparation_002/judge_prompts.json');jobs={};assignments=[];triggers=[]
    for item in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/inputs.jsonl'):
        pid=item['proposition_id'];p=labels[pid];different=p['v4_first']!=p['qwen'];triggers.append(dict(proposition_id=pid,**p,disagreement=different))
        if not different:continue
        for role in ('v4_repeat','independent_review'):
            body=c.judge_body(item,item['reference'],prompts,role);sha=c.fingerprint(body);rid=f'016:stage1:{role}:{sha}'
            jobs.setdefault(rid,dict(request_id=rid,kind='chat',role=role,proposition_id=pid,case_id=item['case_id'],body=body))
            assignments.append(dict(proposition_id=pid,case_id=item['case_id'],role=role,request_id=rid,body_sha256=sha))
    prep=FINAL/'stage1/review_preparation_001';prep.mkdir()
    ordered=sorted(jobs.values(),key=lambda j:c.hash_rank(j['request_id'],'016/review-send/v1:'));assert_jobs(ordered,{'v4_repeat','independent_review'},values)
    c.write_lines(prep/'jobs.jsonl',ordered);c.write_csv(prep/'assignments.csv',assignments,['proposition_id','case_id','role','request_id','body_sha256']);c.write_csv(prep/'trigger.csv',triggers)
    summary=dict(claims=601,disagreements=sum(t['disagreement'] for t in triggers),logical_review_calls=len(assignments),actual_review_calls=len(ordered),GT_used=False)
    c.write_json(prep/'summary.json',summary)
    # Bind immutable base exports, not the live ledger which continues accumulating later review costs.
    c.seal(prep,[target/'provenance.csv',target/'predictions_v4_first.csv',target/'predictions_qwen.csv',ORIGINAL/'stage1/preparation_002/judge_prompts.json'],[Path(__file__),c.TASK/'finish_io016.py',c.TASK/'common016.py'])
    print(c.canonical(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','send','review','forecast'));p.add_argument('--part',choices=('base','review'),default='base');p.add_argument('--limit',type=int,default=48);a=p.parse_args()
    if a.action=='send':send(a.part,a.limit)
    elif a.action=='forecast':forecast(a.part)
    else:globals()[a.action]()
