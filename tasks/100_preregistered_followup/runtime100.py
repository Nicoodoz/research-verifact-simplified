"""One guarded100 ledger after098 closes; shared first answers and independent repeats."""
import argparse,concurrent.futures as cf,datetime as dt,json,os,sqlite3,sys,time
import common100 as c
sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
RETRY={0,408,429,500,502,503,504}

def db():
 c.PRIVATE.mkdir(exist_ok=True,parents=True);con=sqlite3.connect(c.PRIVATE/'budget.sqlite',timeout=60);con.execute('PRAGMA journal_mode=WAL')
 con.execute('CREATE TABLE IF NOT EXISTS attempts(rid TEXT,num INTEGER,model TEXT,charge REAL,status INTEGER,folder TEXT,PRIMARY KEY(rid,num))');return con
def old_increment():
 baseline=c.read(c.OUT/'handoff_budget_snapshot.json')['previous098_cost_and_unknown_cny']
 con=sqlite3.connect(f'file:{(c.ROOT/".local_models/098_p90_native_confirmation/budget.sqlite").as_posix()}?mode=ro',uri=True);total=con.execute('SELECT COALESCE(SUM(charge),0) FROM attempts').fetchone()[0];con.close()
 assert total<=50+1e-9;return total-baseline
def summary():
 con=db();rr=con.execute('SELECT rid,num,model,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close();own=sum(r[3] for r in rr);old=old_increment()
 return dict(attempts=len(rr),HTTP200=sum(r[4]==200 for r in rr),task100_cost_or_reserved_cny=own,new098_cost_or_reserved_cny=old,total_new_cost_or_reserved_cny=own+old,hard_cap_cny=130,operating_line_cny=125)
def completed():
 con=db();rr=con.execute('SELECT rid,folder FROM attempts WHERE status=200 ORDER BY rowid').fetchall();con.close();out={}
 for rid,folder in rr:assert rid not in out;out[rid]=c.ROOT/folder
 return out
def idle(when):return when.astimezone(dt.timezone(dt.timedelta(hours=8))).hour>=22 or when.astimezone(dt.timezone(dt.timedelta(hours=8))).hour<8
def prices(model,tokens=0,cheap=False):
 if model=='deepseek-v4-flash-0731':return (1.5,4.5,.15) if cheap else (3.,9.,.3)
 assert model=='qwen3.5-27b'
 return (.6,4.8,None) if tokens<=128000 else (1.8,14.4,None)
def reserve(j):
 n=len(c.canonical(j['body']).encode())+2048;i,o,_=prices(j['body']['model'],n)
 output=8192 if j['body']['model'].startswith('deepseek') else 2048+512+32
 return (n*i+output*o)/1e6
def account(j,tr,reservation):
 if not tr or tr.get('http_status')!=200 or tr.get('outcome_unknown'):return reservation,'reserved_unknown_or_unsuccessful'
 try:
  x=json.loads(tr['body_text']);model=j['body']['model'];assert x['model']==model;u=x['usage'];n,o=u['prompt_tokens'],u['completion_tokens'];cached=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0)
  assert all(type(z) is int and z>=0 for z in [n,o,cached]) and cached<=n
  start,end=[dt.datetime.fromisoformat(tr[k]) for k in ['started_utc','ended_utc']];cheap=idle(start) and idle(end) and (end-start).total_seconds()<3600
  ip,op,cp=prices(model,n,cheap);value=(n*ip+o*op)/1e6 if cp is None else ((n-cached)*ip+cached*cp+o*op)/1e6
  assert value<=reservation+1e-9
  return value,'usage_idle' if model.startswith('deepseek') and cheap else 'usage_catalog'
 except (KeyError,ValueError,TypeError,AssertionError):return reservation,'reserved_unverified_usage'
def forecast(j,peak=False):
 ip,op,_=prices(j['body']['model'],j['input_token_forecast'],not peak);output=8192 if j['body']['model'].startswith('deepseek') else 2592
 return (j['input_token_forecast']*ip+output*op)/1e6
def reconcile():
 con=db()
 for p in (c.PRIVATE/'attempts').glob('*/request.json'):
  req=c.read(p);rp=p.parent/'receipt.json';tr=c.read(rp)['transport'] if rp.exists() else None;amount,basis=account(req['job'],tr,req['reservation_cny'])
  con.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?,?,?,?)',(req['job']['request_id'],req['attempt'],req['job']['body']['model'],amount,tr['http_status'] if tr else 0,p.parent.relative_to(c.ROOT).as_posix()))
 con.commit();con.close()
