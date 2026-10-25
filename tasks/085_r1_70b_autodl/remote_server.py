"""Run on user-managed Linux AutoDL only. Direct vLLM, no Docker or cloud credentials."""
import argparse,datetime,hashlib,importlib.metadata,json,os,shutil,socket,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def put(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2,sort_keys=True);f.write('\n')
def hashfile(p,git=False):
    p=Path(p);h=hashlib.sha1() if git else hashlib.sha256()
    if git:h.update(f'blob {p.stat().st_size}\0'.encode())
    with p.open('rb') as f:
        while b:=f.read(16*1024*1024):h.update(b)
    return h.hexdigest()
def verify_files(folder,expected):
    rows=[]
    for name,m in expected.items():
        p=Path(folder)/name
        if not p.is_file():raise ValueError(f'Missing checkpoint file: {name}')
        if m.get('size') is not None and p.stat().st_size!=m['size']:raise ValueError(f'Checkpoint size mismatch: {name}')
        alg='sha256' if m.get('sha256') else 'git_blob'
        actual=hashfile(p,git=alg=='git_blob')
        if actual!=m[alg]:raise ValueError(f'Checkpoint content mismatch: {name}; STOP, not exact target')
        rows.append(dict(name=name,size=p.stat().st_size,algorithm=alg,expected=m[alg],actual=actual))
    return rows
def model_files(lock):return {n:m for n,m in lock['model']['files'].items() if n.endswith('.safetensors') or n.endswith('.index.json') or n in ('config.json','generation_config.json')}
def cache_root():
    p=Path(os.getenv('HF_HOME','/root/autodl-tmp/huggingface')).resolve()
    if not p.is_relative_to(Path('/root/autodl-tmp').resolve()):raise ValueError('HF_HOME must be on /root/autodl-tmp; no system-disk model cache')
    return p
def resolve(lock,key,path,download,needed):
    if path:
        p=Path(path).expanduser().resolve()
        if not p.is_dir():raise ValueError('Supplied preinstalled path not found')
        return p,'user_preinstalled_content_verified'
    from huggingface_hub import snapshot_download
    kwargs=dict(repo_id=lock[key]['repo'],revision=lock[key]['revision'],allow_patterns=list(needed))
    try:return Path(snapshot_download(**kwargs,local_files_only=True)),'existing_pinned_cache'
    except Exception:
        if not download:raise RuntimeError(f'{key} cache not found; supply existing path or explicitly --download-if-missing')
    required=sum(m.get('size',m.get('bytes',0)) or 0 for m in needed.values())+8*1024**3
    free=shutil.disk_usage(cache_root()).free
    if free<required:raise RuntimeError(f'Insufficient data-disk free bytes: {free} < conservative required {required}; no download')
    return Path(snapshot_download(**kwargs,local_files_only=False)),'download_pinned_revision'
def command(model_path,token_path,lock,port=8000):
    return [sys.executable,'-m','vllm.entrypoints.openai.api_server','--host','127.0.0.1','--port',str(port),'--api-key','EMPTY',
        '--served-model-name',lock['model']['repo'],'--model',str(model_path),'--revision',lock['model']['revision'],
        '--tokenizer',str(token_path),'--tokenizer-revision',lock['tokenizer']['revision'],'--dtype','auto','--max-model-len','20000',
        '--gpu-memory-utilization','0.90','--tensor-parallel-size','1','--pipeline-parallel-size','1','--block-size','16','--swap-space','4',
        '--enable-prefix-caching','--num-scheduler-steps','1','--max-num-seqs','4','--enable-reasoning','--reasoning-parser','deepseek_r1',
        '--generation-config','vllm','--disable-log-requests']
def gpu():
    return subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,memory.total,memory.used,driver_version','--format=csv,noheader,nounits'],text=True).strip().splitlines()
