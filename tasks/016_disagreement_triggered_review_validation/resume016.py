"""User-authorized service recovery, retaining old answers and all historical charges."""
from pathlib import Path
from collections import Counter
import argparse
import common016 as c
from budget016 import estimate
import run016

ORIGINAL=c.OUT
RECOVERY=ORIGINAL/'recovery_001'

def prepare():
    c.require(not RECOVERY.exists(),'Recovery already prepared')
    c.check_hashes(c.read(ORIGINAL/'handoff_001.json')['files_sha256'])
    prior=c.read(ORIGINAL/'interruption_001/reconciled_ledger.json')
    original_jobs=c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl')
    state=prior['phases']['stage1_base_chat']['jobs']
    missing=[j for j in original_jobs if state[j['request_id']]['status']!='received']
    c.require(len(missing)==956,'Unexpected remaining original jobs')
    probes=[]
    for role,n in [('qwen',2),('v4_first',1)]:
        probes += [j for j in missing if j['role']==role and state[j['request_id']]['attempts']==0][:n]
    c.require(len(probes)==3,'Missing never-sent probe candidates')
    ids={j['request_id'] for j in probes};jobs=probes+[j for j in missing if j['request_id'] not in ids]
    c.require(all(c.fingerprint(j)==c.fingerprint(next(x for x in original_jobs if x['request_id']==j['request_id'])) for j in jobs),'Request change')
    RECOVERY.mkdir();prep=RECOVERY/'stage1/base_preparation_001';prep.mkdir(parents=True)
    c.write_lines(prep/'jobs.jsonl',jobs)
    cal=c.read(ORIGINAL/'token_calibration_001.json');normal=sum(estimate(j['body'],cal)['cny'] for j in jobs)
    review=sum(estimate(j['body'],cal)['cny'] for j in original_jobs if j['role']=='v4_first')*.3*2*1.10
    carry=prior['used_or_reserved_cny'];projected=carry+normal+review+3
    c.write_json(RECOVERY/'protocol.json',dict(created_utc=c.now(),authorization='User: check service recovery and continue016 if recovered; original total cap40 retained',
        original_protocol_sha256=c.file_hash(ORIGINAL/'protocol_002.md'),original_carry_cny=carry,cap_cny=40,remaining_base_jobs=len(jobs),
        old_successful_answers_not_regenerated=246,original_unknown_reservations_retained=True,original_live_and_stop_lock_unchanged=True,
        pending_or_no_answer_only=True,probe_ids=[j['request_id'] for j in probes],probe_bound_cny=sum(c.bound(j) for j in probes),
        service_gate='Three sequential never-sent canonical jobs, Qwen/Qwen/V4. Each must yield a valid200 answer on first attempt; Qwen <=60sec, V4 <=30sec. Otherwise no bulk resume.',
        bulk_control='Only after gate pass, bounded batches and new cost checks; stop new batches on invalid answers or renewed failures/over-budget projections.',
        transport_amendment='Unanswered old failed/stopped requests may receive new attempts after explicit user recovery instruction; old attempts and fees remain, success never regenerated.',
        method_selection_gates_unchanged=True,GT_not_used_in_service_gate=True,conditional_stable_service_total_cny=projected,
        no_later_development_or_reserved_test=True))
    c.write_json(RECOVERY/'prices_001.json',dict(checked_utc=c.now(),source='https://siliconflow.cn/pricing',checked_again_on_recovery=True,
        V4_peak_input_output=[3,9],Qwen_input_output=[3,12],unit='CNY per million tokens',same_rates_as_original=True))
    (RECOVERY/'token_calibration_001.json').write_bytes((ORIGINAL/'token_calibration_001.json').read_bytes())
    c.seal(prep,[ORIGINAL/'stage1/base_preparation_001/manifest.json',ORIGINAL/'interruption_001/manifest.json',RECOVERY/'protocol.json'],[Path(__file__)])
    code=c.execution_code()+[Path(__file__)]
    c.write_json(RECOVERY/'authority_001.json',dict(approved=True,task_cap_cny=40,created_utc=c.now(),
        source='Latest explicit user instruction to check service and continue if recovered; conditional scope and carried costs in protocol.json',
        execution_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in code},
        recovery_protocol_sha256=c.file_hash(RECOVERY/'protocol.json'),original_authority_sha256=c.file_hash(ORIGINAL/'authority_001.json')))
    live=RECOVERY/'live';live.mkdir()
    c.write_json(live/'ledger.json',dict(authority_sha256=c.file_hash(RECOVERY/'authority_001.json'),cap_cny=40,
        used_or_reserved_cny=carry,carry_from_original_cny=carry,carry_source_sha256=c.file_hash(ORIGINAL/'interruption_001/reconciled_ledger.json'),exhausted_accounts=prior['exhausted_accounts'],phases={}))
    c.write_json(RECOVERY/'budget_checks'/f'{c.file_hash(prep/"jobs.jsonl")}.json',dict(jobs_sha256=c.file_hash(prep/'jobs.jsonl'),within_cap=projected<=40,
        projected_task_total_cny=projected,used_or_reserved_cny=carry,remaining_normal_cny=normal,future_disagreement_cny=review,retry_margin_cny=3,
        price_snapshot_sha256=c.file_hash(RECOVERY/'prices_001.json'),calibration_sha256=c.file_hash(RECOVERY/'token_calibration_001.json'),
        assumption='Full resume conditional on new service probes. Only three bounded probes authorized until health gate passes.'))
    c.require(projected<=40,'Even stable-service task forecast exceeds40')
    print(c.canonical(dict(carry_cny=carry,remaining_base_jobs=956,probe_bound_cny=sum(c.bound(j) for j in probes),conditional_total_cny=projected)))

