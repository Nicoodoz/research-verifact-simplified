"""109 supplied-instance orchestrator. Current authorization is CPU prep ONLY.

Help/preflight never loads9B. A future run needs a separate affirmative rental
session, actual quote/start/budget and explicit execution flag on bound Linux.
No SSH, purchase, wakeup, cloud API, package installation or shutdown is done.
"""
from pathlib import Path
import argparse,importlib.metadata as md,math,platform,subprocess,sys,time
import common109 as c

def verify_bundle(bundle):
    bundle=Path(bundle).resolve();m=c.read(bundle/'manifest.json')
    if m['task']!=109:raise ValueError('Wrong task package')
    for name,info in m['files'].items():
        path=(bundle/name).resolve()
        if not path.is_relative_to(bundle) or not path.is_file() or path.stat().st_size!=info['bytes']:raise ValueError('Missing/wrong package file '+name)
        if c.sha(path)!=info['sha256']:raise ValueError('Package integrity mismatch '+name)
    return m

def authorization(bundle,session,execute=False):
    if not execute:raise PermissionError('No109 GPU execution authorization in CPU preparation')
    s=c.read(session)
    if s.get('task')!=109 or s.get('GPU_execution_authorized') is not True or s.get('user_supplied_rented_instance') is not True:raise PermissionError('New explicit user rental AND GPU execution authorization required')
    if platform.system()!='Linux' or s.get('bound_instance')!=platform.node():raise PermissionError('Only the newly authorized bound Linux instance')
    if not s.get('authorization_reference') or s.get('fixed_bundle_sha256')!=c.sha(Path(bundle)/'manifest.json'):raise ValueError('Authorization must bind the prepared109 package')
    for key in ('hourly_cny','cap_cny','billing_start_epoch'):
        if not isinstance(s.get(key),(int,float)) or not math.isfinite(s[key]) or s[key]<=0:raise ValueError('Actual quote/start/approved cap required')
    if s['billing_start_epoch']>time.time() or s.get('API_cap_cny')!=0:raise ValueError('Actual billing start and zero paidAPI required')
    return s

def require_budget(session,seconds=120):
    s=c.read(session);now=time.time();used=s.get('prior_GPU_cny',0)+(now-s['billing_start_epoch'])*s['hourly_cny']/3600
    reserve=s.get('shutdown_reserve_cny',1)
    if used+seconds*s['hourly_cny']/3600>s['cap_cny']-reserve:raise TimeoutError('Whole remaining work exceeds approved109 GPU cap including waiting')
    if s.get('platform_deadline_epoch') and now+seconds+120>=s['platform_deadline_epoch']:raise TimeoutError('Insufficient time before user platform cutoff')
    return used

def preflight(bundle,model_dir=None):
    m=verify_bundle(bundle);bundle=Path(bundle);source=c.read(bundle/'source107/resume.json')
    if source['step']!=50 or source['consumed']!=392 or source['fingerprint']['arm']!='label_only':raise ValueError('Wrong107 continuation source')
    cfg=c.read(bundle/'frozen/config109.json');old=c.read(bundle/'frozen/source107_config.json')
    for key in ('learning_rate','optimizer','betas','eps','weight_decay','scheduler','gradient_clip','bf16','quantization','CPU_offload','gradient_checkpointing','lora_r','lora_alpha','lora_dropout','bias','use_rslora','target_modules','head_chunk_tokens','loss'):
        if cfg['training'][key]!=old['training'][key]:raise ValueError('Unintended old training setting change: '+key)
    for key in ('batch_size','enable_thinking','do_sample','num_beams','num_return_sequences','max_new_tokens','repetition_penalty','truncation','input_template','parser'):
        if cfg['evaluation'][key]!=old['evaluation'][key]:raise ValueError('Unintended107 evaluation change: '+key)
    missing=[]
    if model_dir:
        model_dir=Path(model_dir);assets=c.read(bundle/'frozen/model_assets.json')
        for name,info in assets['files'].items():
            path=model_dir/name
            if not path.is_file() or ('bytes' in info and path.stat().st_size!=info['bytes']):missing.append(name)
            elif not name.endswith('.safetensors') and c.sha(path)!=info['sha256']:raise ValueError('Original model/tokenizer metadata changed: '+name)
        if missing:raise FileNotFoundError('Original9B assets missing: '+', '.join(missing))
        expected=assets['versions'];actual={}
        for name,values in expected.items():
            try:actual[name]=md.version(name)
            except md.PackageNotFoundError:actual[name]=None
            if actual[name]!=values['expected']:missing.append(name+': '+str(actual[name])+' need '+values['expected'])
        if missing:raise RuntimeError('Existing9B environment differs: '+'; '.join(missing))
    return dict(task=109,bundle_verified=True,source107_step=50,source107_label_only=True,main_loss_and_training_settings_unchanged=True,
        fixed500_interface_and_batch2_unchanged=True,original9B_weights_loaded=False,CUDA_initialized=False,
        model_directory_checked=bool(model_dir),newGPU_authorization_granted_by_preflight=False,package_bytes=m['package_bytes'])

