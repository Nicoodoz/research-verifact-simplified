"""Single103 budget ledger, exact successful-call skip, bounded communication recovery."""
import argparse
import concurrent.futures as cf
import json
import os
import sqlite3
import sys
import time
import common103 as c
sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config

RETRY={0,408,429,500,502,503,504}

def db():
    c.PRIVATE.mkdir(parents=True,exist_ok=True);con=sqlite3.connect(c.PRIVATE/'budget.sqlite',timeout=60)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS attempts(rid TEXT,num INTEGER,model TEXT,charge REAL,status INTEGER,folder TEXT,PRIMARY KEY(rid,num))')
    return con

def price(model,tokens):
    i,o,cache=c.PRICES[model]
    if tokens>128000 and model=='qwen3.5-27b':i,o=1.8,14.4
    if tokens>128000 and model=='qwen3.5-35b-a3b':i,o=1.6,12.8
    return i,o,cache

def charge(j,tr,reservation):
    try:
        assert tr and tr['http_status']==200 and not tr.get('outcome_unknown')
        response=json.loads(tr['body_text']);assert response['model']==j['model']
        u=response['usage'];i,o=u['prompt_tokens'],u['completion_tokens'];cached=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0)
        assert all(type(v) is int and v>=0 for v in [i,o,cached]) and cached<=i
        ip,op,cp=price(j['model'],i)
        amount=(i*ip+o*op)/1e6
        assert amount<=reservation+1e-9
        return amount,'verified_usage'
    except (KeyError,ValueError,TypeError,AssertionError,AttributeError):return reservation,'reserved_unknown_or_unverified'

def completed():
    con=db();rows=con.execute('SELECT rid,folder FROM attempts WHERE status=200 ORDER BY rowid').fetchall();con.close();out={}
    for rid,folder in rows:assert rid not in out;out[rid]=c.ROOT/folder
    return out

def summary():
    con=db();rows=con.execute('SELECT rid,num,model,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close()
    return dict(attempts=len(rows),HTTP200=sum(r[4]==200 for r in rows),used_or_reserved_cny=sum(r[3] for r in rows),hard_cap_cny=30,
                by_model={m:dict(attempts=sum(r[2]==m for r in rows),HTTP200=sum(r[2]==m and r[4]==200 for r in rows),cost_or_reserved_cny=sum(r[3] for r in rows if r[2]==m)) for m in c.MODELS})

def reconcile():
    con=db()
    for p in (c.PRIVATE/'attempts').glob('*/request.json'):
        req=c.read(p);rp=p.parent/'receipt.json';tr=c.read(rp)['transport'] if rp.exists() else None
        amount,_=charge(req['job'],tr,req['reservation_cny'])
        con.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?,?,?,?)',(req['job']['request_id'],req['attempt'],req['job']['model'],amount,tr['http_status'] if tr else 0,p.parent.relative_to(c.ROOT).as_posix()))
    con.commit();con.close()

