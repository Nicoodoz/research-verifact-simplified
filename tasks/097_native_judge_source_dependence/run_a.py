"""Append-only budgeted direct V4 caller. No response-content retries."""
import concurrent.futures, json, os, sqlite3, sys, time
import common097 as c
sys.path.insert(0,str(c.ROOT/'src'))
sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config, load_config

CAP=20.0;OPERATING=18.0;RETRY={0,408,429,500,502,503,504}
def db():
    c.PRIVATE.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(c.PRIVATE/'budget.sqlite',timeout=60)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS attempts(rid TEXT,num INT,arm TEXT,charge REAL,status INT,folder TEXT,PRIMARY KEY(rid,num))')
    return con
def charge(j,tr):
    try:
        if tr.get('http_status')!=200 or tr.get('outcome_unknown') is True:return j['bound_cny']
        response=json.loads(tr['body_text']);u=response['usage']
        assert response['model']==c.MODEL
        i,o=u['prompt_tokens'],u['completion_tokens'];cached=u.get('prompt_tokens_details',{}).get('cached_tokens',0)
        assert all(type(v)is int and v>=0 for v in [i,o,cached]) and cached<=i
        amount=((i-cached)*3+cached*.3+o*9)/1e6
        assert amount<=j['bound_cny']+1e-8
        return amount # busy ceiling even if idle, safe for budget
    except (KeyError,TypeError,ValueError,AssertionError):return j['bound_cny']
def reconcile():
    con=db()
    for p in (c.PRIVATE/'attempts').glob('*/request.json'):
        req=c.read(p);j=req['job'];rp=p.parent/'receipt.json';tr=c.read(rp)['transport'] if rp.exists() else None
        con.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?,?,?,?)',(j['request_id'],req['attempt'],j['arm'],charge(j,tr) if tr else j['bound_cny'],tr['http_status'] if tr else 0,p.parent.relative_to(c.ROOT).as_posix()))
    con.commit();con.close()
def summary():
    con=db();x=con.execute('SELECT COUNT(*),COALESCE(SUM(charge),0),SUM(status=200) FROM attempts').fetchone();y=con.execute('SELECT arm,COUNT(*),SUM(status=200),SUM(charge) FROM attempts GROUP BY arm').fetchall();con.close()
    return dict(attempts=x[0],busy_price_or_reserved_cny=x[1],HTTP200=x[2] or 0,by_arm={r[0]:dict(attempts=r[1],HTTP200=r[2] or 0,cost=r[3]) for r in y},unspent_to_cap=CAP-x[1])
def process(j):
    cfg=load_config(c.ROOT/'.env.aliyun')
    assert '.cn-beijing.maas.aliyuncs.com/' in cfg.endpoint
    client=DirectClient(Config(cfg.api_key,cfg.base_url,c.MODEL),timeout=240)
    for _ in range(2):
        con=db();con.execute('BEGIN IMMEDIATE')
        old=con.execute('SELECT num,status FROM attempts WHERE rid=? ORDER BY num',(j['request_id'],)).fetchall()
        if any(status==200 for _,status in old):con.rollback();con.close();return 'cached'
        n=max([z[0] for z in old],default=0)+1
        if n>2:con.rollback();con.close();return 'retry_exhausted'
        used=con.execute('SELECT COALESCE(SUM(charge),0) FROM attempts').fetchone()[0]
        if used+j['bound_cny']>OPERATING:con.rollback();con.close();return 'budget_stop'
        folder=c.PRIVATE/'attempts'/f"{j['request_id']}_{n}";folder.mkdir(parents=True,exist_ok=False)
        c.write_json(folder/'request.json',dict(job=j,attempt=n,utc=c.utc(),prior_reserved=used,operating_cap=OPERATING,hard_cap=CAP))
        con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',(j['request_id'],n,j['arm'],j['bound_cny'],0,folder.relative_to(c.ROOT).as_posix()))
        con.commit();con.close()
        begin=time.monotonic()
        try:tr=client.send(j['body'])
        except Exception as e:tr=dict(http_status=0,body_text='',outcome_unknown=True,error_type=type(e).__name__)
        tr['client_elapsed_seconds']=time.monotonic()-begin
        c.write_json(folder/'receipt.json',dict(request_sha256=c.sha(folder/'request.json'),transport=tr))
        con=db();con.execute('UPDATE attempts SET charge=?,status=? WHERE rid=? AND num=?',(charge(j,tr),tr['http_status'],j['request_id'],n));con.commit();con.close()
        if tr['http_status']==200:
            response=json.loads(tr['body_text'])
            if response.get('model')!=c.MODEL:raise RuntimeError('returned model mismatch; stop')
            return 'success'
        if tr['http_status'] not in RETRY:raise RuntimeError('nonretryable status '+str(tr['http_status']))
        time.sleep(3*n)
    return 'retry_exhausted'
def main():
    freeze=c.read(c.OUT/'a_execution_freeze.json');assert c.sha(c.PRIVATE/'a_execution_jobs.jsonl')==freeze['jobs_sha256']
    correction=c.read(c.OUT/'a_request_correction.json');assert c.sha(c.PRIVATE/'a_execution_jobs_corrected.jsonl')==correction['after_sha256']
    jobs=c.lines(c.PRIVATE/'a_execution_jobs_corrected.jsonl');assert len(jobs)==480
    lock=c.PRIVATE/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        reconcile();con=db();success={x[0] for x in con.execute('SELECT rid FROM attempts WHERE status=200')};con.close()
        todo=[j for j in jobs if j['request_id'] not in success];active={};idx=0;stop=False;last=time.monotonic();done=0
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            while (idx<len(todo) and not stop) or active:
                while idx<len(todo) and not stop and len(active)<4:
                    j=todo[idx];idx+=1;active[pool.submit(process,j)]=j
                ready,_=concurrent.futures.wait(active,timeout=3,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in ready:
                    j=active.pop(fut);result=fut.result();done+=result=='success'
                    if result=='budget_stop':stop=True
                    if result=='retry_exhausted':print('retry exhausted',j['id'],j['arm'],flush=True)
                if time.monotonic()-last>45:
                    print('progress',done,'remaining',len(todo)-idx,'active',len(active),'ledger',summary(),flush=True);last=time.monotonic()
        print('finished',done,'budget_stop',stop,'ledger',summary(),flush=True)
    finally:lock.unlink()
if __name__=='__main__':main()