def run(a):
    s=authorization(a.bundle,a.session,a.execute_rented_gpu);preflight(a.bundle,a.model_dir)
    if a.work.resolve().is_relative_to(a.bundle.resolve()):raise ValueError('Results must not overwrite the immutable source bundle')
    if a.work.exists() and any(a.work.iterdir()) and not (a.work/'identity.json').exists():raise ValueError('Do not overwrite another task/nonempty unrelated work directory')
    a.work.mkdir(parents=True,exist_ok=True);fp=dict(bundle_sha256=c.sha(a.bundle/'manifest.json'),source_adapter_sha256=c.SOURCE_ADAPTER_SHA)
    if (a.work/'identity.json').exists() and c.read(a.work/'identity.json')!=fp:raise ValueError('Existing109 work has another source/package')
    c.put(a.work/'identity.json',fp)
    committed_any=any(p for p in (a.work/'mining_a').glob('batch-*.json') if '.inflight.' not in p.name)
    require_budget(a.session,120 if committed_any else 5400)
    def worker(mode):
        phase={'mine_a':'mining_a','mine_s':'mining_s','evaluate':'evaluation'}.get(mode)
        if phase and (a.work/phase/'done.json').exists() and (a.work/phase/'predictions.jsonl').exists():
            d=c.read(a.work/phase/'done.json')
            expected=500 if mode=='evaluate' else len(c.read(a.bundle/'data/stage_a_ids.json') if mode=='mine_a' else c.read(a.work/'supported_request.json')['ids'])
            if d['N']!=expected:raise ValueError('Existing completed prediction request has wrong count')
            if mode!='evaluate' and d['checkpoint_adapter_sha256']!=c.SOURCE_ADAPTER_SHA:raise ValueError('Existing predictions are not current107 source')
            if mode=='evaluate':
                pointer=c.read(a.work/'train/resume.json')
                if d['checkpoint_adapter_sha256']!=c.sha(a.work/'train'/pointer['slot']/'adapter_model.safetensors'):raise ValueError('Existing evaluation is not this final109 adapter')
            return
        if mode=='train' and (a.work/'train/training_done.json').exists():
            d=c.read(a.work/'train/training_done.json')
            if d['step']!=24 or d['fingerprint']['training_file_sha256']!=c.sha(a.work/'train.jsonl'):raise ValueError('Existing training completion differs')
            return
        command=[sys.executable,'-B','-u',str(a.bundle/'tasks/109_boundary_replay/worker109.py'),mode,
            '--bundle',str(a.bundle.resolve()),'--model-dir',str(a.model_dir.resolve()),'--work',str(a.work.resolve()),
            '--session',str(a.session.resolve()),'--execute-rented-gpu']
        with (a.work/(mode+'.log')).open('ab') as log:result=subprocess.run(command,cwd=a.work,stdout=log,stderr=log)
        if result.returncode:raise RuntimeError('109 '+mode+' exited; preserve first receipts and inspect '+mode+'.log')
    try:
        worker('mine_a')
        from select109 import load_predictions,choose_hard,supported_request,select
        meta={r['id']:r for r in c.rows(a.bundle/'data/pool_metadata.jsonl')};cfg=c.read(a.bundle/'frozen/config109.json')
        first=load_predictions(a.work/'mining_a/predictions.jsonl',c.read(a.bundle/'data/stage_a_ids.json'),meta)
        hard=choose_hard(meta,first,cfg);neighbors=c.read(a.bundle/'data/neighbors.json');source=c.read(a.bundle/'data/source_ids.json')
        request=supported_request(hard,neighbors,source,meta,cfg)
        c.put(a.work/'supported_request.json',dict(hard_ids=hard,ids=request))
        worker('mine_s');second=load_predictions(a.work/'mining_s/predictions.jsonl',request,meta)
        manifest,summary=select(meta,first,second,neighbors,source,cfg);raw={r['id']:r for r in c.rows(a.bundle/'data/pool.jsonl')}
        c.putl(a.work/'selected_manifest.jsonl',manifest);c.putl(a.work/'train.jsonl',[raw[r['id']] for r in manifest]);c.put(a.work/'selection_summary.json',summary)
        worker('train');worker('evaluate')
        from return109 import collect
        collect(a.work)
        c.put(a.work/'GPU_TASKS_COMPLETE.json',dict(task=109,one_candidate=True,source107_reused=True,second_arm_run=False,
            next='persist_and_return_assets_then_stop_GPU_billing_per_new_user_authorization; CPU_analysis_separately',paid_API_calls=0))
    except BaseException as error:
        c.put(a.work/'STOP_AND_SAVE.json',dict(task=109,error_type=type(error).__name__,reason=str(error),
            no_automatic_recipe_change=True,GPU_billing_not_stopped_by_process_exit=True))
        from return109 import collect_partial
        collect_partial(a.work);raise

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['preflight','run'])
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--model-dir',type=Path)
    p.add_argument('--work',type=Path);p.add_argument('--session',type=Path);p.add_argument('--execute-rented-gpu',action='store_true');a=p.parse_args()
    if a.action=='preflight':print(c.canonical(preflight(a.bundle,a.model_dir)))
    else:
        if not a.model_dir or not a.work or not a.session:p.error('Future run requires model-dir/work/new authorized session')
        run(a)

if __name__=='__main__':main()
