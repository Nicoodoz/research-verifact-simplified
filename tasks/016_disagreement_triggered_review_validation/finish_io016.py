"""Read canonical answers and all costs across immutable016 continuations; no API."""
from pathlib import Path
import common016 as c

ORIGINAL=c.OUT
FINAL=ORIGINAL/'finalization_001'

def read_run(root,ledger_path=None):
    ledger_path=ledger_path or root/'live/ledger.json'
    ledger=c.read(ledger_path);values={};attempts=[]
    for phase,state in ledger['phases'].items():
        folder=root/'live'/phase;spec=c.read(folder/'manifest.json');jobfile=c.ROOT/spec['jobfile']
        c.require(state['run_id']==c.fingerprint(spec) and c.file_hash(jobfile)==spec['jobs_sha256'],'Run/job identity drift')
        c.check_manifest(jobfile.parent);seen=set()
        for j in c.jsonlines(jobfile):
            p=state['jobs'][j['request_id']];success=[]
            c.require(p['status']!='in_flight','Wait for active sends before receipt collection')
            for ptr in p['receipts']:
                file=folder/ptr['file'];seen.add(file.name);c.require(c.file_hash(file)==ptr['sha256'],'Receipt changed')
                r=c.read(file);tr=r['transport']
                c.require(r['run_id']==state['run_id'] and r['request_id']==j['request_id'] and r['job_sha256']==c.fingerprint(j),'Receipt binding')
                fee,basis=c.cost(j,tr);c.require(abs(fee-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Fee mismatch')
                attempts.append(dict(epoch=root.relative_to(ORIGINAL).as_posix(),phase=phase,request_id=j['request_id'],role=j.get('role',''),attempt=r['attempt'],
                    account=r['account'],http_status=tr['http_status'],charge_cny=fee,charge_basis=basis,started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],
                    receipt=file.relative_to(c.ROOT).as_posix(),sha256=ptr['sha256']))
                if tr['http_status']==200:success.append((r,file))
            for u in p.get('unreceipted',[]):
                c.require(abs(u['reservation']-c.bound(j))<1e-10,'Unknown reservation changed')
                attempts.append(dict(epoch=root.relative_to(ORIGINAL).as_posix(),phase=phase,request_id=j['request_id'],role=j.get('role',''),attempt=u['attempt'],account=p.get('account',''),
                    http_status=0,charge_cny=u['reservation'],charge_basis='unreceipted_unknown_reservation',started_utc=p.get('started_utc',''),ended_utc='',receipt='',sha256=''))
            c.require(len(success)<=1,'Successful response regenerated within run')
            if success:
                r,file=success[0];values[j['request_id']]=dict(job=j,receipt=r,receipt_path=file.relative_to(c.ROOT).as_posix(),native=c.pilot.strict_json(r['transport']['body_text']))
        c.require(seen=={p.name for p in folder.glob('receipt_*.json')},'Unbound receipt file')
    own=sum(a['charge_cny'] for a in attempts)
    carry=ledger.get('carry_from_original_cny',ledger.get('carry_from_prior_cny',0.))
    c.require(abs(own+carry-ledger['used_or_reserved_cny'])<1e-8,'Run carry accounting mismatch')
    return values,attempts,ledger

def read_single(name,short=False):
    root=ORIGINAL/name;c.check_manifest(root)
    job=c.read(root/'request.json');raw=c.read(root/'receipt.json')
    if short:
        body=job;job=dict(request_id=name,kind='chat',role='service_probe',body=body)
        tr={k:raw[k] for k in ('http_status','body_text','started_utc','ended_utc','outcome_unknown')}
        receipt=dict(transport=tr);result=c.read(root/'result.json')
        fee,basis=c.cost(job,tr) if tr['http_status']==200 else (c.read(root/'authorization.json')['probe_max_reservation_cny'],'unknown_usage_reservation')
        c.require(abs(fee-result['probe_cost_or_reserved_cny'])<1e-10,'Short probe fee')
        values={}
    else:
        receipt=raw;tr=raw['transport'];c.require(raw['job_sha256']==c.fingerprint(job),'Real probe body binding')
        fee,basis=c.cost(job,tr);result=c.read(root/'summary.json')
        c.require(abs(fee-result['additional_cost_or_reserved_cny'])<1e-10,'Real probe fee')
        values={job['request_id']:dict(job=job,receipt=raw,receipt_path=(root/'receipt.json').relative_to(c.ROOT).as_posix(),native=c.pilot.strict_json(tr['body_text']))} if tr['http_status']==200 else {}
    attempt=dict(epoch=name,phase='single_probe',request_id=job['request_id'],role=job['role'],attempt=1,account=raw['account'],
        http_status=tr['http_status'],charge_cny=fee,charge_basis=basis,started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],
        receipt=(root/'receipt.json').relative_to(c.ROOT).as_posix(),sha256=c.file_hash(root/'receipt.json'))
    return values,[attempt]

def collect(include_final=True):
    values={};attempts=[]
    def merge(v,a):
        c.require(not (set(values)&set(v)),'A successful canonical request was regenerated across continuations')
        values.update(v);attempts.extend(a)
    for root,path in [(ORIGINAL,ORIGINAL/'interruption_001/reconciled_ledger.json'),(ORIGINAL/'recovery_001',None),(ORIGINAL/'v4_completion_001',None)]:
        vv,aa,_=read_run(root,path);merge(vv,aa)
    for name,short in [('service_check_001',True),('real_request_check_001',False)]:merge(*read_single(name,short))
    previous=sum(a['charge_cny'] for a in attempts)
    c.require(abs(previous-c.read(ORIGINAL/'current_checkpoint_003.json')['whole_task_used_or_reserved_cny'])<1e-8,'Prior cumulative cost mismatch')
    if include_final and (FINAL/'live/ledger.json').exists():
        c.require(not (FINAL/'task_api.lock').exists(),'Finalization API client active')
        vv,aa,ll=read_run(FINAL);c.require(abs(ll['carry_from_prior_cny']-previous)<1e-8,'Finalization carry mismatch');merge(vv,aa)
    total=sum(a['charge_cny'] for a in attempts);c.require(total<=40,'Whole016 budget exceeded')
    return values,attempts,total

def base_labels(values,require_complete=False):
    jobs=c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl');labels={};provenance=[]
    for j in jobs:
        rid=j['request_id']
        if rid not in values:continue
        v=values[rid];c.require(j==v['job'],'Canonical base request changed')
        n=c.normalize(j,v['receipt']);c.require(n['status']=='success','Received base answer invalid; never regenerate200')
        pid=j['proposition_id'];labels.setdefault(pid,{})[j['role']]=n['verdict']
        provenance.append(dict(proposition_id=pid,role=j['role'],request_id=rid,body_sha256=c.fingerprint(j['body']),receipt=v['receipt_path'],receipt_sha256=c.file_hash(c.ROOT/v['receipt_path'])))
    if require_complete:c.require(len(labels)==601 and all(set(p)=={'v4_first','qwen'} for p in labels.values()),'Incomplete601 paired baselines')
    return labels,provenance
