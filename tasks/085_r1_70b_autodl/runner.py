"""A/B preflight then separately authorized formal run; append-only raw receipts."""
import argparse,concurrent.futures,time,statistics,uuid
from common import *
from provider import Transport,validate_manifest
sys.path.insert(0,str(ROOT/'tasks/085_r1_70b_model_swap'))
from parse_r1 import ParserProfile,parse
RETRY={0,408,429,500,502,503,504}
def load_jobs():
    f=read(OUT/'offline_freeze.json')
    for rel,d in f['sources'].items():assert sha(ROOT/rel)==d,rel
    for name,d in f['files'].items():assert sha(OUT/name)==d,name
    check_old();return lines(OUT/'jobs.jsonl')
def state():
    allrows=[];success={};counts={}
    for p in sorted((OUT/'attempts').glob('*/request.json')):
        req=read(p);rid=req['job']['request_id'];counts[rid]=counts.get(rid,0)+1
        meta=p.parent/'receipt.json';raw=p.parent/'response.raw';rec=read(meta) if meta.exists() else dict(http_status=None,outcome_unknown=True)
        if meta.exists():assert rec['request_sha256']==sha(p) and rec['response_sha256']==sha(raw)
        row=dict(request=req,receipt=rec,folder=p.parent.relative_to(ROOT).as_posix());allrows.append(row)
        if rec.get('http_status')==200:
            if rid in success:raise RuntimeError('Successful logical call duplicated')
            try:returned=json.loads(raw.read_bytes()).get('model')
            except (ValueError,AttributeError):returned=None
            if returned is not None and returned!=MODEL:raise RuntimeError('Saved response model mismatch; explicit investigation required')
            success[rid]=row
    return allrows,success,counts
def invoke(j,stage,transport,deadline=None,sleep=time.sleep):
    _,success,counts=state();rid=j['request_id']
    if rid in success:return success[rid]
    for n in range(counts.get(rid,0)+1,4):
        if deadline is not None and time.monotonic()+transport.timeout>deadline:raise RuntimeError('Runtime authorization reserve exhausted; no new request')
        folder=OUT/'attempts'/f'{rid}_{n}';folder.mkdir(parents=True,exist_ok=False)
        put(folder/'request.json',dict(job=j,stage=stage,attempt_no=n,created_utc=now(),retry_of=f'{rid}_{n-1}' if n>1 else None))
        result=transport.request('/chat/completions',j['body']);raw=result.pop('raw')
        write(folder/'response.raw',raw);put(folder/'receipt.json',dict(result,request_sha256=sha(folder/'request.json'),response_sha256=sha(folder/'response.raw')))
        if result['http_status']==200:
            try:envelope=json.loads(raw)
            except ValueError:envelope={}
            if isinstance(envelope,dict) and envelope.get('model') not in (None,MODEL):raise RuntimeError('Response model mismatch; do not treat alias as identity')
            return state()[1][rid]
        if result['http_status'] not in RETRY or n==3:raise RuntimeError(f"persistent/nonretryable HTTP {result['http_status']}; saved append-only")
        sleep(3*2**(n-1))
    raise RuntimeError('Attempts exhausted; no new automatic chain')
def bind_service(args):
    if not args.server_manifest or not args.server_observation:raise ValueError('Verified remote manifest and live observation required')
    m=read(args.server_manifest);o=read(args.server_observation);lock=read(TASK/'identity_lock.json')
    assert o['server_manifest_sha256']==sha(args.server_manifest)
    assert m['identity_lock_sha256']==sha(TASK/'identity_lock.json')
    validate_manifest(m,o,lock)
    p=OUT/'service_identity.json';obj=dict(manifest=m,observation=o,manifest_sha256=sha(args.server_manifest),observation_sha256=sha(args.server_observation),bound_utc=now())
    if p.exists():
        old=read(p)
        if old['manifest_sha256']!=obj['manifest_sha256'] or old['observation_sha256']!=obj['observation_sha256']:raise ValueError('Service binding changed; requires reviewed continuation, not silent swap')
    else:put(p,obj)
    transport=Transport(timeout=args.timeout)
    tr=transport.request('/models');raw=tr.pop('raw');folder=OUT/'diagnostics'/str(time.time_ns());write(folder/'models.raw',raw);put(folder/'models.json',tr)
    if tr['http_status']!=200 or MODEL not in {x['id'] for x in json.loads(raw)['data']}:raise RuntimeError('/v1/models identity unavailable or mismatch')
    return transport
