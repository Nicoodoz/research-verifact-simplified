"""One ledger across SF BGE and Alibaba Judge; immutable HTTP200 and150CNY cap."""
import concurrent.futures,json,os,sys,time
from collections import Counter,deque
import common036 as c
sys.path.insert(0,str(c.ROOT/'tasks/028_traceable_claim_evidence_verification'))
import common028 as old28
api=old28.api;native=api.old.NATIVE
from verifact_research.inference.siliconflow_pool import load_accounts,balance_exhausted

def body(text,reference,role):
    if role in ('repeat','trace'):return old28.body(text,reference,role)
    b=api.old.body(text,reference,role!='baseline');b['model']=api.MODELS['qwen' if role=='peer' else 'deepseek'];return b
def bound(job):
    return api.bound(dict(job,model_key='qwen' if job.get('role')=='peer' else 'deepseek')) if job['kind']=='chat' else native.bound(job)
def charge(job,tr):
    if balance_exhausted(tr):return 0.,'unanswered_balance_error'
    return api.charge(dict(job,model_key='qwen' if job.get('role')=='peer' else 'deepseek'),tr) if job['kind']=='chat' else native.cost(job,tr)
def parse(job,tr):
    if job['kind']!='chat':return api.old.parse(job,tr)
    if job['role']=='trace':p=old28.trace_parse(tr,job)
    else:p=api.parse(tr,job['role'] in ('score','peer'))
    if p.get('model_returned') not in (None,job['body']['model']):p.update(status='invalid_core_fields',errors=p.get('errors',[])+['unexpected_model'])
    return p
def state():
    attempts=[];terminal={};exhausted=[]
    for path in sorted((c.OUT/'attempts').glob('*/request.json')):
        rq=c.read(path);job=rq['job'];rp=path.parent/'receipt.json';amount=rq['reservation_cny'];basis='unresolved_request_reservation';tr=None
        c.require(rq['body_sha256']==c.digest(job['body']),'Request body hash')
        if rp.exists():
            rec=c.read(rp);c.require(rec['request_sha256']==c.sha(path),'Receipt binding');tr=rec['transport'];amount,basis=charge(job,tr)
            if balance_exhausted(tr):exhausted.append(rq['account'])
            if tr['http_status']==200:
                c.require(job['request_id'] not in terminal,'Repeated HTTP200');terminal[job['request_id']]=dict(job=job,parsed=parse(job,tr),receipt=str(rp.relative_to(c.ROOT)),transport=tr)
        attempts.append(dict(request_id=job['request_id'],stage=rq['stage'],role=job.get('role',job['kind']),account=rq['account'],charge_cny=amount,charge_basis=basis,path=str(path.relative_to(c.ROOT)),http_status=tr['http_status'] if tr else 0,job=job))
    return attempts,terminal,set(exhausted)
