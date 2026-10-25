"""Final receipt, source, model, and accounting binding checks; no API calls."""
from collections import Counter
from decimal import Decimal
import json
import common019 as c

def verify():
    c.require(not (c.OUT/'task_api.lock').exists(), 'Wait for live sends to finish')
    c.check_manifest(c.OUT/'authority.json')
    ledger = c.read(c.OUT/'live_ledger.json')
    seen = set(); costs = Decimal('0'); unknown = []; statuses = Counter()
    normalized = Counter(); accounts = Counter(); bound_checks = 0
    for stage, phase in ledger['phases'].items():
        c.check_manifest(c.OUT/stage/'preparation/manifest.json')
        jobs = {j['request_id']: j for j in c.jsonlines(c.OUT/stage/'preparation/jobs.jsonl')}
        c.require(set(jobs)==set(phase['jobs']), 'Job identities changed')
        for rid, progress in phase['jobs'].items():
            c.require(progress['status']!='in_flight', 'Unresolved live request')
            attempts = set(); successful = 0; job = jobs[rid]
            for ptr in progress['receipts']:
                path = c.OUT/ptr['file']
                c.require(ptr['file'] not in seen, 'Receipt reused')
                seen.add(ptr['file'])
                c.require(c.file_hash(path)==ptr['sha256'], 'Receipt hash mismatch')
                rec = c.read(path); tr = rec['transport']
                c.require(rec['request_id']==rid and rec['job_sha256']==c.fingerprint(job), 'Wrong request binding')
                c.require(rec['provider'] in ('siliconflow','aliyun'), 'Unknown provider')
                expected = dict(job['body'], model=c.MODEL if rec['provider']=='siliconflow' else c.ALI_MODEL)
                c.require(rec['actual_body']==expected, 'Actual request differs from frozen body')
                c.require(rec['actual_body_sha256']==c.fingerprint(expected), 'Actual body digest mismatch')
                endpoint = c.read(c.OUT/'authority.json')['Alibaba_endpoint'] if rec['provider']=='aliyun' else 'https://api.siliconflow.cn/v1/chat/completions'
                c.require(rec['endpoint']==endpoint, 'Endpoint mismatch')
                c.require(rec['attempt'] not in attempts, 'Attempt duplicated')
                attempts.add(rec['attempt'])
                fee, basis = c.charge(expected, tr)
                c.require(abs(fee-ptr['charge_cny'])<1e-12 and basis==ptr['charge_basis'], 'Fee mismatch')
                costs += Decimal(str(fee)); statuses[tr['http_status']] += 1
                c.require(fee<=c.bound(expected)+1e-12, 'Request bound exceeded')
                bound_checks += 1
                if tr['http_status']==200:
                    successful += 1
                    parsed = c.parse(tr, job['arm']=='S')
                    normalized[(stage, parsed['status'])] += 1
                    accounts[(rec['provider'], rec['account'])] += 1
                    c.require(parsed['model_returned']==expected['model'], 'Returned model alias differs')
            for lost in progress.get('unreceipted_attempts', []):
                c.require(lost['attempt'] not in attempts, 'Unknown attempt counted twice')
                attempts.add(lost['attempt']); costs += Decimal(str(lost['reserved_cny']))
                unknown.append(dict(stage=stage,request_id=rid,**lost))
            c.require(attempts==set(range(1,progress['attempts']+1)), 'Missing attempt provenance')
            c.require(successful<=1, 'Successful answer was repeated')
            if progress['status']=='received':
                c.require(successful==1, 'Received status without receipt')
    disk={p.relative_to(c.OUT).as_posix() for s in ledger['phases'] for p in (c.OUT/s/'live').glob('receipt_*.json')}
    c.require(seen==disk, 'Unregistered or missing receipt')
    c.require(abs(float(costs)-ledger['used_or_reserved_cny'])<1e-8 and float(costs)<=80, 'Cumulative cost mismatch')
    result = dict(created_utc=c.now(),passed=True,executor_verification_only=True,
        independent_audit=False,receipt_count=len(seen),unreceipted_attempts=len(unknown),
        total_attempts=len(seen)+len(unknown),HTTP_status_counts=dict(statuses),
        normalized_counts=[dict(stage=s,status=k,n=v) for (s,k),v in normalized.items()],
        accounts=[dict(provider=p,account=a,n=v) for (p,a),v in accounts.items()],
        used_or_reserved_cny=float(costs),request_bound_checks=bound_checks,
        no_duplicate_successes=True,exact_request_bindings=True,
        unknown_cost_retained=unknown)
    c.write_json(c.OUT/'receipt_integrity_001.json',result)
    print(c.canonical(result),flush=True)

if __name__=='__main__':
    verify()
