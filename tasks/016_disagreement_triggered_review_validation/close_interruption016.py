"""Close a budget-stopped client without inventing responses or altering the live run."""
from collections import Counter
from decimal import Decimal
from pathlib import Path
import copy
import common016 as c
from replay_history import check_history

def close():
    out=c.OUT/'interruption_001';c.require((out/'budget_reassessment.json').exists(),'Missing stop rationale')
    c.require(c.read(out/'budget_reassessment.json')['over_cap'],'No budget stop condition')
    auth=c.read(c.OUT/'authority_001.json');c.check_hashes(auth['execution_sha256'])
    c.require((c.OUT/'task_api.lock').exists(),'Retain API stop lock to prohibit accidental resume')
    original=c.read(c.OUT/'live/ledger.json');ledger=copy.deepcopy(original)
    c.write_json(out/'ledger_at_stop.json',original);attempts=[];normal=[];predictions=[];changes=[];frozen={}
    def bind(p):frozen[p.relative_to(c.ROOT).as_posix()]=c.file_hash(p)
    for p in (c.OUT/'live/ledger.json',c.OUT/'task_api.lock',c.OUT/'authority_001.json',c.OUT/'protocol_002.md',c.OUT/'prices_001.json'):bind(p)
    for phase,state in ledger['phases'].items():
        folder=c.OUT/'live'/phase;spec=c.read(folder/'manifest.json');bind(folder/'manifest.json');jobs_path=c.ROOT/spec['jobfile'];bind(jobs_path)
        c.require(state['run_id']==c.fingerprint(spec) and c.file_hash(jobs_path)==spec['jobs_sha256'],'Phase binding')
        c.require(spec['authority_sha256']==c.file_hash(c.OUT/'authority_001.json'),'Authority mismatch')
        c.check_manifest(jobs_path.parent);jobs=c.jsonlines(jobs_path);seen=set()
        for i,j in enumerate(jobs):
            p=state['jobs'][j['request_id']]
            if p['status']=='in_flight':
                orphan=folder/f'receipt_{i+1:06d}_{p["attempts"]:02d}.json'
                if orphan.exists():
                    r=c.read(orphan);c.require(r['attempt']==p['attempts'] and r['job_sha256']==c.fingerprint(j),'Orphan binding')
                    charge,basis=c.cost(j,r['transport'])
                    ledger['used_or_reserved_cny']=float(Decimal(str(ledger['used_or_reserved_cny']))-Decimal(str(c.bound(j)))+Decimal(str(charge)))
                    p['receipts'].append(dict(file=orphan.name,sha256=c.file_hash(orphan),charge_cny=charge,charge_basis=basis))
                    p['status']='received' if r['transport']['http_status']==200 else 'stopped_after_error'
                    changes.append(dict(phase=phase,request_id=j['request_id'],action='recovered_saved_receipt',receipt=orphan.name))
                else:
                    p.setdefault('unreceipted',[]).append(dict(attempt=p['attempts'],reservation=c.bound(j),reason='client_terminated_for_budget_stop'))
                    p['status']='stopped_unknown';p['unknowns']+=1
                    changes.append(dict(phase=phase,request_id=j['request_id'],action='retain_existing_inflight_reservation',reservation_cny=c.bound(j)))
            successful=[]
            for ptr in p['receipts']:
                path=folder/ptr['file'];seen.add(path.name);bind(path);c.require(c.file_hash(path)==ptr['sha256'],'Receipt changed')
                r=c.read(path);tr=r['transport'];c.require(r['request_id']==j['request_id'] and r['run_id']==state['run_id'] and r['job_sha256']==c.fingerprint(j),'Receipt binding')
                charge,basis=c.cost(j,tr);c.require(abs(charge-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Fee mismatch')
                attempts.append(dict(phase=phase,request_id=j['request_id'],role=j.get('role',''),attempt=r['attempt'],account=r['account'],http_status=tr['http_status'],
                    charge_cny=charge,charge_basis=basis,started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],receipt=path.relative_to(c.ROOT).as_posix(),sha256=ptr['sha256']))
                if tr['http_status']==200:successful.append(r)
            c.require(len(successful)<=1,'Successful answer regenerated')
            if j['kind']=='chat' and successful:
                n=c.normalize(j,successful[0]);normal.append(dict(n,role=j['role']))
                if n['status']=='success':predictions.append(dict(proposition_id=j['proposition_id'],role=j['role'],verdict=n['verdict'],request_id=j['request_id']))
            for u in p.get('unreceipted',[]):
                attempts.append(dict(phase=phase,request_id=j['request_id'],role=j.get('role',''),attempt=u['attempt'],account=p.get('account',''),http_status=0,
                    charge_cny=u['reservation'],charge_basis='unreceipted_unknown_reservation',started_utc=p.get('started_utc',''),ended_utc='',receipt='',sha256=''))
        c.require(seen=={p.name for p in folder.glob('receipt_*.json')},'Unbound raw receipts')
    total=sum(a['charge_cny'] for a in attempts);c.require(abs(total-ledger['used_or_reserved_cny'])<1e-8 and total<=40,'Task accounting mismatch')
    ledger['interruption']=dict(stopped_utc=c.now(),reason='updated_cost_projection_over_40',no_automatic_resume=True,
        original_live_ledger_unchanged=True,API_lock_retained=True,remaining_task_cap_cny=40-total)
    c.write_json(out/'reconciled_ledger.json',ledger);c.write_json(out/'reconciliation_actions.json',changes)
    c.write_csv(out/'attempts.csv',attempts);c.write_lines(out/'partial_normalized_responses.jsonl',normal)
    c.write_csv(out/'partial_predictions.csv',predictions)
    history=check_history(c.read(c.OUT/'historical_protection_001.json'),bindings={});c.write_json(out/'history_check.json',history)
    summary=dict(status='stopped_budget_forecast_incomplete_no_efficacy_conclusion',created_utc=c.now(),
        intended_claims=601,intended_base_judge_calls=1202,received_base_answers=len(normal),valid_partial_predictions=len(predictions),
        valid_by_role=dict(Counter(r['role'] for r in predictions)),http_receipts=sum(bool(a['receipt']) for a in attempts),
        unreceipted_stopped_or_unknown_attempts=sum(not bool(a['receipt']) for a in attempts),attempts_including_unreceipted=len(attempts),
        receipt_http_counts=dict(Counter(a['http_status'] for a in attempts if a['receipt'])),
        received_usage_estimated_cny=sum(a['charge_cny'] for a in attempts if 'unknown' not in a['charge_basis']),
        unknown_or_failed_usage_reserved_cny=sum(a['charge_cny'] for a in attempts if 'unknown' in a['charge_basis']),
        total_used_or_reserved_cny=total,hard_task_cap_cny=40,remaining_cap_cny=40-total,
        inference_scope='601 fixed claims, V4/Qwen base only; no disagreement review sent',
        no_GT_performance_evaluation=True,no_available_case_comparison=True,ordinary_repeat_calls=0,independent_review_calls=0,
        final_confirmation_performed=False,reserved_test_selected_or_analyzed=False,scientific_direction_failed=False,
        no_automatic_resume=True,partial_failures=[dict(request_id=n['request_id'],errors=n['structural_errors']) for n in normal if n['status']!='success'],
        protected_history_files=history['strict_unchanged_files'],accounts=dict(Counter(a['account'] for a in attempts)))
    c.write_json(out/'summary.json',summary);c.write_json(out/'live_frozen_files.json',frozen)
    c.seal(out,[],[Path(__file__),c.TASK/'budget_stop016.py',c.TASK/'common016.py'])
    print(c.canonical(summary))

if __name__=='__main__':close()
