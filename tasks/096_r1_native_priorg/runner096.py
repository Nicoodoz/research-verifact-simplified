"""Own096 append-only R1 runner; no network at import or dry-run.

Runtime authorization, actual GPU wall-clock budget, manifest and local request
fingerprints are checked BEFORE even /models. No old085 runner is invoked.
"""
import concurrent.futures,datetime,json,time,os,re,urllib.request,urllib.error,urllib.parse,threading,sys
import common096 as c
sys.path.insert(0,str(c.ROOT/'tasks/085_r1_70b_model_swap'))
from parse_r1 import ParserProfile,parse
RETRY={0,408,429,500,502,503,504}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('redirects forbidden')

def aware(s):
    v=datetime.datetime.fromisoformat(s)
    if v.tzinfo is None:raise ValueError('timezone required')
    return v

def validate_runtime(path,clock=None):
    cfg=c.read(path);clock=clock or datetime.datetime.now(datetime.timezone.utc)
    assert cfg.get('service_ready_confirmed_by_user') is True and cfg.get('execute_r1_authorized') is True,'WAIT_FOR_USER_SERVICE_READY: no network authorized'
    frozen=c.read(c.OUT/'offline_freeze.json')
    for rel,hh in frozen['code_sha256'].items():assert c.sha(c.ROOT/rel)==hh,('offline code changed; document technical amendment before live calls',rel)
    p=urllib.parse.urlsplit(cfg['base_url']);assert p.scheme=='http' and p.hostname in ('localhost','127.0.0.1','::1') and p.path.rstrip('/')=='/v1' and not (p.username or p.password or p.query or p.fragment),'loopback /v1 only'
    assert cfg['model']==c.MODEL and cfg['api_key']=='EMPTY'
    assert type(cfg['gpu_hourly_cny']) in (int,float) and cfg['gpu_hourly_cny']>0
    assert type(cfg['gpu_cap_cny']) in (int,float) and cfg['gpu_cap_cny']>0
    assert type(cfg['metered_api_cap_cny']) in (int,float) and cfg['metered_api_cap_cny']>=0
    start=aware(cfg['gpu_billing_start']);end=aware(cfg['stop_sending_at']);assert start<=clock<end
    assert cfg['client_concurrency'] in [2,4] and cfg['timeout_seconds']==900 and cfg['shutdown_margin_seconds']>=120
    if cfg['client_concurrency']==4:assert (c.OUT/'concurrency4_authorization.json').exists(),'4 workers requires measured preflight evidence'
    manifest_path=c.Path(cfg['private_server_manifest_path']).resolve();manifest=c.read(manifest_path)
    for k in ['model_repository','resolved_revision','revision_provider','model_path','vllm_version','torch_version','cuda_version','gpu_inventory','server_command','files']:
        assert manifest.get(k),('missing actual server metadata',k)
    assert manifest['model_repository']==c.MODEL and manifest['vllm_version']=='0.10.1.1'
    assert manifest.get('max_model_len')==20000 and manifest.get('quant_method')=='awq'
    local=c.read(c.OUT/'tokenizer_manifest.json')
    for name in ['config.json','tokenizer.json','tokenizer_config.json']:
        assert manifest['files'][name]==local['files'][name],('server config/tokenizer mismatch; do not silently use cached085 identity',name)
    cfg['_manifest_sha256']=c.sha(manifest_path)
    cfg['_authorized_runtime']=True
    budget_check(cfg,clock=clock)
    return cfg

def budget_check(cfg,clock=None,request_seconds=None):
    clock=clock or datetime.datetime.now(datetime.timezone.utc);start=aware(cfg['gpu_billing_start']);deadline=aware(cfg['stop_sending_at'])
    bound=cfg['timeout_seconds'] if request_seconds is None else request_seconds
    accrued=max(0,(clock-start).total_seconds())*cfg['gpu_hourly_cny']/3600
    # GPU is billed for whole-instance WALL time. Concurrent requests do not
    # multiply the hourly rate; the latest outstanding completion is reserved.
    reserve=(bound+cfg['shutdown_margin_seconds'])*cfg['gpu_hourly_cny']/3600
    if clock>=deadline or accrued+reserve>cfg['gpu_cap_cny']:raise RuntimeError('STOP_NEW_SENDS_GPU_CAP_OR_DEADLINE; stop Python does NOT stop AutoDL billing')
    return dict(estimated_accrued_cny=accrued,inflight_wall_reserve_cny=reserve,gpu_cap_cny=cfg['gpu_cap_cny'],billing_start=cfg['gpu_billing_start'],clock=clock.isoformat())

