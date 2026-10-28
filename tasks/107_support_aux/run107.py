"""Task107 supplied-instance entry; import/help/preflight never loads a model.

The user has authorized stage2 after renting an instance. The session record
below records that rental's actual price/start and binds the prepared package;
it is not a new scientific approval. No cloud/API/SSH/purchase is performed.
"""
from __future__ import annotations
import argparse
import importlib.metadata as md
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
import common107 as c


def verify_bundle(root):
    root=Path(root).resolve();manifest=c.read(root/'manifest.json')
    if manifest.get('task')!=107:raise ValueError('Not a task107 package')
    for name,wanted in manifest['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or c.sha(path)!=wanted:raise ValueError('Bundle mismatch: '+name)
    return manifest


def verify_authorization(bundle,session):
    a=c.read(session)
    if a.get('task')!=107 or a.get('user_supplied_rented_instance') is not True:raise PermissionError('User-rented107 instance session record required')
    for key in ('user_request_reference','hourly_cny','billing_start_epoch','fixed_bundle_sha256'):
        if key not in a or a[key] in (None,''):raise ValueError('Missing rental field '+key)
    if a['fixed_bundle_sha256']!=c.sha(Path(bundle)/'manifest.json'):raise ValueError('Rental session binds a different package')
    if not math.isfinite(a['hourly_cny']) or a['hourly_cny']<=0 or a['billing_start_epoch']>time.time():raise ValueError('Actual quote and billing start required')
    if a.get('cap_cny')!=20 or a.get('API_cap_cny')!=0:raise ValueError('107 GPU cap20 and API0 are fixed')
    return a


def used_cny(state,now=None):
    now=time.time() if now is None else now
    total=sum(s['cost_cny'] for s in state.get('closed_sessions',[]))+state.get('adjustments_cny',0.)
    active=state.get('active')
    if active:
        if now<active['billing_start_epoch']:raise ValueError('Clock before platform billing start')
        total+=(now-active['billing_start_epoch'])/3600*active['hourly_cny']
    return total


def require_budget(ledger,seconds=120):
    state=c.read(ledger);active=state.get('active')
    if not active or active['machine']!=platform.node():raise RuntimeError('No bound current billing session')
    if (Path(ledger).parent/'stop_requested.json').exists():raise TimeoutError('Budget stop requested; preserve state and stop platform billing')
    if used_cny(state)+seconds*active['hourly_cny']/3600>state['operating_line_cny']:raise TimeoutError('Budget stop; stopping this process does not stop GPU billing')
    return state


def require_whole_remaining(ledger,estimate,gate):
    """Actual price + measured GPU speed, before the first formal optimizer step."""
    state=require_budget(ledger,0);active=state['active'];work=Path(ledger).parent
    if gate.get('status')!='PASS' or gate['bundle_sha256']!=state['bundle_manifest_sha256']:raise ValueError('Current successful real GPU gate required')
    absolute=estimate.get('runtime_estimate_mode')=='actual_gpu_absolute'
    if absolute:
        measured=gate.get('measured_run_estimate_seconds',{})
        if not measured or any(not math.isfinite(float(measured.get(k,0))) or measured.get(k,0)<=0 for k in ('train_each','eval_each','remaining_overhead')):raise ValueError('Actual current-card training and frozen-batch throughput measurements required')
        train_seconds=float(measured['train_each']);eval_seconds=float(measured['eval_each'])
        train_factor=inference_factor=None
    else:
        # Historical v1 preparation compatibility only. A current-card package
        # freezes actual_gpu_absolute and must never fall back to these ratios.
        train_factor=max(1.,float(gate['training_slowdown_vs105']))
        inference_factor=max(1.,float(gate['inference_slowdown_vs105']))
        train_seconds=float(estimate['per_arm_train_remaining_seconds'])*train_factor
        eval_seconds=float(estimate['per_arm_eval_cautious_seconds'])*inference_factor
    components={};discounts={}
    for arm in c.ARMS:
        value=train_seconds
        path=work/'train'/arm/'resume.json'
        if path.exists():
            saved=c.read(path)
            if saved['fingerprint']['bundle_manifest_sha256']!=state['bundle_manifest_sha256']:raise ValueError('Committed work belongs to another package')
            removed=value*min(1.,saved['consumed']/392);value-=removed;discounts['train/'+arm]=removed
        components['train/'+arm]=value
        value=eval_seconds
        done=work/'eval'/arm/'development'/'evaluation_done.json'
        if done.exists():
            d=c.read(done)
            if d['bundle_sha256']!=state['bundle_manifest_sha256'] or d['received']!=500:raise ValueError('Invalid evaluation completion receipt')
            discounts['eval/'+arm]=value;value=0.
        components['eval/'+arm]=value
    components['saving_loading_transfer_shutdown']=float(measured['remaining_overhead'] if absolute else estimate['remaining_overhead_seconds'])
    seconds=sum(components.values());already=used_cny(state);projected=already+seconds*active['hourly_cny']/3600
    receipt=dict(utc=c.utc(),bundle_sha256=state['bundle_manifest_sha256'],estimated_remaining_seconds=seconds,
        components_seconds=components,committed_work_discounts_seconds=discounts,actual_hourly_cny=active['hourly_cny'],
        runtime_estimate_mode='actual_gpu_absolute' if absolute else 'historical_v1_comparison',
        measured_training_slowdown=train_factor,measured_inference_slowdown=inference_factor,
        already_used_cny=already,estimated_total_compute_cny=projected,operating_line_cny=state['operating_line_cny'],
        shutdown_unknown_reserve_cny=2,remaining_budget_gap_cny=max(0.,projected-state['operating_line_cny']),
        fits_complete_frozen_run=projected<=state['operating_line_cny'],formal_optimizer_updates_permitted=projected<=state['operating_line_cny'])
    c.put(work/'whole_run_budget_gate.json',receipt)
    if not receipt['fits_complete_frozen_run']:raise TimeoutError('Whole two-arm training/evaluation/save cannot fit; no formal training; report gap and stop billing')
    return receipt


def preflight(bundle,model_dir,work):
    bundle=Path(bundle);model_dir=Path(model_dir);work=Path(work);verify_bundle(bundle)
    free=shutil.disk_usage(work if work.exists() else work.parent).free
    if free<8*1024**3:raise RuntimeError('Need8GiB existing scratch for two arms rolling checkpoints/results; do not purchase storage')
    sys.path.insert(0,str(bundle/'tasks/105_brief_supervision'))
    from verify105 import weights
    result=weights(model_dir,c.read(bundle/'frozen/weights_manifest.json'))
    versions={}
    for name,wanted in c.read(bundle/'frozen/environment_versions.json').items():
        try:actual=md.version(name)
        except md.PackageNotFoundError:actual=None
        versions[name]=dict(expected=wanted,actual=actual)
    if any(v['expected']!=v['actual'] for v in versions.values()):raise RuntimeError('Pinned105 environment differs: '+c.canonical(versions))
    from tokenizer_cpu105 import CPUPinnedTokenizer
    from data105 import encode,shared
    tok=CPUPinnedTokenizer(model_dir)
    expected={(r['arm'],r['id']):r for r in c.rows(bundle/'frozen/train_token_lengths.jsonl')}
    files=[bundle/'data/train'/(arm+'.jsonl') for arm in c.ARMS]
    if c.sha(files[0])!=c.sha(files[1]):raise ValueError('The two arms do not use byte-identical original196 data')
    for arm,file in zip(c.ARMS,files):
        rows=c.rows(file)
        if len(rows)!=196:raise ValueError('Expected original196')
        for row in rows:
            e=encode(tok,row);r=expected[(arm,row['id'])]
            if e['prompt_token_sha256']!=r['prompt_token_sha256'] or e['answer_sha256']!=r['answer_sha256'] or len(e['input_ids'])!=r['total_tokens'] or e['verdict_answer_token_indices']!=r['verdict_answer_token_indices']:raise ValueError('Training tokenizer bridge mismatch')
    lengths={r['id']:r for r in c.rows(bundle/'frozen/eval_token_lengths.jsonl')}
    for row in c.rows(bundle/'data/eval_inputs.jsonl'):
        if c.digest(c.canonical(shared.prompt_ids(tok,row)))!=lengths[row['id']]['prompt_token_sha256']:raise ValueError('Evaluation tokenizer bridge mismatch')
    if any(n=='torch' or n.startswith('torch.') or n=='transformers' or n.startswith('transformers.') for n in sys.modules):raise RuntimeError('No-GPU preflight imported model stack')
    result.update(task=107,bundle_sha256=c.sha(bundle/'manifest.json'),model_dir=str(model_dir.resolve()),versions=versions,
        tokenizer_bridge_verified=True,model_loaded=False,existing_free_bytes=free,API_calls=0)
    c.put(work/'preflight107.json',result);return result


def watch(ledger):
    """Independent stop request; this cannot shut down or stop billing."""
    ledger=Path(ledger)
    while True:
        if (ledger.parent/'complete107.json').exists():return
        state=c.read(ledger)
        if used_cny(state)>=state['operating_line_cny']:
            c.put(ledger.parent/'stop_requested.json',dict(reason='budget_operating_line',utc=c.utc(),used_cny=used_cny(state)))
            c.put(ledger.parent/'MANUAL_SHUTDOWN_REQUIRED.json',dict(utc=c.utc(),billing_still_running=True,platform_shutdown_executed=False))
            # A flag cannot interrupt a long generate/kernel. Terminate only
            # our verified worker; its last atomic checkpoint/first receipts
            # remain intact. This still cannot stop platform GPU billing.
            lock=ledger.parent/'gpu_worker.lock'
            if lock.exists():
                pid=int(lock.read_text());cmdline=Path('/proc')/str(pid)/'cmdline'
                if cmdline.exists() and b'worker107.py' in cmdline.read_bytes():
                    os.kill(pid,signal.SIGTERM)
                    for unused in range(10):
                        if not cmdline.exists():break
                        time.sleep(1)
                    if cmdline.exists() and b'worker107.py' in cmdline.read_bytes():os.kill(pid,signal.SIGKILL)
                    c.put(ledger.parent/'budget_worker_stop.json',dict(utc=c.utc(),worker_pid=pid,
                        SIGTERM_sent=True,SIGKILL_after_10s_if_needed=True,platform_shutdown_executed=False,billing_still_running=True))
            return
        time.sleep(3)


def verify_fixed_outputs(bundle,work):
    bundle=Path(bundle);work=Path(work);bundle_sha=c.sha(bundle/'manifest.json')
    batches=c.read(bundle/'frozen/eval_batches.json')['batches'];count={}
    for arm in c.ARMS:
        done=c.read(work/'train'/arm/'training_done.json')
        if done['step']!=50 or done['consumed']!=392 or done['fingerprint']['bundle_manifest_sha256']!=bundle_sha:raise ValueError('Incomplete fixed training')
        records=[]
        for entry in batches:
            saved=c.read(work/'eval'/arm/'development'/f"batch-{entry['batch']:04d}.json")
            if saved['bundle_sha256']!=bundle_sha or saved['ids']!=entry['ids'] or [r['id'] for r in saved['records']]!=entry['ids'] or any(r['arm']!=arm for r in saved['records']):raise ValueError('Frozen batch mismatch')
            records+=saved['records']
        if len(records)!=500 or len({r['id'] for r in records})!=500:raise ValueError('Expected500 first receipts per arm')
        count[arm]=len(records)
    return dict(first_receipts=count,formal_training_steps_each=50,formal_consumption_each=392)


def execute(a):
    if not a.execute_rented_gpu:raise PermissionError('GPU execution waits for the user-rented-instance handoff and explicit CLI flag')
    if platform.system()!='Linux':raise RuntimeError('GPU execution is supplied Linux instance only')
    verify_bundle(a.bundle);session=verify_authorization(a.bundle,a.session)
    pre=c.read(a.work/'preflight107.json')
    if pre['bundle_sha256']!=c.sha(a.bundle/'manifest.json') or pre['model_dir']!=str(a.model_dir.resolve()):raise ValueError('Current no-GPU preflight required')
    ledger=a.work/'compute107.json'
    if ledger.exists():
        state=c.read(ledger)
        if state['session_sha256']!=c.sha(a.session):raise ValueError('Cannot reset or replace an existing cumulative billing ledger')
    else:
        c.put(ledger,dict(task=107,session_sha256=c.sha(a.session),cap_cny=20,API_cap_cny=0,
            bundle_manifest_sha256=c.sha(a.bundle/'manifest.json'),operating_line_cny=18,closed_sessions=[],
            active=dict(machine=platform.node(),hourly_cny=session['hourly_cny'],billing_start_epoch=session['billing_start_epoch'])))
    watcher=subprocess.Popen([sys.executable,str(Path(__file__)),'watch','--work',str(a.work)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base=[sys.executable,str(Path(__file__).with_name('worker107.py')),'--bundle',str(a.bundle),'--work',str(a.work),
        '--model-dir',str(a.model_dir),'--ledger',str(ledger),'--session',str(a.session),'--execute-rented-gpu']
    try:
        if not (a.work/'gpu_gate.json').exists():subprocess.run(base+['--mode','gate','--arm','support_aux'],check=True)
        require_whole_remaining(ledger,c.read(a.bundle/'frozen/cost_estimate.json'),c.read(a.work/'gpu_gate.json'))
        for arm in c.ARMS:
            command=base+['--mode','train','--arm',arm]
            if (a.work/'train'/arm/'resume.json').exists():command.append('--resume')
            subprocess.run(command,check=True)
            subprocess.run(base+['--mode','eval','--arm',arm],check=True)
        verified=verify_fixed_outputs(a.bundle,a.work)
        c.put(a.work/'complete107.json',dict(task=107,utc=c.utc(),bundle_sha256=c.sha(a.bundle/'manifest.json'),all_fixed_stages_complete=True,**verified))
    finally:
        c.put(a.work/'MANUAL_SHUTDOWN_REQUIRED.json',dict(utc=c.utc(),billing_still_running=True,platform_shutdown_executed=False,
            instruction='Save adapters/checkpoints/raw receipts, stop this instance in platform console; never release instance/delete retained disk. CPU analysis follows confirmed stopped billing.'))
        watcher.terminate()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['preflight','run','watch'])
    p.add_argument('--bundle',type=Path);p.add_argument('--model-dir',type=Path);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--session',type=Path);p.add_argument('--execute-rented-gpu',action='store_true');a=p.parse_args()
    if a.action=='watch':watch(a.work/'compute107.json');return
    if a.action=='preflight':print(c.canonical(preflight(a.bundle,a.model_dir,a.work)));return
    if a.session is None:p.error('The user-rented-instance session metadata is required')
    if not a.execute_rented_gpu or platform.system()!='Linux':raise PermissionError('Only explicitly handed-off Linux GPU execution is permitted')
    a.work.mkdir(parents=True,exist_ok=True);lock=a.work/'orchestrator107.lock'
    if lock.exists():
        pid=int(lock.read_text())
        try:os.kill(pid,0)
        except ProcessLookupError:lock.unlink()
        else:raise RuntimeError('Another107 supervisor is live')
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:execute(a)
    finally:lock.unlink()


if __name__=='__main__':main()
