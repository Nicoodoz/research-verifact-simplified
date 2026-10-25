"""Canonical answers and full costs across016 providers/epochs; read-only, no GT."""
from pathlib import Path
import common016 as c
from finish_io016 import collect as collect_prior, ORIGINAL

OUT=ORIGINAL/'completion_002'
ALI_MODEL='qwen3.8-27b'

def bound(job):
    return ((len(c.canonical(job['body']).encode())+2000)*3+job['body']['max_tokens']*(12 if job['role']=='qwen' else 9))/1e6

def charge(job,tr):
    if job['body']['model']!=ALI_MODEL:return c.cost(job,tr)
    try:
        u=c.pilot.strict_json(tr['body_text'])['usage'];p=u['prompt_tokens'];o=u['completion_tokens']
        c.require(all(type(x)is int and x>=0 for x in (p,o)) and u['total_tokens']==p+o,'Usage invalid')
        return (p*3+o*12)/1e6,'Alibaba_Beijing_public_price_no_cache_discount_not_invoice'
    except (ValueError,TypeError,KeyError):return bound(job),'unknown_usage_reservation'

def collect(include_new=True):
    values,attempts,total=collect_prior()
    probe=ORIGINAL/'aliyun_real_request_check_001';c.check_manifest(probe)
    j=c.read(probe/'job.json');r=c.read(probe/'attempt_001/receipt.json');tr=r['transport'];fee,basis=charge(j,tr)
    c.require(abs(fee-c.read(probe/'summary.json')['additional_cost_or_reserved_cny'])<1e-10,'Probe charge mismatch')
    c.require(r['body_sha256']==c.fingerprint(j['body']),'Probe body mismatch')
    if tr['http_status']==200:values[j['request_id']]=dict(job=j,receipt=r,receipt_path=(probe/'attempt_001/receipt.json').relative_to(c.ROOT).as_posix())
    attempts.append(dict(epoch='aliyun_real_request_check_001',phase='single_probe',request_id=j['request_id'],role='qwen',attempt=1,
        account='aliyun_main',http_status=tr['http_status'],charge_cny=fee,charge_basis=basis,started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],
        receipt=(probe/'attempt_001/receipt.json').relative_to(c.ROOT).as_posix(),sha256=c.file_hash(probe/'attempt_001/receipt.json')))
    total+=fee;c.require(abs(total-c.read(ORIGINAL/'current_checkpoint_005.json')['whole_task_used_or_reserved_cny'])<1e-8,'Prior005 cost drift')
    if include_new and (OUT/'live/ledger.json').exists():
        c.require(not (OUT/'task_api.lock').exists(),'Active sender')
        ledger=c.read(OUT/'live/ledger.json');c.require(abs(total-ledger['carry_cny'])<1e-8,'Carry drift');own=[]
        for phase,state in ledger['phases'].items():
            prep=OUT/phase;c.check_manifest(prep);jobs=c.jsonlines(prep/'jobs.jsonl');seen=set()
            for job in jobs:
                progress=state['jobs'][job['request_id']];c.require(progress['status']!='in_flight','Unreconciled in-flight request')
                received=[]
                for ptr in progress['receipts']:
                    file=OUT/ptr['file'];seen.add(file.name);c.require(c.file_hash(file)==ptr['sha256'],'Receipt changed')
                    rec=c.read(file);t=rec['transport'];fc,bc=charge(job,t)
                    c.require(rec['job_sha256']==c.fingerprint(job) and rec['request_id']==job['request_id'],'Receipt binding')
                    c.require(rec['jobs_sha256']==c.file_hash(prep/'jobs.jsonl'),'Receipt phase binding')
                    c.require(abs(fc-ptr['charge_cny'])<1e-10 and bc==ptr['charge_basis'],'Cost binding')
                    own.append(dict(epoch='completion_002',phase=phase,request_id=job['request_id'],role=job['role'],attempt=rec['attempt'],account=rec['account'],
                        http_status=t['http_status'],charge_cny=fc,charge_basis=bc,started_utc=t['started_utc'],ended_utc=t['ended_utc'],receipt=file.relative_to(c.ROOT).as_posix(),sha256=ptr['sha256']))
                    if t['http_status']==200:received.append((rec,file))
                c.require(len(received)<=1,'Successful answer regenerated')
                if received:
                    rec,file=received[0];c.require(job['request_id'] not in values,'Duplicate successful request')
                    values[job['request_id']]=dict(job=job,receipt=rec,receipt_path=file.relative_to(c.ROOT).as_posix())
            c.require(seen=={p.name for p in (OUT/'live'/phase).glob('receipt_*.json')},'Orphan receipt')
        total+=sum(a['charge_cny'] for a in own);attempts+=own
        c.require(abs(total-ledger['used_or_reserved_cny'])<1e-8,'Whole-task accounting mismatch')
    c.require(total<=40,'Whole task exceeds40')
    keys=[(v['job'].get('role'),v['job'].get('proposition_id')) for v in values.values() if v['job']['kind']=='chat']
    c.require(len(keys)==len(set(keys)),'Canonical role/claim duplicated across suppliers')
    return values,attempts,total

def answers(values,complete=False):
    result={};provenance=[]
    original={(j['proposition_id'],j['role']):j for j in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl')}
    for rid,v in values.items():
        j=v['job']
        if j['kind']!='chat':continue
        n=c.old14.normalize(j,v['receipt'],model=j['body']['model'])
        c.require(n['status']=='success','Invalid received answer; retained, never regenerated')
        pid=j['proposition_id'];role=j['role']
        if role in ('v4_first','qwen'):
            expected=original[(pid,role)]['body'];actual=j['body']
            c.require({k:v for k,v in expected.items() if k!='model'}=={k:v for k,v in actual.items() if k!='model'},'Base body changed')
            c.require(actual['model'] in ((c.QWEN,ALI_MODEL) if role=='qwen' else (c.V4,)),'Unexpected model')
        result[(pid,role)]=n
        provenance.append(dict(proposition_id=pid,role=role,request_id=rid,provider='aliyun' if j['body']['model']==ALI_MODEL else 'siliconflow',
            body_sha256=c.fingerprint(j['body']),receipt=v['receipt_path'],receipt_sha256=c.file_hash(c.ROOT/v['receipt_path'])))
    if complete:c.require(sum(role in ('v4_first','qwen') for pid,role in result)==1202,'Incomplete601 paired baseline')
    return result,provenance