def process(j,future_reserve=0.):
 cfg=load_config(c.ROOT/'.env.aliyun');assert cfg.base_url.rstrip('/')=='https://maas.qianwenaiapi.com/compatible-mode/v1';client=DirectClient(Config(cfg.api_key,cfg.base_url,j['body']['model']),timeout=240)
 for _ in range(3):
  con=db();con.execute('BEGIN IMMEDIATE');rr=con.execute('SELECT num,status FROM attempts WHERE rid=? ORDER BY num',(j['request_id'],)).fetchall()
  if any(s==200 for _,s in rr):con.rollback();con.close();return 'cached'
  n=max([a for a,_ in rr],default=0)+1
  if n>3:con.rollback();con.close();return 'retry_exhausted'
  amount=reserve(j);used=con.execute('SELECT COALESCE(SUM(charge),0) FROM attempts').fetchone()[0]+old_increment()
  if used+amount+future_reserve>125:con.rollback();con.close();return 'budget_stop'
  folder=c.PRIVATE/'attempts'/f"{j['request_id']}_{n}";folder.mkdir(parents=True,exist_ok=False)
  c.put(folder/'request.json',dict(job=j,attempt=n,utc=c.utc(),reservation_cny=amount,prior_new_used_or_reserved_cny=used,future_confirmation_reserve_cny=future_reserve,hard_new_cap_cny=130,operating_line_cny=125,endpoint=cfg.base_url))
  con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',(j['request_id'],n,j['body']['model'],amount,0,folder.relative_to(c.ROOT).as_posix()));con.commit();con.close();start=time.monotonic()
  try:tr=client.send(j['body'])
  except Exception as exc:tr=dict(http_status=0,body_text='',outcome_unknown=True,error_type=type(exc).__name__,started_utc=c.utc(),ended_utc=c.utc())
  tr['elapsed_seconds']=time.monotonic()-start;c.put(folder/'receipt.json',dict(request_sha256=c.sha(folder/'request.json'),transport=tr));charge,basis=account(j,tr,amount)
  c.put(folder/'accounting.json',dict(cost_or_reserved_cny=charge,basis=basis,reservation_cny=amount));con=db();con.execute('UPDATE attempts SET charge=?,status=? WHERE rid=? AND num=?',(charge,tr['http_status'],j['request_id'],n));con.commit();con.close()
  if tr['http_status']==200:
   if basis=='reserved_unverified_usage':raise RuntimeError('Model/usage not verified; full reserve retained')
   return 'success'
  if tr['http_status'] not in RETRY:raise RuntimeError('Nonretryable HTTP '+str(tr['http_status']))
  if n<3:time.sleep(3*2**(n-1))
 return 'retry_exhausted'
def phase_jobs(mode):
 branch=c.read(c.OUT/'branch_decision.json');assert branch['098_complete']
 if mode=='cross_model_confirmation':
  assert branch['branch']=='cross_model';return c.lines(c.PRIVATE/'all_cross_model_jobs.jsonl'),0.
 assert branch['branch']=='evidence'
 jobs=c.lines(c.PRIVATE/'all_evidence_jobs.jsonl')
 if mode=='development':
  reserve_future=max(x['confirmation_max_output_no_cache_cny'] for x in c.read(c.OUT/'budget_plan.json')['chosen']['candidate_paths'].values())
  return [j for j in jobs if j['stage']=='development'],reserve_future
 decision=c.read(c.OUT/'development_decision.json');winner=decision['winner'];assert winner is not None,'All candidates rejected: do not run confirmation'
 arms=['O','C',winner]+(['S24'] if winner=='L24' else []);rep=['O',winner]+(['S24'] if winner=='L24' else [])
 return [j for j in jobs if j['stage']=='confirmation' and j['arm'] in (rep if j['repeat'] else arms)],0.
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['development','confirmation','cross_model_confirmation','status']);p.add_argument('--workers',type=int,default=4);args=p.parse_args()
 if args.mode=='status':print(c.canonical(summary()));return
 for name in ['execution_freeze.json','runtime_analysis_freeze.json']:
  for rel,h in c.read(c.OUT/name)['files'].items():assert c.sha(c.ROOT/rel)==h,rel
 assert not (c.ROOT/'.local_models/098_p90_native_confirmation/run.lock').exists(),'No simultaneous paid098/100'
 jobs,future=phase_jobs(args.mode);unique={}
 # Rotate within each ID. Aliases share one first answer, never across repeat slots.
 for j in sorted(jobs,key=lambda j:(j['repeat'],c.digest('100/send/'+j['id']),c.digest(j['id']+'/'+j['arm']))):unique.setdefault(j['request_id'],j)
 jobs=list(unique.values());lock=c.PRIVATE/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 try:
  reconcile();done=completed();todo=[j for j in jobs if j['request_id'] not in done];peak=not idle(dt.datetime.now(dt.timezone.utc))
  if peak and future:future*=2
  bound=summary()['total_new_cost_or_reserved_cny']+sum(forecast(j,peak) for j in todo)+future
  assert bound<=125,('Full remaining phase plus confirmation reserve exceeds125 at current tariff',bound)
  print(c.canonical(dict(phase=args.mode,logical_jobs=len(phase_jobs(args.mode)[0]),unique_jobs=len(jobs),remaining=len(todo),complete_phase_forecast_plus_future=bound)),flush=True)
  active={};index=0;stop=False;last=time.monotonic()
  with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
   while (index<len(todo) and not stop) or active:
    now_peak=not idle(dt.datetime.now(dt.timezone.utc))
    if now_peak and not peak:
     peak=True;future*=2
     remaining_bound=summary()['total_new_cost_or_reserved_cny']+sum(forecast(j,True) for j in todo[index:])+future
     print(c.canonical(dict(tariff_changed_to_peak=True,remaining_complete_bound=remaining_bound)),flush=True)
     if remaining_bound>125:stop=True;print('tariff_change_full_remaining_budget_stop',flush=True)
    while index<len(todo) and not stop and len(active)<args.workers:
     j=todo[index];index+=1;active[pool.submit(process,j,future)]=j
    if not active:break
    ready,_=cf.wait(active,timeout=2,return_when=cf.FIRST_COMPLETED)
    for f in ready:
     j=active.pop(f);result=f.result()
     if result in ['budget_stop','retry_exhausted']:stop=True;print(result,j['request_id'],flush=True)
    if time.monotonic()-last>=30:print(c.canonical(dict(phase=args.mode,progress=summary(),queued=len(todo)-index,active=len(active))),flush=True);last=time.monotonic()
  done=completed();print(c.canonical(dict(finished=True,requested=len(jobs),success=sum(j['request_id'] in done for j in jobs),ledger=summary())),flush=True)
 finally:lock.unlink()
if __name__=='__main__':main()
