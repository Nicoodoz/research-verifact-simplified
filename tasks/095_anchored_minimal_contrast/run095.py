"""Unified append-only runner; SQLite transaction atomically reserves all in-flight costs."""
import argparse,concurrent.futures,datetime,json,os,sqlite3,sys,time
import common095 as c
sys.path.insert(0,str(c.ROOT/'src'));sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
RETRY={0,408,429,500,502,503,504};LIMITS={'baseline':80,'method':45,'extension':35,'preflight':1}
def db():
    con=sqlite3.connect(c.PRIVATE/'budget.sqlite',timeout=60);con.execute('PRAGMA journal_mode=WAL');con.execute('CREATE TABLE IF NOT EXISTS attempts(rid TEXT, num INTEGER, phase TEXT, reserved REAL, charge REAL, status INTEGER, folder TEXT, PRIMARY KEY(rid,num))');return con
def charge(j,tr):
    try:
        n=json.loads(tr['body_text']);u=n['usage'];i=u['prompt_tokens'];o=u['completion_tokens'];cached=u.get('prompt_tokens_details',{}).get('cached_tokens',0)
        assert all(type(v)is int and v>=0 for v in [i,o,cached]) and cached<=i
        amount=((i-cached)*3+cached*.3+o*9)/1e6
        assert amount<=j['bound_cny']+1e-8
        return amount
    except (ValueError,KeyError,AssertionError,TypeError):return j['bound_cny']
def reconcile():
    con=db()
    for p in (c.PRIVATE/'attempts').glob('*/request.json'):
        r=c.read(p);j=r['job'];rp=p.parent/'receipt.json';tr=c.read(rp)['transport'] if rp.exists() else None
        con.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?,?,?,?,?)',(j['request_id'],r['attempt'],j['phase'],j['bound_cny'],charge(j,tr) if tr else j['bound_cny'],tr['http_status'] if tr else 0,p.parent.relative_to(c.ROOT).as_posix()))
    con.commit();con.close()
def summary():
    con=db();rows=con.execute('SELECT phase,COUNT(*),SUM(charge),SUM(status=200) FROM attempts GROUP BY phase').fetchall();con.close();return {p:dict(attempts=n,cost_or_reserved=cost,HTTP200=ok) for p,n,cost,ok in rows}
def process(j):
    cfg=load_config(c.ROOT/'.env.aliyun');assert '.cn-beijing.maas.aliyuncs.com/' in cfg.endpoint
    cli=DirectClient(Config(cfg.api_key,cfg.base_url,c.MODEL),timeout=240)
    for _ in range(3):
        con=db();con.execute('BEGIN IMMEDIATE')
        old=con.execute('SELECT num,status FROM attempts WHERE rid=? ORDER BY num',(j['request_id'],)).fetchall()
        if any(status==200 for _,status in old):con.rollback();con.close();return 'cached'
        attempt=max([n for n,_ in old],default=0)+1
        if attempt>3:con.rollback();con.close();raise RuntimeError('finite retries exhausted '+j['request_id'])
        used=con.execute('SELECT COALESCE(SUM(charge),0) FROM attempts').fetchone()[0];phase=con.execute('SELECT COALESCE(SUM(charge),0) FROM attempts WHERE phase=?',(j['phase'],)).fetchone()[0]
        limit=150 if attempt>1 else 130
        if used+j['bound_cny']>limit or phase+j['bound_cny']>LIMITS[j['phase']]:con.rollback();con.close();return 'budget_stop'
        folder=c.PRIVATE/'attempts'/f"{j['request_id']}_{attempt}";folder.mkdir(parents=True,exist_ok=False)
        c.put(folder/'request.json',dict(job=j,attempt=attempt,utc=c.now(),prior_task_reserved=used,prior_phase_reserved=phase,hard_cap_cny=150))
        con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?)',(j['request_id'],attempt,j['phase'],j['bound_cny'],j['bound_cny'],0,folder.relative_to(c.ROOT).as_posix()));con.commit();con.close()
        start=time.monotonic()
        try:tr=cli.send(j['body'])
        except Exception as e:tr=dict(http_status=0,body_text='',outcome_unknown=True,error_type=type(e).__name__)
        tr['client_elapsed_seconds']=time.monotonic()-start;c.put(folder/'receipt.json',dict(request_sha256=c.sha(folder/'request.json'),transport=tr))
        con=db();con.execute('UPDATE attempts SET charge=?,status=? WHERE rid=? AND num=?',(charge(j,tr),tr['http_status'],j['request_id'],attempt));con.commit();con.close()
        if tr['http_status']==200:assert json.loads(tr['body_text'])['model']==c.MODEL;return 'success'
        if tr['http_status'] not in RETRY:raise RuntimeError('nonretryable HTTP '+str(tr['http_status']))
        time.sleep(3*attempt)
    raise RuntimeError('communication retries exhausted')
def run(stage,workers):
    plan=c.read(c.OUT/'baseline_plan.json')
    for p,h in plan['sources'].items():assert c.sha(c.ROOT/p)==h,p
    frozen=c.read(c.OUT/'runner_freeze.json')
    for p,h in frozen['sources'].items():assert c.sha(c.ROOT/p)==h,p
    lock=c.PRIVATE/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        reconcile();jobs=c.lines(c.PRIVATE/(stage+'_jobs.jsonl'));con=db();success={r[0] for r in con.execute('SELECT rid FROM attempts WHERE status=200')};con.close();todo=[j for j in jobs if j['request_id'] not in success];active={};idx=0;completed=0;stop=False;last=time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while (idx<len(todo) and not stop) or active:
                while idx<len(todo) and not stop and len(active)<workers:
                    j=todo[idx];idx+=1;active[pool.submit(process,j)]=j
                ready,_=concurrent.futures.wait(active,timeout=3,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in ready:
                    active.pop(f);result=f.result();completed+=result=='success'
                    if result=='budget_stop':stop=True
                if time.monotonic()-last>45:
                    s=summary();print(stage,'new completed',completed,'queue',len(todo)-idx,'active',len(active),'ledger',s,flush=True);c.progress(stage,dict(new_completed=completed,remaining_queue=len(todo)-idx,ledger=s));last=time.monotonic()
        c.progress(stage,dict(completed_new=completed,budget_stop=stop,ledger=summary()));print('stage finished',stage,'budget_stop',stop,summary(),flush=True)
    finally:lock.unlink()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    if a.stage=='status':print(summary())
    else:run(a.stage,a.workers)
