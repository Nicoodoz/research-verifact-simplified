"""Single30yuan transaction ledger; finite retries and no successful-answer retry."""
import concurrent.futures as cf,datetime as dt,json,os,sqlite3,sys,time,argparse
import common101 as c
sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
RETRY={0,408,429,500,502,503,504}
def db():
 c.PRIVATE.mkdir(parents=True,exist_ok=True);con=sqlite3.connect(c.PRIVATE/'budget.sqlite',timeout=60);con.execute('PRAGMA journal_mode=WAL')
 con.execute('CREATE TABLE IF NOT EXISTS attempts(rid TEXT,num INTEGER,arm TEXT,charge REAL,status INTEGER,folder TEXT,PRIMARY KEY(rid,num))');return con
def summary():
 con=db();rr=con.execute('SELECT rid,num,arm,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close()
 return dict(attempts=len(rr),HTTP200=sum(r[4]==200 for r in rr),retries=sum(r[1]>1 for r in rr),used_or_reserved_cny=sum(r[3] for r in rr),hard_cap_cny=30)
def completed():
 con=db();rr=con.execute('SELECT rid,folder FROM attempts WHERE status=200 ORDER BY rowid').fetchall();con.close();out={}
 for rid,folder in rr:assert rid not in out;out[rid]=c.ROOT/folder
 return out
def reserve(j):return ((len(c.canonical(j['body']).encode('utf-8'))+2048)*3+j['body']['max_tokens']*9)/1e6
def idle(t):return t.astimezone(dt.timezone(dt.timedelta(hours=8))).hour>=22 or t.astimezone(dt.timezone(dt.timedelta(hours=8))).hour<8
def account(j,tr,bound):
 if not tr or tr.get('http_status')!=200 or tr.get('outcome_unknown'):return bound,'unknown_or_unsuccessful_reserved'
 try:
  response=json.loads(tr['body_text']);assert response['model']==c.MODEL
  u=response['usage'];n,o=u['prompt_tokens'],u['completion_tokens'];cached=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0)
  assert all(type(v) is int and v>=0 for v in [n,o,cached]) and cached<=n
  s,e=[dt.datetime.fromisoformat(tr[k]) for k in ['started_utc','ended_utc']];cheap=idle(s) and idle(e) and (e-s).total_seconds()<3600
  value=((n-cached)*3+cached*.3+o*9)/1e6*(.5 if cheap else 1)
  assert value<=bound+1e-9
  return value,'usage_idle' if cheap else 'usage_peak'
 except (KeyError,ValueError,TypeError,AssertionError):return bound,'usage_unverified_reserved'
def process(j):
 cfg=load_config(c.ROOT/'.env.aliyun');assert cfg.base_url.rstrip('/')==c.ENDPOINT
 client=DirectClient(Config(cfg.api_key,cfg.base_url,c.MODEL),timeout=180)
 for _ in range(3):
  con=db();con.execute('BEGIN IMMEDIATE');rr=con.execute('SELECT num,status FROM attempts WHERE rid=? ORDER BY num',(j['request_id'],)).fetchall()
  if any(s==200 for n,s in rr):con.rollback();con.close();return 'cached'
  n=max([n for n,s in rr],default=0)+1
  if n>3:con.rollback();con.close();return 'retry_exhausted'
  bound=reserve(j);used=con.execute('SELECT COALESCE(SUM(charge),0) FROM attempts').fetchone()[0]
  if used+bound>c.CAP:con.rollback();con.close();return 'budget_stop'
  folder=c.PRIVATE/'attempts'/f"{j['request_id']}_{n}";folder.mkdir(parents=True,exist_ok=False)
  c.put(folder/'request.json',dict(job=j,attempt=n,utc=c.utc(),reservation_cny=bound,prior_used_or_reserved_cny=used,hard_cap_cny=30,endpoint=cfg.base_url))
  con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',(j['request_id'],n,j['arm'],bound,0,folder.relative_to(c.ROOT).as_posix()));con.commit();con.close();start=time.monotonic()
  try:tr=client.send(j['body'])
  except Exception as exc:tr=dict(http_status=0,body_text='',outcome_unknown=True,error_type=type(exc).__name__,started_utc=c.utc(),ended_utc=c.utc())
  tr['elapsed_seconds']=time.monotonic()-start;c.put(folder/'receipt.json',dict(request_sha256=c.sha(folder/'request.json'),transport=tr))
  charge,basis=account(j,tr,bound);c.put(folder/'accounting.json',dict(cost_or_reserved_cny=charge,basis=basis,reservation_cny=bound))
  con=db();con.execute('UPDATE attempts SET charge=?,status=? WHERE rid=? AND num=?',(charge,tr['http_status'],j['request_id'],n));con.commit();con.close()
  if tr['http_status']==200:
   if basis=='usage_unverified_reserved':raise RuntimeError('Unverified model/usage; reservation retained')
   return 'success'
  if tr['http_status'] not in RETRY:raise RuntimeError('Nonretryable HTTP '+str(tr['http_status']))
  if n<3:time.sleep(3*2**(n-1))
 return 'retry_exhausted'
def run(phase,workers=4):
 for rel,h in c.read(c.OUT/'execution_freeze.json')['files'].items():assert c.sha(c.ROOT/rel)==h,rel
 if phase=='confirmation':
  for rel,h in c.read(c.OUT/'trigger_freeze.json')['files'].items():assert c.sha(c.ROOT/rel)==h,rel
 jobs=c.lines(c.PRIVATE/(phase+'_jobs.jsonl'));done=completed();todo=[j for j in jobs if j['request_id'] not in done]
 todo=sorted(todo,key=lambda j:(j['repeat'],c.digest('101/send/v1/'+j['id']),c.digest(j['id']+'/'+j['arm'])))
 lock=c.PRIVATE/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 try:
  print(c.canonical(dict(phase=phase,remaining=len(todo),ledger=summary())),flush=True)
  index=0;active={};stop=False;last=time.monotonic()
  with cf.ThreadPoolExecutor(max_workers=workers) as pool:
   while (index<len(todo) and not stop) or active:
    while index<len(todo) and not stop and len(active)<workers:
     j=todo[index];index+=1;active[pool.submit(process,j)]=j
    if not active:break
    ready,_=cf.wait(active,timeout=2,return_when=cf.FIRST_COMPLETED)
    for f in ready:
     j=active.pop(f)
     try:status=f.result()
     except Exception as exc:stop=True;status='blocked_'+str(exc)
     if status not in ['success','cached']:stop=True;print(c.canonical(dict(status=status,id=j['id'])),flush=True)
    if time.monotonic()-last>=25:print(c.canonical(dict(phase=phase,queued=len(todo)-index,active=len(active),ledger=summary())),flush=True);last=time.monotonic()
  done=completed();result=dict(phase=phase,logical_jobs=len(jobs),completed=sum(j['request_id'] in done for j in jobs),ledger=summary());print(c.canonical(result),flush=True)
  assert result['completed']==len(jobs),'Phase incomplete; do not analyze partial target quality'
 finally:lock.unlink()
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['development','baseline','confirmation','status']);ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
 if args.phase=='status':print(c.canonical(summary()))
 else:run(args.phase,args.workers)
