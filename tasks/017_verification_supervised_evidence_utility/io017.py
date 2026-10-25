"""Receipt-only accounting and canonical prediction reconstruction for017."""
import common017 as c
from run017 import cost,bound,ALI_MODEL

def collect():
    c.require(not (c.OUT/'task_api.lock').exists(),'API process active')
    c.check(c.OUT/'preparation_001');ledger=c.read(c.OUT/'live/ledger.json');state=ledger['phases']['headroom']['jobs']
    values={};attempts=[];seen=set();norm={}
    for j in c.jsonlines(c.OUT/'preparation_001/jobs.jsonl'):
        p=state[j['request_id']];c.require(p['status']!='in_flight','Unreconciled interrupted request')
        successes=[]
        for ptr in p['receipts']:
            file=c.OUT/'live/headroom'/ptr['file'];seen.add(file.name)
            c.require(c.file_hash(file)==ptr['sha256'],'Receipt changed');r=c.read(file)
            c.require(r['request_id']==j['request_id'] and r['original_job_sha256']==c.fingerprint(j),'Receipt binding mismatch')
            body=r['actual_body'];expected=dict(j['body'],model=ALI_MODEL if r['provider']=='aliyun' else c.MODEL)
            c.require(body==expected and c.fingerprint(body)==r['actual_body_sha256'],'Actual body differs beyond registered model identifier')
            actual=dict(j,body=body);tr=r['transport'];fee,basis=cost(actual,tr)
            c.require(abs(fee-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Cost mismatch')
            attempts.append(dict(request_id=j['request_id'],proposition_id=j['proposition_id'],attempt=r['attempt'],provider=r['provider'],account=r['account'],
                http_status=tr['http_status'],charge_cny=fee,charge_basis=basis,started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],
                receipt=file.relative_to(c.ROOT).as_posix(),sha256=ptr['sha256']))
            if tr['http_status']==200:successes.append(dict(job=actual,receipt=r,path=file))
        c.require(len(successes)<=1,'Successful request repeated')
        if successes:
            value=successes[0];values[j['request_id']]=value
            norm[j['request_id']]=c.old.old14.normalize(value['job'],value['receipt'],model=value['job']['body']['model'])
    c.require(seen=={p.name for p in (c.OUT/'live/headroom').glob('receipt_*.json')},'Unbound receipt file')
    total=sum(a['charge_cny'] for a in attempts);c.require(abs(total-ledger['used_or_reserved_cny'])<1e-8 and total<=80,'Whole task accounting mismatch')
    return values,norm,attempts,total

def logical():
    values,norm,attempts,total=collect();labels={};providers={};provenance=[]
    for a in c.csvrows(c.OUT/'preparation_001/assignments.csv'):
        rid=a['request_id'];c.require(rid in norm and norm[rid]['status']=='success','Incomplete or invalid headroom results; no available-case scoring')
        key=(a['proposition_id'],a['arm'],int(a['repeat']));c.require(key not in labels,'Duplicate logical assignment')
        labels[key]=norm[rid]['verdict'];providers[key]=values[rid]['receipt']['provider']
        provenance.append(dict(a,verdict=labels[key],provider=providers[key],receipt=values[rid]['path'].relative_to(c.ROOT).as_posix()))
    return values,norm,attempts,total,labels,providers,provenance