def current():
    ledger=c.read(RECOVERY/'live/ledger.json');jobs={j['request_id']:j for j in c.jsonlines(RECOVERY/'stage1/base_preparation_001/jobs.jsonl')}
    results={};attempts=[];total=ledger['carry_from_original_cny']
    c.require(ledger['carry_source_sha256']==c.file_hash(ORIGINAL/'interruption_001/reconciled_ledger.json'),'Carry source drift')
    for phase,st in ledger['phases'].items():
        folder=RECOVERY/'live'/phase;spec=c.read(folder/'manifest.json');c.require(st['run_id']==c.fingerprint(spec),'Run identity')
        for rid,p in st['jobs'].items():
            for ptr in p['receipts']:
                f=folder/ptr['file'];c.require(c.file_hash(f)==ptr['sha256'],'Recovery receipt changed');r=c.read(f);j=jobs[rid]
                c.require(r['job_sha256']==c.fingerprint(j) and r['run_id']==st['run_id'],'Recovery body identity')
                fee,basis=c.cost(j,r['transport']);c.require(abs(fee-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Recovery charge mismatch')
                total+=fee;attempts.append(dict(request_id=rid,status=r['transport']['http_status'],fee_cny=fee))
                if r['transport']['http_status']==200:
                    c.require(rid not in results,'Successful recovery answer regenerated');results[rid]=c.normalize(j,r)
            for u in p.get('unreceipted',[]):total+=u['reservation']
    c.require(abs(total-ledger['used_or_reserved_cny'])<1e-8,'Carried task fees do not reconcile')
    protocol=c.read(RECOVERY/'protocol.json');checks=[]
    for rid in protocol['probe_ids']:
        n=results.get(rid,{});aa=[a for a in attempts if a['request_id']==rid];limit=60 if jobs[rid]['role']=='qwen' else 30
        checks.append(dict(role=jobs[rid]['role'],request_id=rid,attempts=len(aa),http=[a['status'] for a in aa],valid=n.get('status')=='success',
            latency_seconds=n.get('latency_seconds'),passed=len(aa)==1 and n.get('status')=='success' and n['latency_seconds']<=limit))
    return dict(created_utc=c.now(),task_total_cny=total,recovery_cost_cny=total-ledger['carry_from_original_cny'],
        new_attempts=len(attempts),new_valid=sum(n['status']=='success' for n in results.values()),checks=checks,
        service_gate_passed=all(x['passed'] for x in checks),failure_seen=any(a['status']!=200 for a in attempts),
        invalid_seen=any(n['status']!='success' for n in results.values()))

def probe():
    status=current();c.require(status['new_attempts']<3 and not status['failure_seen'] and not status['invalid_seen'],'Probe gate stopped or complete')
    for x in status['checks']:
        if x['attempts']:c.require(x['passed'],'Response too slow for bulk-recovery gate')
    c.OUT=RECOVERY
    try:run016.execute(RECOVERY/'stage1/base_preparation_001/jobs.jsonl',workers=1,limit=1)
    finally:c.OUT=ORIGINAL
    result=current();c.write_json(RECOVERY/f'health_after_{result["new_attempts"]:03d}.json',result);print(c.canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','probe','status'));a=p.parse_args()
    if a.action=='status':print(c.canonical(current()))
    else:globals()[a.action]()