def process(j,operating=30.):
    cfg=load_config(c.ROOT/'.env.aliyun');assert cfg.base_url.rstrip('/')==c.ENDPOINT
    client=DirectClient(Config(cfg.api_key,cfg.base_url,j['model']),timeout=240)
    for _ in range(3):
        con=db();con.execute('BEGIN IMMEDIATE');old=con.execute('SELECT num,status FROM attempts WHERE rid=? ORDER BY num',(j['request_id'],)).fetchall()
        if any(status==200 for _,status in old):con.rollback();con.close();return 'cached'
        n=max([r[0] for r in old],default=0)+1
        if n>3:con.rollback();con.close();return 'retry_exhausted'
        # Input byte upper bound may cross a higher priced tier even if actual tokens do not.
        bytes_bound=len(c.canonical(j['body']).encode('utf-8'))+2048
        ip,op,_=price(j['model'],bytes_bound)
        reservation=(bytes_bound*ip+(j['body'].get('thinking_budget',0)+j['body']['max_tokens']+32)*op)/1e6
        used=con.execute('SELECT COALESCE(SUM(charge),0) FROM attempts').fetchone()[0]
        if used+reservation>min(operating,c.CAP):con.rollback();con.close();return 'budget_stop'
        folder=c.PRIVATE/'attempts'/f"{j['request_id']}_{n}";folder.mkdir(parents=True,exist_ok=False)
        c.put(folder/'request.json',dict(job=j,attempt=n,utc=c.utc(),prior_used_or_reserved_cny=used,reservation_cny=reservation,operating_cap_cny=operating,hard_cap_cny=30,endpoint=c.ENDPOINT))
        con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',(j['request_id'],n,j['model'],reservation,0,folder.relative_to(c.ROOT).as_posix()));con.commit();con.close()
        begin=time.monotonic()
        try:tr=client.send(j['body'])
        except Exception as e:tr=dict(http_status=0,body_text='',outcome_unknown=True,error_type=type(e).__name__,started_utc=c.utc(),ended_utc=c.utc())
        tr['elapsed_seconds']=time.monotonic()-begin
        c.put(folder/'receipt.json',dict(request_sha256=c.sha(folder/'request.json'),transport=tr))
        amount,basis=charge(j,tr,reservation);c.put(folder/'accounting.json',dict(cost_or_reserved_cny=amount,basis=basis,reservation_cny=reservation))
        con=db();con.execute('UPDATE attempts SET charge=?,status=? WHERE rid=? AND num=?',(amount,tr['http_status'],j['request_id'],n));con.commit();con.close()
        if tr['http_status']==200:
            if basis!='verified_usage':raise RuntimeError('model_or_usage_unverified; stop and preserve maximum reserve')
            return 'success'
        if tr['http_status'] not in RETRY:raise RuntimeError('nonretryable_HTTP_'+str(tr['http_status'])+'_'+j['model'])
        if n<3:time.sleep(3*2**(n-1))
    return 'retry_exhausted'

def run(jobs,workers=4):
    reconcile();done=completed();todo=[j for j in jobs if j['request_id'] not in done]
    active={};index=0;stop=False;last=time.monotonic()
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        try:
            while (index<len(todo) and not stop) or active:
                while index<len(todo) and not stop and len(active)<workers:
                    j=todo[index];index+=1;active[pool.submit(process,j)]=j
                if not active:break
                ready,_=cf.wait(active,timeout=2,return_when=cf.FIRST_COMPLETED)
                for f in ready:
                    j=active.pop(f);result=f.result()
                    if result in ['budget_stop','retry_exhausted']:stop=True;print(result,j['request_id'],flush=True)
                if time.monotonic()-last>=30:
                    print(c.canonical(dict(progress=summary(),queued=len(todo)-index,active=len(active))),flush=True);last=time.monotonic()
        except BaseException:
            for f in active:f.cancel()
            raise
    done=completed();print(c.canonical(dict(finished=True,requested=len(jobs),success=sum(j['request_id'] in done for j in jobs),ledger=summary())),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','all','status']);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    if a.mode=='status':print(c.canonical(summary()));return
    freeze=c.read(c.OUT/'data_freeze.json')
    for rel,d in freeze['files'].items():assert c.sha(c.ROOT/rel)==d,rel
    jobs=c.lines(c.PRIVATE/('jobs_all.jsonl' if a.mode=='preflight' else 'jobs_selected.jsonl'))
    if a.mode=='all':
        decision=c.read(c.OUT/'api_execution_freeze.json')
        for rel,h in decision['files'].items():assert c.sha(c.ROOT/rel)==h,rel
    if a.mode=='preflight':jobs=[j for j in jobs if j['request_id'] in freeze['usage_probe_ids']]
    lock=c.PRIVATE/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:run(jobs,a.workers)
    finally:lock.unlink()

if __name__=='__main__':main()
