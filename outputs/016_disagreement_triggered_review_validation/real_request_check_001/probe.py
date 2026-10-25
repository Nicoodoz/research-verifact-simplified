"""One authorized never-sent frozen Qwen judge request; retain answer, no batch or scoring."""
from pathlib import Path
import sys
from datetime import datetime

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tasks/016_disagreement_triggered_review_validation'))
import common016 as c
from budget016 import estimate

out=Path(__file__).resolve().parent
checkpoint=c.read(c.OUT/'current_checkpoint_002.json')
base=c.OUT/'stage1/base_preparation_001'
c.check_manifest(base)
c.check_hashes(c.read(c.OUT/'service_check_001/manifest.json')['files'])
old=c.read(c.OUT/'interruption_001/reconciled_ledger.json')['phases']['stage1_base_chat']['jobs']
recovery=c.read(c.OUT/'recovery_001/live/ledger.json')['phases']['stage1_base_chat']['jobs']
jobs=c.jsonlines(base/'jobs.jsonl')
job=next(j for j in jobs if j['role']=='qwen' and old[j['request_id']]['attempts']==0 and recovery[j['request_id']]['attempts']==0)
c.require(job['body']['model']==c.QWEN and job['body']['max_tokens']==2048,'Unexpected frozen request')
carry=checkpoint['whole_task_used_or_reserved_cny'];bound=c.bound(job)
c.require(carry+bound<=40,'016 whole task cap exceeded')
cal=c.read(c.OUT/'token_calibration_001.json')
c.write_json(out/'request.json',job)
registration=dict(created_utc=c.now(),authorization='User explicitly asks to test one real experiment request',
    selected_by='First never-attempted Qwen job in original frozen order; exclude original and recovery attempts',
    request_id=job['request_id'],body_sha256=c.fingerprint(job['body']),original_jobs_sha256=c.file_hash(base/'jobs.jsonl'),
    checkpoint_sha256=c.file_hash(c.OUT/'current_checkpoint_002.json'),estimated_usage_cost=estimate(job['body'],cal),
    carried_task_cost_cny=carry,additional_max_reservation_cny=bound,task_cap_cny=40,
    requests_allowed=1,retries_allowed=0,HTTP_timeout_seconds=180,claim_reference_prompt_generation_unchanged=True,
    GT_used=False,no_batch_resume=True,no_repeat_or_independent_review=True,retain_first_valid_answer_for_original016=True)
c.write_json(out/'authorization.json',registration)
accounts=[a for a in c.load_accounts(ROOT/'.env.siliconflow_pool',environ={}) if int(a.alias.split('_')[-1])>=2]
c.require(accounts and accounts[0].alias=='account_2','Account2 required')
a=accounts[0]
tr=c.NATIVE.HttpClient().send(a,job)
for account in accounts:tr['body_text']=tr['body_text'].replace(account.key,'[REDACTED_API_KEY]')
receipt=dict(run_id=c.fingerprint(registration),request_id=job['request_id'],job_sha256=c.fingerprint(job),account=a.alias,attempt=1,transport=tr)
c.write_json(out/'receipt.json',receipt)
fee,basis=c.cost(job,tr);normalized=c.normalize(job,receipt)
c.write_json(out/'normalized.json',normalized)
valid=normalized['status']=='success'
if valid:c.write_csv(out/'prediction_qwen.csv',[dict(proposition_id=job['proposition_id'],verdict=normalized['verdict'],request_id=job['request_id'])])
elapsed=(datetime.fromisoformat(tr['ended_utc'])-datetime.fromisoformat(tr['started_utc'])).total_seconds()
summary=dict(checked_utc=tr['ended_utc'],model=c.QWEN,request_id=job['request_id'],http_status=tr['http_status'],valid_answer=valid,
    latency_seconds=elapsed,usage=normalized.get('usage'),structural_errors=normalized['structural_errors'],adherence_errors=normalized.get('adherence_errors',[]),
    additional_cost_or_reserved_cny=fee,cost_basis=basis,task_total_cost_or_reserved_cny=carry+fee,task_cap_cny=40,
    V4_valid=601,Qwen_valid=checkpoint['Qwen_valid']+int(valid),requests_sent=1,retries=0,
    no_GT_evaluation=True,batch_resumed=False,repeat_or_independent_review_calls=0,
    limitation='One authentic request only; does not establish sustained batch stability.')
c.write_json(out/'summary.json',summary)
c.seal(out,[base/'manifest.json',c.OUT/'current_checkpoint_002.json'],[Path(__file__)])
print(c.canonical(summary))
