"""Load receipted native outputs, checking every exact input and terminal answer."""
import common020 as c

def load_phase(stage):
    prep=c.job_preparation(stage);c.check_manifest(prep)
    jobs=c.jsonlines(prep/'jobs.jsonl');ledger=c.read(c.OUT/'live_ledger.json')
    state=ledger['phases'].get(stage,{}).get('jobs',{});values={};attempts=[]
    for j in jobs:
        p=state.get(j['request_id'],{});success=[]
        for ptr in p.get('receipts',[]):
            path=c.OUT/ptr['file'];c.require(c.file_hash(path)==ptr['sha256'],'Receipt modified')
            r=c.read(path);c.require(r['request_id']==j['request_id'] and r['job_sha256']==c.fingerprint(j),'Request binding')
            expected=dict(j['body'])
            if r['provider']=='aliyun':
                c.require(j['kind']=='chat','Unregistered Alibaba BGE');expected['model']=c.ALI_MODEL
            c.require(r['actual_body']==expected and r['actual_body_sha256']==c.fingerprint(expected),'Actual request changed')
            cost,basis=c.charge(dict(j,body=expected),r['transport'])
            c.require(abs(cost-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Cost mismatch')
            attempts.append(dict(stage=stage,request_id=j['request_id'],**ptr))
            if r['transport']['http_status']==200:success.append(r)
        c.require(len(success)<=1,'Repeated terminal HTTP200')
        if success:
            rec=success[0];parsed=c.parse(dict(j,body=rec['actual_body']),rec['transport'])
            values[j['request_id']]=dict(status='received' if parsed['status']=='success' else 'invalid',job=j,receipt=rec,parsed=parsed,native=c.prior.strict_json(rec['transport']['body_text']))
        else:values[j['request_id']]=dict(status='missing',job=j,receipt=None)
    return values,attempts