def prepare(args):
    if sys.platform!='linux':raise RuntimeError('Remote prepare/launch is Linux AutoDL only; use --dry-run locally')
    root=cache_root();root.mkdir(parents=True,exist_ok=True);os.environ['HF_HOME']=str(root);os.environ['VLLM_USE_V1']='1'
    os.environ['HF_HUB_CACHE']=str(root/'hub');os.environ['HUGGINGFACE_HUB_CACHE']=str(root/'hub')
    os.environ['VLLM_CACHE_ROOT']=str(root.parent/'vllm-cache')
    lock=read(HERE/'identity_lock.json');version=importlib.metadata.version('vllm')
    if version!='0.9.2':raise RuntimeError(f'vLLM version {version} differs from frozen0.9.2; do not silently upgrade')
    mf=model_files(lock);tf={n:dict(sha256=v['sha256'],size=v['bytes']) for n,v in lock['official_tokenizer_files'].items()}
    run=Path(args.run_dir).resolve();run.mkdir(parents=True,exist_ok=True)
    start=now()
    try:
        mp,ms=resolve(lock,'model',args.model_path,args.download_if_missing,mf)
        tp,ts=resolve(lock,'tokenizer',args.tokenizer_path,args.download_if_missing,tf)
        mv=verify_files(mp,mf);tv=verify_files(tp,tf)
        if {p.name for p in mp.glob('*.safetensors')}!={n for n in mf if n.endswith('.safetensors')}:raise ValueError('Unexpected checkpoint shard set')
        config=read(mp/'config.json');tok=read(tp/'tokenizer_config.json')
        chat=hashlib.sha256(tok['chat_template'].encode()).hexdigest()
        if chat!=lock['chat_template_sha256']:raise ValueError('Official chat template mismatch')
    except Exception as e:
        put(run/'identity_failure.json',dict(created_utc=now(),status='IDENTITY_OR_SOURCE_UNVERIFIED_STOP',error_type=type(e).__name__,detail=str(e),model_expected=lock['model']['repo']))
        raise
    cmd=command(mp,tp,lock,args.port)
    manifest=dict(status='VERIFIED_FILES_BEFORE_SERVER_START',created_utc=now(),preparation_started_utc=start,
        model=dict(repo=lock['model']['repo'],resolved_revision=lock['model']['revision'],local_path=str(mp),source=ms,files=mv,config=config,quantization=config.get('quantization_config')),
        tokenizer=dict(repo=lock['tokenizer']['repo'],resolved_revision=lock['tokenizer']['revision'],local_path=str(tp),source=ts,files=tv,chat_template_sha256=chat),
        versions={p:importlib.metadata.version(p) for p in ('vllm','torch','transformers','tokenizers','huggingface_hub')},python=sys.version,
        gpu=gpu(),server_command=cmd,environment={k:os.environ[k] for k in ('HF_HOME','HF_HUB_CACHE','HUGGINGFACE_HUB_CACHE','VLLM_CACHE_ROOT','VLLM_USE_V1')},disk_free_bytes=shutil.disk_usage(root).free,
        identity_lock_sha256=hashfile(HERE/'identity_lock.json'),original_verifact_historical_revision_proven=False,
        instance_created_by_script=False,credentials_stored=False)
    put(run/'server_manifest.json',manifest);return run,cmd
def observe(run,pid,port):
    actual=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0');actual=[x.decode() for x in actual if x]
    expected=read(run/'server_manifest.json')['server_command']
    if actual!=expected:raise RuntimeError('Actual server process arguments differ from manifest')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def get(path):
        with opener.open(urllib.request.Request(f'http://127.0.0.1:{port}{path}',headers={'Authorization':'Bearer EMPTY'}),timeout=5) as r:return json.load(r)
    log=(run/'server.log').read_text(encoding='utf-8',errors='replace') if (run/'server.log').exists() else ''
    engine_lines=[s for s in log.splitlines() if any(k in s for k in ('Initializing a V1 LLM engine','GPU KV cache size','Maximum concurrency','quantization=','dtype='))]
    result=dict(status='SERVICE_READY_OBSERVED',observed_utc=now(),pid=pid,actual_process_command=actual,models=get('/v1/models'),version=get('/version'),gpu=gpu(),runtime_engine_log_lines=engine_lines,
        server_manifest_sha256=hashfile(run/'server_manifest.json'),server_log_sha256=hashfile(run/'server.log') if (run/'server.log').exists() else None)
    put(run/f'observation_{time.time_ns()}.json',result);return result
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','launch','observe'));p.add_argument('--dry-run',action='store_true')
    p.add_argument('--model-path');p.add_argument('--tokenizer-path');p.add_argument('--download-if-missing',action='store_true');p.add_argument('--port',type=int,default=8000)
    p.add_argument('--run-dir',default='/root/autodl-tmp/verifact085/run001');p.add_argument('--pid',type=int);args=p.parse_args()
    if args.dry_run:
        lock=read(HERE/'identity_lock.json');print(json.dumps(dict(command=command('<verified-model-path>','<verified-tokenizer-path>',lock,args.port),network_calls=0,inference_calls=0),ensure_ascii=False));return
    if args.action=='observe':print(json.dumps(observe(Path(args.run_dir),args.pid,args.port),ensure_ascii=False));return
    if args.action=='launch':
        with socket.socket() as probe:probe.bind(('127.0.0.1',args.port))
    run,cmd=prepare(args)
    if args.action=='prepare':print('Verified manifest:',run/'server_manifest.json');return
    log=(run/'server.log').open('xb');proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=os.environ.copy());log.close()
    put(run/'launch.json',dict(pid=proc.pid,started_utc=now(),command=cmd,manifest_sha256=hashfile(run/'server_manifest.json')))
    for _ in range(120):
        if proc.poll() is not None:raise RuntimeError(f'vLLM exited {proc.returncode}; inspect server.log; no model/context fallback')
        try:
            record=observe(run,proc.pid,args.port);print(json.dumps(dict(status=record['status'],pid=proc.pid,run_dir=str(run)),ensure_ascii=False));return
        except (OSError,ValueError):time.sleep(5)
    raise RuntimeError('Readiness not observed within10min; process not killed automatically; inspect log and manage instance manually')
if __name__=='__main__':main()