def selected(jobs):
    sel=read(OLD/'preflight_selection.json');mapping={(x['id'],x['arm']):x for x in jobs}
    return [(x['role'],mapping[x['id'],x['arm']]) for x in sel['cases']]
def raw_of(row):return (ROOT/row['folder']/'response.raw').read_bytes()
def observe_envelope(raw):
    x=json.loads(raw);assert x['model']==MODEL
    c=x['choices'][0];m=c['message'];u=x.get('usage')
    assert 'reasoning_content' in m and isinstance(m['reasoning_content'],str),'reasoning parser output not observed'
    assert isinstance(m.get('content'),str) and isinstance(c.get('finish_reason'),str)
    assert isinstance(u,dict) and all(type(u.get(k))is int and u[k]>=0 for k in ('prompt_tokens','completion_tokens','total_tokens'))
    return dict(content_path=['choices',0,'message','content'],reasoning_path=['choices',0,'message','reasoning_content'],finish_path=['choices',0,'finish_reason'],usage_path=['usage'])
def stage_a(jobs,tr):
    a=read(OUT/'fictional_job.json');row=invoke(a,'A',tr);paths=observe_envelope(raw_of(row))
    p=OUT/'preflight/A_structure.json'
    if not p.exists():put(p,dict(status='OBSERVED_REAL_A_NO_GT',paths=paths,response_sha256=sha(ROOT/row['folder']/'response.raw'),created_utc=now()))
    return paths
def stage_b(jobs,tr):
    paths=read(OUT/'preflight/A_structure.json')['paths'];profile=ParserProfile(**paths)
    results={};lengths={(x['id'],x['arm']):x['chat_input_tokens'] for x in lines(OLD/'tokenizer_lengths.jsonl')}
    for role,j in selected(jobs):
        assert lengths[j['id'],j['arm']]+8192<=20000
        row=invoke(j,'B',tr);raw=raw_of(row);assert observe_envelope(raw)==paths
        parsed=parse(raw,profile);u=parsed['usage'];expected=lengths[j['id'],j['arm']]
        # Exact official-tokenizer chat count ensures the server did not silently change/truncate input.
        results[role]=dict(id=j['id'],arm=j['arm'],request_id=j['request_id'],parsed=parsed,expected_input_tokens=expected,input_tokens_match=u['prompt_tokens']==expected,
            raw_response_path=(Path(row['folder'])/'response.raw').as_posix(),raw_response_sha256=digest(raw),elapsed_seconds=row['receipt']['elapsed_seconds'])
    p=OUT/'preflight/B_result.json'
    if not p.exists():put(p,dict(created_utc=now(),results=results,GT_read=False))
    if not all(x['parsed']['valid'] and x['parsed']['truncated'] is False and x['input_tokens_match'] for x in results.values()):
        raise RuntimeError('B invalid/truncated/tokenization mismatch: keep first answers, no content retries; formal gate closed')
    frozen=OUT/'preflight/parser_profile.json'
    if not frozen.exists():put(frozen,dict(status='FROZEN_AFTER_AB_NO_GT',**paths,preflight_sha256=sha(p),parser_source_sha256=sha(ROOT/'tasks/085_r1_70b_model_swap/parse_r1.py'),created_utc=now()))
    return results
