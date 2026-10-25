"""One durable fixed V4 arbitration screen; receipt-first, cumulative budget, no answer regeneration."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import argparse
import json
import os
import time
import common015 as c

RETRYABLE={408,429,500,502,503,504}

def next_status(tr, attempts, unknowns, transient):
    if c.balance_exhausted(tr):
        return 'pending' if attempts<5 else 'failed_balance'
    if tr['http_status']==200:
        return 'received'
    if tr['http_status']==0:
        return 'retry' if unknowns<2 and attempts<5 else 'failed_unknown'
    if tr['http_status'] in RETRYABLE:
        return 'retry' if transient<3 and attempts<5 else 'failed_service'
    return 'configuration_pause'

def run(limit=None,workers=4):
    c.require(1<=workers<=4, 'Bad workers')
    manifest=c.verify_preparation()
    jobs=c.jsonlines(c.OUT/'preparation_001/jobs.jsonl')
    c.require(all(j['body']['model']==c.MODEL for j in jobs),'V4 only')
    accounts=[a for a in c.load_accounts(c.ROOT/'.env.siliconflow_pool',environ={}) if int(a.alias.split('_')[-1])>=2]
    c.require(accounts and accounts[0].alias=='account_2','Account_2 required')
    live=c.OUT/'live';live.mkdir(exist_ok=True)
    lock=c.OUT/'task_api.lock'
    with lock.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    try:
        spec=dict(preparation_sha256=c.file_hash(c.OUT/'preparation_001/manifest.json'),cap_cny=40,
            driver_sha256=c.file_hash(c.TASK/'run015.py'),endpoint='https://api.siliconflow.cn/v1/chat/completions')
        runid=c.fingerprint(spec)
        if (live/'state.json').exists():
            c.require(c.read(live/'manifest.json')==spec,'Frozen execution changed')
            state=c.read(live/'state.json')
        else:
            c.require(not list(live.iterdir()),'Nonempty new live directory')
            c.write_json(live/'manifest.json',spec)
            state=dict(run_id=runid,used_or_reserved_cny=0.,exhausted_accounts=[],
                jobs={j['request_id']:dict(status='pending',attempts=0,unknowns=0,transient=0,receipts=[]) for j in jobs})
            c.save(live/'state.json',state)
        c.require(state['run_id']==runid and not state.get('bound_violation'),'Invalid execution state')
        def finish(i,j,receipt):
            p=state['jobs'][j['request_id']]
            c.require(receipt['run_id']==runid and receipt['job_sha256']==c.fingerprint(j) and receipt['attempt']==p['attempts'],'Receipt binding')
            tr=receipt['transport'];charge,basis=c.cost(j,tr)
            state['used_or_reserved_cny']=float(Decimal(str(state['used_or_reserved_cny']))-Decimal(str(c.bound(j)))+Decimal(str(charge)))
            if tr['http_status']==0:p['unknowns']+=1
            if tr['http_status'] in RETRYABLE:p['transient']+=1
            p['status']=next_status(tr,p['attempts'],p['unknowns'],p['transient'])
            if c.balance_exhausted(tr) and receipt['account'] not in state['exhausted_accounts']:
                state['exhausted_accounts'].append(receipt['account'])
            path=live/f'receipt_{i+1:06d}_{p["attempts"]:02d}.json'
            p['receipts'].append(dict(file=path.name,sha256=c.file_hash(path),charge_cny=charge,charge_basis=basis))
            if charge>c.bound(j)+1e-10:state['bound_violation']=True
        for i,j in enumerate(jobs):
            p=state['jobs'][j['request_id']]
            for ptr in p['receipts']:c.require(c.file_hash(live/ptr['file'])==ptr['sha256'],'Receipt changed')
            if p['status']=='in_flight':
                path=live/f'receipt_{i+1:06d}_{p["attempts"]:02d}.json'
                if path.exists():finish(i,j,c.read(path))
                else:
                    p['unknowns']+=1
                    p.setdefault('unreceipted',[]).append(dict(attempt=p['attempts'],reservation=c.bound(j)))
                    p['status']='retry' if p['unknowns']<2 and p['attempts']<5 else 'failed_unknown'
        c.save(live/'state.json',state)
        client=c.HttpClient(timeout=180)
        def send(i,j,account,attempt):
            try:tr=client.send(account,j['body'])
            except Exception:tr=dict(http_status=0,body_text='',headers={},outcome_unknown=True,started_utc=c.now(),ended_utc=c.now())
            safe=c.canonical(tr)
            for a in accounts:safe=safe.replace(json.dumps(a.key,ensure_ascii=False)[1:-1],'[REDACTED_API_KEY]')
            return dict(run_id=runid,request_id=j['request_id'],job_sha256=c.fingerprint(j),account=account.alias,attempt=attempt,transport=json.loads(safe))
        sent=0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            while not state.get('bound_violation'):
                if any(p['status']=='configuration_pause' for p in state['jobs'].values()):break
                if limit is not None and sent>=limit:break
                if any(p['status']=='retry' for p in state['jobs'].values()):
                    time.sleep(20)
                    for p in state['jobs'].values():
                        if p['status']=='retry':p['status']='pending'
                pending=[(i,j) for i,j in enumerate(jobs) if state['jobs'][j['request_id']]['status']=='pending']
                if not pending:break
                account=next((a for a in accounts if a.alias not in state['exhausted_accounts']),None)
                if account is None:break
                batch=[]
                for i,j in pending[:min(workers,limit-sent) if limit is not None else workers]:
                    if state['used_or_reserved_cny']+c.bound(j)>40:break
                    p=state['jobs'][j['request_id']]
                    p.update(status='in_flight',attempts=p['attempts']+1,account=account.alias,started_utc=c.now())
                    state['used_or_reserved_cny']+=c.bound(j)
                    c.save(live/'state.json',state)
                    batch.append((i,j,account,p['attempts']))
                if not batch:break
                futures={pool.submit(send,*b):(b[0],b[1]) for b in batch}
                sent+=len(batch)
                for fut in as_completed(futures):
                    i,j=futures[fut];receipt=fut.result()
                    c.write_json(live/f'receipt_{i+1:06d}_{receipt["attempt"]:02d}.json',receipt)
                    finish(i,j,receipt);c.save(live/'state.json',state)
                n=sum(p['status']=='received' for p in state['jobs'].values())
                if n%20<workers or limit is not None:print('received',n,'budget',round(state['used_or_reserved_cny'],4),flush=True)
        counts={s:sum(p['status']==s for p in state['jobs'].values()) for s in sorted({p['status'] for p in state['jobs'].values()})}
        summary=dict(updated_utc=c.now(),status_counts=counts,used_or_reserved_cny=state['used_or_reserved_cny'],cap_cny=40,
            complete=counts.get('received')==len(jobs),bound_violation=state.get('bound_violation',False))
        c.save(live/'summary.json',summary);print(c.canonical(summary),flush=True)
    finally:
        lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int);p.add_argument('--workers',type=int,default=4)
    a=p.parse_args();run(a.limit,a.workers)