def request(cfg,path,body=None):
    assert cfg.get('_authorized_runtime') is True,'No runtime authorization, including read-only endpoint probes'
    budget_check(cfg)
    base=cfg['base_url'].rstrip('/');url=base+path if not path.startswith('@') else base.rsplit('/v1',1)[0]+path[1:]
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());before=time.monotonic();start=c.now()
    req=urllib.request.Request(url,data=c.encoded(body) if body is not None else None,headers={'Authorization':'Bearer EMPTY','Content-Type':'application/json'})
    try:
        with opener.open(req,timeout=cfg['timeout_seconds'] if body else 30) as r:raw=r.read();status=r.status
        unknown=False;err=None
    except urllib.error.HTTPError as e:raw=e.read();status=e.code;unknown=False;err='HTTPError'
    except (OSError,ValueError) as e:raw=b'';status=0;unknown=body is not None;err=type(e).__name__
    return raw,dict(http_status=status,outcome_unknown=unknown,error_type=err,started_utc=start,ended_utc=c.now(),elapsed_seconds=time.monotonic()-before)

def attempts(j):
    out=[]
    for p in sorted((c.PRIVATE/'attempts'/j['request_id']).glob('*/request.json'),key=lambda p:int(p.parent.name)):
        rq=c.read(p);assert rq['body_sha256']==j['body_sha256']
        rec=c.read(p.parent/'receipt.json') if (p.parent/'receipt.json').exists() else dict(http_status=None,outcome_unknown=True)
        if rec.get('response_sha256'):
            assert rec['response_sha256']==c.sha(p.parent/'response.raw') and rec['request_sha256']==c.sha(p)
        out.append((p.parent,rec))
    assert sum(r.get('http_status')==200 for _,r in out)<=1
    return out

def success(j):return next((p for p,r in attempts(j) if r.get('http_status')==200),None)

def frozen_jobs(stage):
    freeze=c.read(c.OUT/'data_freeze.json');assert c.sha(c.PRIVATE/'jobs.jsonl')==freeze['jobs_sha256']
    jobs=c.lines(c.PRIVATE/'jobs.jsonl')
    for j in jobs:assert c.digest(j['body'])==j['body_sha256'] and set(json.loads(j['body']['messages'][1]['content']))=={'proposition','reference'}
    if stage=='technical':
        plan=c.read(c.OUT/'technical_preflight_plan.json');ids=set(plan['calibration_request_ids']);return [c.read(c.PRIVATE/'fictional_job.json')]+[j for j in jobs if j['request_id'] in ids]
    if stage in ['main','stress']:
        selection=c.read(c.OUT/'live_plan_selection.json');ids=set(selection[stage+'_ids']);jobs=[j for j in jobs if j['id'] in ids]
    else:jobs=[j for j in jobs if j['stage']==stage]
    return jobs

def probe(cfg,path,name):
    raw,receipt=request(cfg,path);folder=c.PRIVATE/'service_probes'/str(time.time_ns());folder.mkdir(parents=True)
    (folder/'response.raw').write_bytes(raw);c.put(folder/'receipt.json',dict(receipt,kind=name,response_sha256=c.sha(folder/'response.raw')))
    return raw,receipt

def ensure_identity(cfg):
    raw,receipt=probe(cfg,'/models','models');assert receipt['http_status']==200,'R1 endpoint unavailable'
    cards=json.loads(raw)['data'];assert len(cards)==1 and cards[0]['id']==c.MODEL and cards[0].get('max_model_len')==20000
    c.append(c.OUT/'gpu_runtime_ledger.jsonl',dict(event='models_identity_observed',utc=c.now(),manifest_sha256=cfg['_manifest_sha256'],models_sha256=c.key('',raw.decode()),**budget_check(cfg),remote_weight_bytes_verified=False))

