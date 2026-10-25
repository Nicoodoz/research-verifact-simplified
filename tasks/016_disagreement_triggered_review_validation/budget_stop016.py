"""Read-only rolling service-cost forecast. Does not load keys, call API, or score labels."""
from datetime import datetime,timezone,timedelta
from collections import Counter
import common016 as c
from budget016 import estimate

def assess():
    jobs={j['request_id']:j for j in c.jsonlines(c.OUT/'stage1/base_preparation_001/jobs.jsonl')}
    ledger=c.read(c.OUT/'live/ledger.json');state=ledger['phases']['stage1_base_chat']['jobs'];cut=datetime.now(timezone.utc)-timedelta(minutes=10)
    receipts=[c.read(p) for p in (c.OUT/'live/stage1_base_chat').glob('receipt_*.json')]
    recent=[r for r in receipts if datetime.fromisoformat(r['transport']['ended_utc'])>=cut]
    cal=c.read(c.OUT/'token_calibration_001.json');normal=sum(estimate(j['body'],cal)['cny'] for rid,j in jobs.items() if state[rid]['status'] not in ('received','in_flight'))
    failure_allowances={};windows={}
    for role in ('v4_first','qwen'):
        rr=[r for r in recent if jobs[r['request_id']]['role']==role];success=sum(r['transport']['http_status']==200 for r in rr)
        failed=[r for r in rr if r['transport']['http_status']!=200];charge=sum(c.cost(jobs[r['request_id']],r['transport'])[0] for r in failed)
        remaining=sum(j['role']==role and state[rid]['status'] not in ('received','in_flight') for rid,j in jobs.items())
        failure_allowances[role]=charge/success*remaining if success else None
        windows[role]=dict(success=success,failures=len(failed),failure_http_counts=dict(Counter(r['transport']['http_status'] for r in failed)),
            failed_or_unknown_reservations_cny=charge,remaining_unsatisfied_not_inflight=remaining)
    # Existing preregistered 30% disagreement planning allowance; no GT or label-rate inspection.
    future=sum(estimate(j['body'],cal)['cny'] for j in jobs.values() if j['role']=='v4_first')*.30*2*1.10
    projected=ledger['used_or_reserved_cny']+normal+sum(v for v in failure_allowances.values() if v is not None)+future
    out=c.OUT/'interruption_001';out.mkdir(exist_ok=False)
    record=dict(created_utc=c.now(),reason='Service failures invalidate initial <=40 task forecast; stop required by task-wide budget rule',
        window_minutes=10,window_start=cut.isoformat(),observed=windows,ledger_used_or_reserved_cny=ledger['used_or_reserved_cny'],
        remaining_normal_token_estimated_cny=normal,projected_additional_failure_reservations_cny=failure_allowances,
        original_future_disagreement_allowance_cny=future,projected_task_total_cny=projected,task_cap_cny=40,
        over_cap=projected>40 or any(v is None for v in failure_allowances.values()),
        terminal_failures=[dict(request_id=rid,role=jobs[rid]['role'],status=p['status'],attempts=p['attempts']) for rid,p in state.items() if p['status'].startswith('failed')],
        uncertainty='Rolling recent service conditions, not an invoice or guaranteed future failure rate. Recovery cannot be assumed to authorize continued sends.',
        model_labels_or_GT_used=False,original_estimate_retained=True)
    c.write_json(out/'budget_reassessment.json',record);print(c.canonical(record))

if __name__=='__main__':assess()
