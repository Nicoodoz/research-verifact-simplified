"""Post-service technical inspection and once-only scale selection, GT-blind."""
import statistics,json,datetime,time
import common096 as c
import runner096 as run
from parse_r1 import ParserProfile,parse

def inspect_and_freeze():
    lengths={r['request_id']:r for r in c.lines(c.OUT/'local_token_lengths.jsonl')};jobs=run.frozen_jobs('technical');observed=[];reasoning_paths=[]
    for j in jobs:
        folder=run.success(j);assert folder is not None,'Preflight incomplete'
        n=c.read(folder/'response.raw');assert n.get('model')==c.MODEL
        ch=n['choices'][0];msg=ch['message'];assert isinstance(msg.get('content'),str)
        rp=['choices',0,'message','reasoning_content'] if isinstance(msg.get('reasoning_content'),str) else None;reasoning_paths.append(rp)
        pp=ParserProfile(content_path=['choices',0,'message','content'],finish_path=['choices',0,'finish_reason'],usage_path=['usage'],reasoning_path=rp)
        p=parse(n,pp);assert p['valid'] and not p['truncated'],'Technical preflight invalid; retain response, do not repeat on content'
        u=n['usage'];assert u['prompt_tokens']==lengths[j['request_id']]['input_tokens'] and u['prompt_tokens']+8192<=20000,'Actual tokenizer/context mismatch'
        receipt=c.read(folder/'receipt.json')
        observed.append(dict(id=j['id'],request_id=j['request_id'],stage=j['stage'],prompt_tokens=u['prompt_tokens'],completion_tokens=u['completion_tokens'],finish_reason=ch['finish_reason'],raw_valid=p['valid'],scores_valid=p['label_scores'] is not None,reasoning_chars=len(p['reasoning'] or ''),content_chars=len(msg['content']),raw_think_tags='<think>' in msg['content'].lower(),elapsed_seconds=receipt['elapsed_seconds'],started_utc=receipt['started_utc'],ended_utc=receipt['ended_utc'],response_sha256=c.sha(folder/'response.raw')))
    assert sum(r['scores_valid'] for r in observed if r['stage']=='calibration')>=2,'Too few usable preflight scores for planned adaptation'
    assert all(x==reasoning_paths[0] for x in reasoning_paths),'Native envelope inconsistent; freeze no guessed path'
    c.put(c.OUT/'technical_observations.json',dict(observations=observed,GT_read=False,empty_reasoning_is_not_proof_of_no_reasoning=True))
    c.put(c.OUT/'live_parser_profile.json',dict(status='FROZEN_AFTER_AB_NO_GT',content_path=['choices',0,'message','content'],reasoning_path=reasoning_paths[0],finish_path=['choices',0,'finish_reason'],usage_path=['usage'],model=c.MODEL,GT_read=False,source_parse_sha256=c.sha(c.ROOT/'tasks/085_r1_70b_model_swap/parse_r1.py'),response_sha256=[r['response_sha256'] for r in observed]))

def forecast_and_select(runtime):
    if (c.OUT/'live_plan_selection.json').exists():
        print('PLAN_ALREADY_FROZEN',c.read(c.OUT/'live_plan_selection.json')['name']);return
    cfg=run.validate_runtime(runtime);data=c.read(c.OUT/'technical_observations.json')['observations'];cal=[r for r in data if r['stage']=='calibration']
    start=min(run.aware(r['started_utc']) for r in cal);end=max(run.aware(r['ended_utc']) for r in cal);wall=(end-start).total_seconds();assert wall>0
    observed_seconds_per_request=wall/len(cal)
    # Three heterogeneous observations are not a throughput guarantee. Use
    # 50% wall-time margin, with runtime timeout reserves enforced separately.
    conservative_seconds=observed_seconds_per_request*1.5
    now=datetime.datetime.now(datetime.timezone.utc);elapsed=(now-run.aware(cfg['gpu_billing_start'])).total_seconds();variants=c.read(c.OUT/'panel_variants.json');choices=[]
    for name in ['main800_stress200','main800_only','main600_stress100','main600_only']:
        v=variants[name];remaining=140+len(v['main_ids'])+len(v['stress_ids']);seconds=remaining*conservative_seconds
        cost=(elapsed+seconds+cfg['shutdown_margin_seconds'])*cfg['gpu_hourly_cny']/3600
        fits=cost<=cfg['gpu_cap_cny'] and now+datetime.timedelta(seconds=seconds)<run.aware(cfg['stop_sending_at'])
        choices.append(dict(name=name,remaining=remaining,forecast_seconds=seconds,total_billing_forecast_cny=cost,fits=fits))
    forecast_path=c.OUT/('live_throughput_forecast_'+str(time.time_ns())+'.json')
    c.put(forecast_path,dict(actual_preflight_wall_seconds=wall,observed_seconds_per_request=observed_seconds_per_request,completion_tokens=[r['completion_tokens'] for r in cal],client_concurrency=cfg['client_concurrency'],factor=1.5,choices=choices,not_hard_guarantee=True))
    chosen=next((r for r in choices if r['fits']),None)
    if chosen is None:raise RuntimeError('NO_FROZEN_SIZE_FITS_GPU_CAP; no evaluation requests sent')
    assert not any(run.attempts(j) for stage in ['main','stress'] for j in c.lines(c.PRIVATE/'jobs.jsonl') if j['stage']==stage),'size decision must precede evaluation sending'
    v=variants[chosen['name']]
    c.put(c.OUT/'live_plan_selection.json',dict(status='SIZE_FROZEN_BEFORE_EVALUATION_REQUESTS',name=chosen['name'],**v,main_panel_path='main_panel.jsonl' if len(v['main_ids'])==800 else 'main600_panel.jsonl',stress_panel_path='stress_panel.jsonl' if len(v['stress_ids'])==200 else 'stress100_panel.jsonl' if v['stress_ids'] else None,reason='first predeclared plan fitting measured throughput, billing start, cap and deadline; preserve800main before optionalstress; no results/GT joined',forecast_path=forecast_path.relative_to(c.ROOT).as_posix(),forecast_sha256=c.sha(forecast_path)))
    print('LIVE_PLAN_FROZEN',chosen['name'])

def done():
    selection=c.read(c.OUT/'live_plan_selection.json');jobs=[]
    for stage in ['calibration','main','stress']:jobs+=run.frozen_jobs(stage)
    seen=[]
    for j in jobs:
        folder=run.success(j);assert folder is not None,'Incomplete R1 inference; do not request shutdown as finished'
        receipt=c.read(folder/'receipt.json');assert receipt['response_sha256']==c.sha(folder/'response.raw')
        seen.append(dict(request_id=j['request_id'],response_sha256=receipt['response_sha256']))
    c.put(c.OUT/'R1_INFERENCE_DONE.json',dict(status='R1_INFERENCE_DONE',utc=c.now(),clinical_HTTP200=len(seen),receipts=seen,default_changed=False,message='All chosen clinical responses saved locally. User must shut down AutoDL on platform; stopping Python/vLLM does not end billing. CPU evaluation needs no GPU.'))
    print('R1_INFERENCE_DONE — 请在AutoDL平台关机；停止Python不等于停止计费。')
