"""Validate frozen jobs, raw receipts and cumulative accounting before offline use."""
import common016 as c

def load_phase(phase):
    c.require(not (c.OUT/'task_api.lock').exists(),'Wait for current API phase to stop')
    ledger=c.read(c.OUT/'live/ledger.json');folder=c.OUT/'live'/phase;spec=c.read(folder/'manifest.json')
    c.require(ledger['phases'][phase]['run_id']==c.fingerprint(spec),'Phase identity')
    path=c.ROOT/spec['jobfile'];c.require(c.file_hash(path)==spec['jobs_sha256'],'Jobs changed');c.check_manifest(path.parent)
    jobs=c.jsonlines(path);values={};attempts=[];seen=set()
    for job in jobs:
        p=ledger['phases'][phase]['jobs'][job['request_id']];success=[]
        for ptr in p['receipts']:
            file=folder/ptr['file'];seen.add(file.name);c.require(c.file_hash(file)==ptr['sha256'],'Receipt changed')
            r=c.read(file);tr=r['transport'];c.require(r['run_id']==c.fingerprint(spec) and r['job_sha256']==c.fingerprint(job) and r['request_id']==job['request_id'],'Receipt binding')
            charge,basis=c.cost(job,tr);c.require(abs(charge-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Cost mismatch')
            attempts.append(dict(phase=phase,request_id=job['request_id'],role=job.get('role',''),attempt=r['attempt'],account=r['account'],
                http_status=tr['http_status'],charge_cny=charge,charge_basis=basis,started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],
                receipt=file.relative_to(c.ROOT).as_posix(),sha256=ptr['sha256']))
            if tr['http_status']==200:success.append(r)
        for unknown in p.get('unreceipted',[]):
            attempts.append(dict(phase=phase,request_id=job['request_id'],role=job.get('role',''),attempt=unknown['attempt'],account=p.get('account'),
                http_status=0,charge_cny=unknown['reservation'],charge_basis='unreceipted_unknown',started_utc='',ended_utc='',receipt='',sha256=''))
        c.require(len(success)<=1,'Successful answer regenerated')
        values[job['request_id']]=dict(job=job,receipt=success[0] if success else None,
            native=c.pilot.strict_json(success[0]['transport']['body_text']) if success else None,status='received' if success else p['status'])
    c.require(seen=={p.name for p in folder.glob('receipt_*.json')},'Unbound receipt files')
    accounted=sum(ptr['charge_cny'] for st in ledger['phases'].values() for p in st['jobs'].values() for ptr in p['receipts'])
    accounted+=sum(u['reservation'] for st in ledger['phases'].values() for p in st['jobs'].values() for u in p.get('unreceipted',[]))
    c.require(abs(accounted-ledger['used_or_reserved_cny'])<1e-8 and accounted<=ledger['cap_cny'] and not ledger.get('bound_violation'),'Whole-task accounting mismatch')
    return values,attempts