def server_idle(cfg):
    for _ in range(2):
        raw,h=probe(cfg,'@/health','recovery_health');raw,m=probe(cfg,'@/metrics','recovery_metrics')
        if h['http_status']!=200 or m['http_status']!=200:return False
        text=raw.decode(errors='replace');values=[]
        for metric in ['num_requests_running','num_requests_waiting']:
            found=re.findall(r'^vllm:'+metric+r'(?:\{[^\n]*\})?\s+([0-9.eE+-]+)\s*$',text,re.M)
            if not found or any(float(v)!=0 for v in found):return False
            values.extend(found)
        time.sleep(2)
    c.append(c.OUT/'gpu_runtime_ledger.jsonl',dict(event='unknown_recovery_server_idle_confirmed',utc=c.now(),**budget_check(cfg)))
    return True

def invoke_once(j,cfg):
    old=attempts(j)
    if success(j):return success(j),200
    num=len(old)+1;assert num<=3,'finite recovery exhausted'
    budget=budget_check(cfg);folder=c.PRIVATE/'attempts'/j['request_id']/str(num);folder.mkdir(parents=True,exist_ok=False)
    c.put(folder/'request.json',dict(request_id=j['request_id'],body_sha256=j['body_sha256'],job=j,attempt=num,utc=c.now(),gpu_budget_at_send=budget))
    raw,receipt=request(cfg,'/chat/completions',j['body'])
    with (folder/'response.raw').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    c.put(folder/'receipt.json',dict(receipt,request_sha256=c.sha(folder/'request.json'),response_sha256=c.sha(folder/'response.raw')))
    return folder,receipt['http_status']

def run_jobs(jobs,cfg):
    lock=c.PRIVATE/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        pending=[j for j in jobs if success(j) is None]
        if any(attempts(j) and attempts(j)[-1][1].get('outcome_unknown') for j in pending):
            if not server_idle(cfg):raise RuntimeError('UNRESOLVED_PRIOR_INFLIGHT; no repeat while server state unknown')
        with concurrent.futures.ThreadPoolExecutor(max_workers=cfg['client_concurrency']) as pool:
            # Small complete batches drain on an error before any recovery.
            while pending:
                batch=pending[:cfg['client_concurrency']];pending=pending[len(batch):];futures=[pool.submit(invoke_once,j,cfg) for j in batch];failed=[]
                for j,f in zip(batch,futures):
                    folder,status=f.result()
                    if status!=200:failed.append((j,status))
                    else:
                        try:n=c.read(folder/'response.raw')
                        except (ValueError,UnicodeDecodeError):n={}
                        if isinstance(n,dict) and n.get('model') not in (None,c.MODEL):raise RuntimeError('successful unexpected-model answer retained; stop')
                if failed:
                    if any(s not in RETRY for _,s in failed):raise RuntimeError('Persistent non-retryable service condition')
                    if any(s==0 for _,s in failed) and not server_idle(cfg):raise RuntimeError('UNKNOWN_INFLIGHT_NOT_RESOLVED; saved, no immediate retry')
                    time.sleep(2);pending=[j for j,_ in failed]+pending
    finally:lock.unlink(missing_ok=True)

def execute(stage,runtime):
    assert not (c.PRIVATE/'run.lock').exists(),'R1 process already active; no duplicate runner or probe'
    cfg=validate_runtime(runtime);ensure_identity(cfg)
    if stage!='technical':
        assert (c.OUT/'live_parser_profile.json').exists() and (c.OUT/'live_plan_selection.json').exists(),'preflight/one-time size decision required'
    if stage in ['main','stress']:assert (c.OUT/'adapted_parameters.json').exists(),'freeze calibrated model before evaluation-label join'
    start=time.monotonic();jobs=frozen_jobs(stage);run_jobs(jobs,cfg)
    c.append(c.OUT/'gpu_runtime_ledger.jsonl',dict(event='stage_inference_saved',stage=stage,utc=c.now(),N=len(jobs),wall_seconds=time.monotonic()-start,**budget_check(cfg,request_seconds=0)))
    print('R1_STAGE_SAVED',stage,len(jobs))
