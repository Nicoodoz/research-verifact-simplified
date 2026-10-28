"""Inert-by-default 106 local preflight and future, separately authorized GPU run.

This module never buys, starts, connects to, or shuts down an instance. The
operator supplies an already-running Linux instance and a NEW authorization
record; merely preparing task106 does not supply that authorization.
"""
from __future__ import annotations
import argparse
import importlib.metadata as md
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import math
import shutil
import common106 as c

def verify_bundle(root):
    root=Path(root).resolve();manifest=c.read(root/'manifest.json')
    if manifest.get('task')!=106:raise ValueError('Not a task106 package')
    for name,wanted in manifest['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or c.sha(path)!=wanted:raise ValueError('Bundle mismatch: '+name)
    return manifest

def verify_authorization(bundle, authorization):
    a=c.read(authorization)
    if a.get('task')!=106 or a.get('explicit_user_gpu_authorization') is not True:raise PermissionError('A new explicit user GPU authorization is required')
    for key in ('user_request_reference','authorized_at','hourly_cny','billing_start_epoch','cap_cny','fixed_bundle_sha256'):
        if key not in a or a[key] in (None,''):raise ValueError('Missing authorization field '+key)
    if a['fixed_bundle_sha256']!=c.sha(Path(bundle)/'manifest.json'):raise ValueError('Authorization does not bind this exact frozen package')
    if a['hourly_cny']<=0 or a['cap_cny']<=2 or a['billing_start_epoch']>time.time():raise ValueError('Actual quote/start/cap required')
    if a.get('confirmed_original_9b_environment') is not True:raise ValueError('Explicit original-base/environment confirmation required')
    if a.get('baseline_cache_mode') not in {'reuse','rerun'}:raise ValueError('Predeclare baseline cache reuse or paid rerun in the new GPU authorization')
    return a

def used_cny(state,now=None):
    now=time.time() if now is None else now
    cost=sum(s['cost_cny'] for s in state.get('closed_sessions',[]))+state.get('adjustments_cny',0.)
    active=state.get('active')
    if active:
        if now<active['billing_start_epoch']:raise ValueError('Clock before platform billing start')
        cost+=(now-active['billing_start_epoch'])/3600*active['hourly_cny']
    return cost

def require_budget(ledger,seconds=120):
    state=c.read(ledger);active=state.get('active')
    if not active or active['machine']!=platform.node():raise RuntimeError('No current bound billing session')
    if (Path(ledger).parent/'stop_requested.json').exists():raise TimeoutError('Stop requested; preserve committed checkpoints and manually stop instance')
    if used_cny(state)+seconds*active['hourly_cny']/3600>state['operating_line_cny']:raise TimeoutError('Budget stop; manual platform shutdown still required')
    return state

def require_whole_remaining(ledger,estimate,baseline_mode):
    """After resource gate, BEFORE any optimizer update or formal answer."""
    state=require_budget(ledger,0);active=state['active']
    seconds=float(estimate['remaining_after_gate_seconds']);discounted={}
    components=estimate.get('remaining_components_seconds',{})
    if components and abs(sum(components.values())-seconds)>1:raise ValueError('Remaining component totals do not match whole-run estimate')
    # Conservative recovery discount: committed training consumption can remove
    # its compute fraction; an evaluation/diagnostic component is removed only
    # when its ENTIRE fixed raw panel (+all diagnostic path scores) is present.
    work=Path(ledger).parent;expected_bundle=state.get('bundle_manifest_sha256')
    for key,value in components.items():
        fraction=0.
        if key.startswith('train/'):
            path=work/'train'/key.split('/')[1]/'resume.json'
            if path.exists():
                saved=c.read(path)
                if saved['fingerprint']['bundle_manifest_sha256']==expected_bundle:fraction=min(1.,saved['consumed']/392)
        elif key.startswith(('development/','diagnostic/')):
            panel,arm=key.split('/');folder=work/'eval'/arm/panel;records=[]
            for path in folder.glob('batch-*.json'):
                if '.inflight.' not in path.name:
                    saved=c.read(path)
                    if saved['bundle_sha256']==expected_bundle:records+=saved['records']
            need=500 if panel=='development' else int(estimate['diagnostic_N'])
            if len(records)==need and len({r['id'] for r in records})==need:
                if panel=='development':fraction=1.
                else:
                    scores=[c.read(path) for path in (folder/'complete_label_paths').glob('*.json')]
                    if len(scores)==need and all(s['bundle_sha256']==expected_bundle for s in scores):fraction=1.
        if fraction:
            discounted[key]=value*fraction;seconds-=value*fraction
    if baseline_mode=='rerun':seconds+=float(estimate['baseline_rerun_extra_seconds'])
    if seconds<=0:raise ValueError('A positive complete remaining-work estimate is required')
    projected=used_cny(state)+seconds*active['hourly_cny']/3600
    receipt=dict(utc=c.utc(),estimated_remaining_seconds=seconds,actual_hourly_cny=active['hourly_cny'],
                 committed_work_discounts_seconds=discounted,
                 already_used_cny=used_cny(state),estimated_total_compute_cny=projected,operating_line_cny=state['operating_line_cny'],
                 remaining_budget_gap_cny=max(0.,projected-state['operating_line_cny']),optimizer_updates=0,
                 fits_complete_frozen_run=projected<=state['operating_line_cny'])
    c.put(Path(ledger).parent/'whole_run_budget_gate.json',receipt)
    if not receipt['fits_complete_frozen_run']:raise TimeoutError('Complete frozen comparison exceeds remaining budget; no optimizer update; manual shutdown required')
    return receipt

def preflight(bundle,model_dir,work):
    bundle=Path(bundle);model_dir=Path(model_dir);work=Path(work);verify_bundle(bundle)
    free=shutil.disk_usage(work if work.exists() else work.parent).free
    if free<6*1024**3:raise RuntimeError('Need6GiB existing scratch for rolling checkpoints/results; do not buy storage automatically')
    expected=c.read(bundle/'frozen/weights_manifest.json')
    sys.path.insert(0,str(bundle/'tasks/105_brief_supervision'))
    from verify105 import weights
    result=weights(model_dir,expected)
    versions={}
    for name,wanted in c.read(bundle/'frozen/environment_versions.json').items():
        try:actual=md.version(name)
        except md.PackageNotFoundError:actual=None
        versions[name]={'expected':wanted,'actual':actual}
    if any(r['expected']!=r['actual'] for r in versions.values()):raise RuntimeError('Pinned GPU environment differs: '+c.canonical(versions))
    from tokenizer_cpu105 import CPUPinnedTokenizer
    from data105 import encode,shared
    tok=CPUPinnedTokenizer(model_dir)
    wanted={(r['arm'],r['id']):r for r in c.rows(bundle/'frozen/train_token_lengths.jsonl')}
    for arm in ('label_mean','label_sum'):
        for row in c.rows(bundle/'data/train'/(arm+'.jsonl')):
            e=encode(tok,row);r=wanted[(arm,row['id'])]
            if e['prompt_token_sha256']!=r['prompt_token_sha256'] or e['answer_sha256']!=r['answer_sha256'] or len(e['input_ids'])!=r['total_tokens']:raise ValueError('Training tokenizer bridge mismatch')
    for prefix,file in [('eval','eval_inputs.jsonl'),('diagnostic','diagnostic_inputs.jsonl')]:
        maps={r['id']:r for r in c.rows(bundle/'frozen'/(prefix+'_token_lengths.jsonl'))}
        for row in c.rows(bundle/'data'/file):
            if c.digest(c.canonical(shared.prompt_ids(tok,row)))!=maps[row['id']]['prompt_token_sha256']:raise ValueError('Evaluation tokenizer bridge mismatch')
    if any(name=='torch' or name.startswith('torch.') or name=='transformers' or name.startswith('transformers.') for name in sys.modules):raise RuntimeError('Preflight unexpectedly imported model stack')
    result.update(task=106,bundle_sha256=c.sha(bundle/'manifest.json'),model_dir=str(model_dir.resolve()),versions=versions,tokenizer_bridge_verified=True,model_loaded=False,existing_free_bytes=free)
    c.put(work/'preflight106.json',result);return result

def watch(ledger):
    """Independent manual-stop reminder, NEVER system/platform shutdown."""
    ledger=Path(ledger)
    while True:
        state=c.read(ledger)
        if (ledger.parent/'complete106.json').exists():return
        if used_cny(state)>=state['operating_line_cny']:
            c.put(ledger.parent/'stop_requested.json',dict(reason='budget_operating_line',utc=c.utc(),used_cny=used_cny(state),platform_shutdown_executed=False))
            c.put(ledger.parent/'MANUAL_SHUTDOWN_REQUIRED.json',dict(utc=c.utc(),reason='budget stop',billing_still_running=True))
            return
        time.sleep(3)

def verify_fixed_outputs(bundle,work,baseline_mode):
    """No model imports; do not mark complete with missing diagnostic paths."""
    bundle=Path(bundle);work=Path(work);bundle_sha=c.sha(bundle/'manifest.json')
    expected={r['id'] for r in c.rows(bundle/'data/diagnostic_inputs.jsonl')}
    total_paths=0
    for arm in ('base_judge','label_mean','label_sum'):
        for prefix,panel,needed in [('diagnostic','diagnostic',True),('eval','development',arm=='label_sum' or baseline_mode=='rerun')]:
            if not needed:continue
            batches=c.read(bundle/'frozen'/(prefix+'_batches.json'))['batches']
            for entry in batches:
                path=work/'eval'/arm/panel/f"batch-{entry['batch']:04d}.json"
                saved=c.read(path)
                if saved['bundle_sha256']!=bundle_sha or saved['ids']!=entry['ids'] or [r['id'] for r in saved['records']]!=entry['ids'] or any(r['arm']!=arm for r in saved['records']):raise ValueError('Fixed formal/diagnostic batch incomplete or mismatched')
        score_dir=work/'eval'/arm/'diagnostic/complete_label_paths'
        scores=[c.read(path) for path in score_dir.glob('*.json')]
        if len(scores)!=len(expected) or {s['id'] for s in scores}!=expected:raise ValueError('Missing or duplicate fixed training diagnostic label scores')
        for score in scores:
            values=score.get('complete_JSON_EOS_sum_logP',{})
            if score['arm']!=arm or score['bundle_sha256']!=bundle_sha or set(values)!=set(c.LABELS) or not all(math.isfinite(v) and v<=0 for v in values.values()):raise ValueError('Incomplete diagnostic legal paths')
            total_paths+=len(values)
    return dict(diagnostic_cases_each_model=len(expected),models=3,complete_legal_paths=total_paths,all_fixed_greedy_batches_received=True)

def execute(a):
    if not a.execute_authorized_gpu:raise PermissionError('Preparation does not authorize execution; explicit future flag and user record required')
    if platform.system()!='Linux':raise RuntimeError('Future GPU entry runs only on the supplied Linux instance')
    verify_bundle(a.bundle);authorization=verify_authorization(a.bundle,a.authorization)
    pre=c.read(a.work/'preflight106.json')
    if pre['bundle_sha256']!=c.sha(a.bundle/'manifest.json') or pre['model_dir']!=str(a.model_dir.resolve()):raise ValueError('Current preflight required')
    ledger=a.work/'compute106.json'
    if ledger.exists():
        state=c.read(ledger)
        if state['authorization_sha256']!=c.sha(a.authorization):raise ValueError('Cannot reset ledger under a different authorization')
    else:
        c.put(ledger,dict(task=106,authorization_sha256=c.sha(a.authorization),cap_cny=authorization['cap_cny'],
              baseline_cache_mode=authorization['baseline_cache_mode'],
              bundle_manifest_sha256=c.sha(a.bundle/'manifest.json'),
              operating_line_cny=authorization['cap_cny']-2,closed_sessions=[],active=dict(machine=platform.node(),hourly_cny=authorization['hourly_cny'],billing_start_epoch=authorization['billing_start_epoch'])))
    watcher=subprocess.Popen([sys.executable,str(Path(__file__)), 'watch','--work',str(a.work)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    worker=Path(__file__).with_name('worker106.py')
    base=[sys.executable,str(worker),'--bundle',str(a.bundle),'--work',str(a.work),'--model-dir',str(a.model_dir),'--ledger',str(ledger),
          '--authorization',str(a.authorization),'--execute-authorized-gpu']
    stages=[('gate','label_sum','development')]
    if authorization['baseline_cache_mode']=='rerun':stages += [('eval','base_judge','development'),('eval','label_mean','development')]
    stages += [('eval','base_judge','diagnostic'),('eval','label_mean','diagnostic'),
               ('train','label_sum','development'),('eval','label_sum','development'),('eval','label_sum','diagnostic')]
    try:
        for mode,arm,panel in stages:
            require_budget(ledger)
            command=base+['--mode',mode,'--arm',arm,'--panel',panel]
            if mode=='train' and (a.work/'train'/arm/'resume.json').exists():command.append('--resume')
            subprocess.run(command,check=True)
            if mode=='gate':require_whole_remaining(ledger,c.read(a.bundle/'frozen/cost_estimate.json'),authorization['baseline_cache_mode'])
        verified=verify_fixed_outputs(a.bundle,a.work,authorization['baseline_cache_mode'])
        c.put(a.work/'complete106.json',dict(utc=c.utc(),task=106,all_fixed_stages_complete=True,bundle_sha256=c.sha(a.bundle/'manifest.json'),**verified))
    finally:
        c.put(a.work/'MANUAL_SHUTDOWN_REQUIRED.json',dict(utc=c.utc(),billing_still_running=True,platform_shutdown_executed=False,
               instruction='Save completed adapters/results, stop this instance in platform console now; transfer/report on CPU afterwards.'))
        watcher.terminate()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['preflight','run','watch'])
    p.add_argument('--bundle',type=Path);p.add_argument('--model-dir',type=Path);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--authorization',type=Path);p.add_argument('--execute-authorized-gpu',action='store_true');a=p.parse_args()
    if a.action=='watch':watch(a.work/'compute106.json')
    elif a.action=='preflight':print(c.canonical(preflight(a.bundle,a.model_dir,a.work)))
    else:
        if a.authorization is None:p.error('A NEW user authorization record is required')
        # An orchestration lock prevents two supervisors from interleaving
        # otherwise individually locked workers. Never remove a live lock.
        if not a.execute_authorized_gpu:raise PermissionError('No GPU execution authorization flag')
        if platform.system()!='Linux':raise RuntimeError('Future GPU orchestration is Linux-only')
        a.work.mkdir(parents=True,exist_ok=True)
        lock=a.work/'orchestrator106.lock'
        if lock.exists():
            pid=int(lock.read_text())
            try:os.kill(pid,0)
            except ProcessLookupError:lock.unlink()
            else:raise RuntimeError('Another106 supervisor is live; refuse concurrent execution')
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        os.write(fd,str(os.getpid()).encode());os.close(fd)
        try:execute(a)
        finally:lock.unlink()

if __name__=='__main__':main()