def jobs_hash(jobs):return c.digest(jobs)
def run(jobs,stage,workers=8):
    c.require((c.OUT/'final_freeze_001/manifest.json').exists(),'Before models not frozen')
    attempts,terminal,exhausted=state();used=sum(a['charge_cny'] for a in attempts);counts=Counter(a['request_id'] for a in attempts);pending=[j for j in jobs if j['request_id'] not in terminal and counts[j['request_id']]<3]
    for j in jobs:
        if j['request_id'] in terminal:c.require(terminal[j['request_id']]['job']==j,'Existing job identity differs')
    accounts=[a for a in load_accounts(c.ROOT/'.env.siliconflow_pool') if a.alias not in ('account_1','account_2')];cfg=api.load_config(c.ROOT/'.env.aliyun');clients={m:old28.DirectClient(api.Config(cfg.api_key,cfg.base_url,m),timeout=180) for m in api.MODELS.values()};sf=native.HttpClient()
    for j in pending:
        if j['kind']=='chat':clients[j['body']['model']].validate(j['body'])
        else:c.require(j['body']['model'] in (api.old.baseline.EMBED_MODEL,api.old.baseline.RERANK_MODEL),'BGE model')
    lock=c.OUT/'live.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd);queue=deque(pending);inflight={};reserved=0.;done=0;stop=None;bad=deque(maxlen=50)
    def redact(v):
        if isinstance(v,str):
            for secret in [cfg.api_key,*[a.key for a in accounts]]:v=v.replace(secret,'[REDACTED]')
            return v
        if isinstance(v,dict):return {k:redact(x) for k,x in v.items()}
        return v
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while (queue and stop is None) or inflight:
                while queue and stop is None and len(inflight)<workers:
                    j=queue.popleft();reserve=bound(j)
                    if used+reserved+reserve>c.CAP:stop='task_budget150';break
                    account=None
                    if j['kind']!='chat':
                        account=next((a for a in accounts if a.alias not in exhausted),None)
                        if account is None:stop='all_enabled_SF_accounts_exhausted';break
                    number=counts[j['request_id']]+1;dest=c.OUT/'attempts'/f"{c.digest(j['request_id'])[:24]}_{number:02}";c.require(not dest.exists(),'Attempt collision');c.put(dest/'request.json',dict(created_utc=c.now(),stage=stage,account=account.alias if account else 'aliyun',job=j,attempt=number,body_sha256=c.digest(j['body']),reservation_cny=reserve,prior_task_used_or_reserved_cny=used+reserved,cap_cny=c.CAP));counts[j['request_id']]+=1;reserved+=reserve
                    fut=pool.submit(sf.send,account,j) if account else pool.submit(clients[j['body']['model']].send,j['body']);inflight[fut]=(j,dest,reserve,account.alias if account else 'aliyun')
                if not inflight:break
                ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in ready:
                    j,dest,reserve,alias=inflight.pop(fut);reserved-=reserve
                    try:tr=redact(fut.result())
                    except Exception as exc:tr=dict(http_status=0,body_text='',headers={},outcome_unknown=True,started_utc=c.now(),ended_utc=c.now(),exception_type=type(exc).__name__)
                    c.put(dest/'receipt.json',dict(request_sha256=c.sha(dest/'request.json'),transport=tr));amount,basis=charge(j,tr);used+=amount;done+=1;p=parse(j,tr);bad.append(tr['http_status']!=200 or p['status'] not in ('success','valid','valid_with_format_anomaly'))
                    if tr['http_status']==200:terminal[j['request_id']]=dict(job=j,parsed=p,receipt=str((dest/'receipt.json').relative_to(c.ROOT)),transport=tr)
                    elif balance_exhausted(tr):exhausted.add(alias)
                    if tr['http_status']!=200 and counts[j['request_id']]<3:queue.append(j)
                    if tr['http_status'] in (400,401,403,404) or p.get('model_returned') not in (None,j['body']['model']):stop='interface_or_model_error'
                    if len(bad)>=10 and sum(bad)>=10 and sum(bad)/len(bad)>.2:stop='systemic_invalid_or_transport'
                    if amount>reserve+1e-10:stop='reservation_underestimate'
                    c.put(c.OUT/'execution_status.json',dict(state='running' if stop is None else 'stopping',stage=stage,completed_this_call=done,pending=len(queue),inflight=len(inflight),used_cny=used,inflight_reserved_cny=reserved,exhausted_accounts=sorted(exhausted),reason=stop,updated_utc=c.now()))
                    if done%50==0 or stop:print(stage,done,'used',round(used,6),'pending',len(queue),'stop',stop,flush=True)
        serial=1+len(list(c.OUT.glob(f'{stage}_execution_summary_*.json')))
        c.put(c.OUT/f'{stage}_execution_summary_{serial:03}.json',dict(created_utc=c.now(),completed_now=done,terminal_for_stage=sum(j['request_id'] in terminal for j in jobs),planned=len(jobs),stop=stop,used_cny=used,exhausted_accounts=sorted(exhausted)))
        if stop:raise RuntimeError(stop)
        return state()
    finally:lock.unlink()
