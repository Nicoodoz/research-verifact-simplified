"""One task-wide durable ledger, bounded concurrency and receipt-first accounting."""
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from decimal import Decimal
from pathlib import Path
import argparse
import os
import json
import time
import common016 as c

RETRYABLE={408,429,500,502,503,504}

def next_status(tr,attempts,unknowns,transient):
    if c.balance_exhausted(tr):return 'pending' if attempts<5 else 'failed_balance'
    if tr['http_status']==200:return 'received'
    if tr['http_status']==0:return 'retry' if unknowns<2 and attempts<5 else 'failed_unknown'
    if tr['http_status'] in RETRYABLE:return 'retry' if transient<3 and attempts<5 else 'failed_service'
    return 'configuration_pause'

def execute(jobfile,workers=4,limit=None):
    c.require(1<=workers<=4,'Invalid workers')
    auth=c.read(c.OUT/'authority_001.json')
    c.require(auth['approved'] is True and auth['task_cap_cny']>0,'Explicit whole-task budget approval required')
    c.check_hashes(auth['execution_sha256'])
    jobfile=Path(jobfile).resolve();c.require(jobfile.is_relative_to(c.OUT),'Jobs outside 016')
    cohort=jobfile.relative_to(c.OUT).parts[0];c.patient_ids(cohort)
    c.check_manifest(jobfile.parent)
    jobs=c.jsonlines(jobfile);kinds={j['kind'] for j in jobs}
    c.require(len(kinds)==1 and len({j['request_id'] for j in jobs})==len(jobs),'Nonunique or mixed jobs')
    kind=next(iter(kinds));phase=cohort+'_'+kind
    for j in jobs:
        c.require(j['body']['model'] in {'chat':{c.V4,c.QWEN},'embedding':{c.baseline.EMBED_MODEL},'rerank':{c.baseline.RERANK_MODEL}}[kind],'Unexpected model')
    accounts=[a for a in c.load_accounts(c.ROOT/'.env.siliconflow_pool',environ={}) if int(a.alias.split('_')[-1])>=2]
    c.require(accounts and accounts[0].alias=='account_2','Dedicated account_2 required')
    live=c.OUT/'live';live.mkdir(exist_ok=True);folder=live/phase;folder.mkdir(exist_ok=True)
    spec=dict(phase=phase,jobfile=jobfile.relative_to(c.ROOT).as_posix(),jobs_sha256=c.file_hash(jobfile),
        preparation_manifest_sha256=c.file_hash(jobfile.parent/'manifest.json'),authority_sha256=c.file_hash(c.OUT/'authority_001.json'),
        task_cap_cny=auth['task_cap_cny'],endpoints=c.NATIVE.ENDPOINTS,driver_sha256=c.file_hash(Path(__file__)))
    runid=c.fingerprint(spec);ledgerpath=live/'ledger.json';lock=c.OUT/'task_api.lock'
    with lock.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    try:
        ledger=c.read(ledgerpath) if ledgerpath.exists() else dict(authority_sha256=spec['authority_sha256'],cap_cny=auth['task_cap_cny'],
            used_or_reserved_cny=0.,exhausted_accounts=[],phases={})
        c.require(ledger['authority_sha256']==spec['authority_sha256'] and ledger['cap_cny']==auth['task_cap_cny'],'Budget authority changed')
        if (folder/'manifest.json').exists():c.require(c.read(folder/'manifest.json')==spec,'Phase inputs changed')
        else:c.write_json(folder/'manifest.json',spec)
        if phase not in ledger['phases']:
            ledger['phases'][phase]=dict(run_id=runid,jobs={j['request_id']:dict(status='pending',attempts=0,unknowns=0,transient=0,receipts=[]) for j in jobs})
        state=ledger['phases'][phase];c.require(state['run_id']==runid and not ledger.get('bound_violation'),'Invalid state')
        def checkpoint():c.save(ledgerpath,ledger)
        def finish(i,j,r):
            p=state['jobs'][j['request_id']];tr=r['transport']
            c.require(r['run_id']==runid and r['job_sha256']==c.fingerprint(j) and r['attempt']==p['attempts'],'Receipt mismatch')
            charge,basis=c.cost(j,tr)
            ledger['used_or_reserved_cny']=float(Decimal(str(ledger['used_or_reserved_cny']))-Decimal(str(c.bound(j)))+Decimal(str(charge)))
            if tr['http_status']==0:p['unknowns']+=1
            if tr['http_status'] in RETRYABLE:p['transient']+=1
            p['status']=next_status(tr,p['attempts'],p['unknowns'],p['transient'])
            p['next_eligible_epoch']=time.time()+20 if p['status']=='retry' else 0
            if c.balance_exhausted(tr) and r['account'] not in ledger['exhausted_accounts']:ledger['exhausted_accounts'].append(r['account'])
            path=folder/f'receipt_{i+1:06d}_{p["attempts"]:02d}.json'
            p['receipts'].append(dict(file=path.name,sha256=c.file_hash(path),charge_cny=charge,charge_basis=basis))
            if charge>c.bound(j)+1e-10:ledger['bound_violation']=True
            checkpoint()
        for i,j in enumerate(jobs):
            p=state['jobs'][j['request_id']]
            for ptr in p['receipts']:c.require(c.file_hash(folder/ptr['file'])==ptr['sha256'],'Existing receipt changed')
            if p['status']=='in_flight':
                path=folder/f'receipt_{i+1:06d}_{p["attempts"]:02d}.json'
                if path.exists():finish(i,j,c.read(path))
                else:
                    p['unknowns']+=1;p.setdefault('unreceipted',[]).append(dict(attempt=p['attempts'],reservation=c.bound(j)))
                    p['status']='retry' if p['unknowns']<2 and p['attempts']<5 else 'failed_unknown';p['next_eligible_epoch']=time.time()+20
        checkpoint();client=c.NATIVE.HttpClient()
        def send(i,j,a,attempt):
            started=c.now()
            try:tr=client.send(a,j)
            except Exception:tr=dict(http_status=0,body_text='',headers={},outcome_unknown=True,started_utc=started,ended_utc=c.now())
            text=c.canonical(tr)
            for account in accounts:text=text.replace(json.dumps(account.key,ensure_ascii=False)[1:-1],'[REDACTED_API_KEY]')
            return dict(run_id=runid,request_id=j['request_id'],job_sha256=c.fingerprint(j),account=a.alias,attempt=attempt,transport=json.loads(text))
        sent=0;last_print=time.monotonic();budget_halt=False
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures={}
            while True:
                budget_halt=False
                halt=ledger.get('bound_violation') or any(p['status']=='configuration_pause' for p in state['jobs'].values())
                account=next((a for a in accounts if a.alias not in ledger['exhausted_accounts']),None)
                eligible=[(i,j) for i,j in enumerate(jobs) for p in [state['jobs'][j['request_id']]]
                    if p['status'] in ('pending','retry') and p.get('next_eligible_epoch',0)<=time.time()]
                if not halt and account and (limit is None or sent<limit):
                    for i,j in eligible:
                        if len(futures)>=workers or (limit is not None and sent>=limit):break
                        if ledger['used_or_reserved_cny']+c.bound(j)>ledger['cap_cny']:
                            budget_halt=True;break
                        p=state['jobs'][j['request_id']]
                        p.update(status='in_flight',attempts=p['attempts']+1,account=account.alias,started_utc=c.now())
                        ledger['used_or_reserved_cny']+=c.bound(j);checkpoint()
                        futures[pool.submit(send,i,j,account,p['attempts'])]=(i,j);sent+=1
                if not futures:
                    waiting=any(p['status']=='retry' for p in state['jobs'].values())
                    if waiting and not halt and account and not budget_halt and (limit is None or sent<limit):time.sleep(1);continue
                    break
                completed,_=wait(futures,timeout=1,return_when=FIRST_COMPLETED)
                for fut in completed:
                    i,j=futures.pop(fut);r=fut.result()
                    c.write_json(folder/f'receipt_{i+1:06d}_{r["attempt"]:02d}.json',r);finish(i,j,r)
                if time.monotonic()-last_print>=30:
                    print(phase,'received',sum(p['status']=='received' for p in state['jobs'].values()),'/',len(jobs),
                        'task_budget',round(ledger['used_or_reserved_cny'],4),flush=True);last_print=time.monotonic()
        counts={s:sum(p['status']==s for p in state['jobs'].values()) for s in sorted({p['status'] for p in state['jobs'].values()})}
        summary=dict(updated_utc=c.now(),phase=phase,status_counts=counts,complete=counts.get('received',0)==len(jobs),
            task_used_or_reserved_cny=ledger['used_or_reserved_cny'],task_cap_cny=ledger['cap_cny'],budget_halt=budget_halt)
        c.save(folder/'summary.json',summary);print(c.canonical(summary),flush=True)
    finally:lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('jobs',type=Path);p.add_argument('--workers',type=int,default=4);p.add_argument('--limit',type=int)
    a=p.parse_args();execute(a.jobs,a.workers,a.limit)