def forecast(jobs,args):
    b=read(OUT/'preflight/B_result.json')['results'];_,s,_=state()
    times={a:[v['elapsed_seconds'] for v in b.values() if v['arm']==a] for a in ('B','F4')}
    remaining={a:sum(j['arm']==a and j['request_id'] not in s for j in jobs) for a in times}
    seconds=sum(remaining[a]*statistics.mean(times[a]) for a in times)
    upper=sum(remaining[a]*max(times[a]) for a in times)*1.5
    result=dict(status='AWAIT_EXPLICIT_FORMAL_AUTHORIZATION',created_utc=now(),remaining_slots=remaining,already_successful=360-sum(remaining.values()),
        measured_client_concurrency=1,proposed_client_concurrency=1,estimated_serial_seconds=seconds,planning_seconds_with_50percent_buffer=upper,
        hourly_price_cny=args.hourly_price,estimated_cny=seconds/3600*args.hourly_price if args.hourly_price is not None else None,
        buffered_estimate_cny=upper/3600*args.hourly_price if args.hourly_price is not None else None,
        sample_completion_tokens={k:v['parsed']['usage']['completion_tokens'] for k,v in b.items()},
        limitations='Only 3 preflight requests; prefix-cache/length/load variation. Not a guaranteed upper cost. GPU rental includes download/startup/idle separately. No automatic full batch.',
        B_result_sha256=sha(OUT/'preflight/B_result.json'))
    p=OUT/'preflight/forecast.json'
    if not p.exists():put(p,result)
    print(canonical(result));return result
def formal(jobs,tr,args):
    if not args.allow_formal or not args.approval_note or args.max_runtime_hours is None or args.max_runtime_hours<=0:
        raise PermissionError('Formal batch requires explicit user authorization after forecast, --allow-formal --approval-note and --max-runtime-hours')
    if args.hourly_price is None or args.hourly_price<=0:raise ValueError('Actual user-supplied GPU hourly price required before formal run')
    read(OUT/'preflight/forecast.json');ParserProfile.from_json(read(OUT/'preflight/parser_profile.json'))
    # Conservative default1; a higher value needs a separately saved measured stability record.
    if args.workers!=1:raise ValueError('Only measured single-request concurrency is authorized in this branch; no untested throughput multiplier')
    start=now();t=time.monotonic();deadline=t+args.max_runtime_hours*3600
    run=OUT/'formal_runs'/str(time.time_ns());put(run/'authorization.json',dict(created_utc=start,user_approval_note=args.approval_note,hourly_price_cny=args.hourly_price,max_runtime_hours=args.max_runtime_hours,workers=1,
        forecast_sha256=sha(OUT/'preflight/forecast.json'),parser_sha256=sha(OUT/'preflight/parser_profile.json')))
    error=None
    try:
        for j in jobs:invoke(j,'formal',tr,deadline)
    except Exception as e:error=type(e).__name__+':'+str(e);raise
    finally:
        elapsed=time.monotonic()-t;put(run/'runtime.json',dict(started_utc=start,ended_utc=now(),wall_seconds=elapsed,estimated_gpu_cny=elapsed/3600*args.hourly_price,status='COMPLETE' if error is None else 'STOPPED',error=error))
def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('dry-run','A','B','forecast','formal','status'))
    p.add_argument('--allow-inference',action='store_true');p.add_argument('--allow-formal',action='store_true');p.add_argument('--server-manifest',type=Path);p.add_argument('--server-observation',type=Path)
    p.add_argument('--hourly-price',type=float);p.add_argument('--max-runtime-hours',type=float);p.add_argument('--approval-note');p.add_argument('--workers',type=int,default=1);p.add_argument('--timeout',type=float,default=900)
    args=p.parse_args();jobs=load_jobs()
    if args.stage=='status':
        rows,s,c=state();print(canonical(dict(attempts=len(rows),success=len(s),unknown=sum(x['receipt'].get('outcome_unknown',False) for x in rows))));return
    if args.stage=='dry-run' or (args.stage in ('A','B','formal') and not args.allow_inference):
        print(canonical(dict(status='OFFLINE_ONLY',endpoint_configured=bool(os.getenv('R1_BASE_URL')),jobs=len(jobs),stage_B=[dict(role=r,id=j['id'],arm=j['arm']) for r,j in selected(jobs)],network_calls=0,inference_calls=0)));return
    if args.stage=='forecast':forecast(jobs,args);return
    # Formal authorization checked before any service contact.
    if args.stage=='formal' and not args.allow_formal:raise PermissionError('Formal inference not authorized')
    lock=OUT/'run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        tr=bind_service(args)
        if args.stage=='A':stage_a(jobs,tr)
        elif args.stage=='B':stage_b(jobs,tr);forecast(jobs,args)
        else:formal(jobs,tr,args)
    finally:lock.unlink()
if __name__=='__main__':main()
