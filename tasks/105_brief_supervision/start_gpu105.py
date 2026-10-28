"""Single next-stage launcher; CPU-only checks until a real GPU boot is present.

Never starts/switches/rents an instance. Price and prior billing-end confirmation
are operational inputs, not changes to the frozen experiment.
"""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
from datetime import datetime
import common105 as c
import budget105 as budget
from data105 import training_plan,validate_cursor
from verify105 import bundle as verify_bundle

def epoch(text):
    try:return float(text)
    except ValueError:
        value=datetime.fromisoformat(text)
        if value.tzinfo is None:raise ValueError('ISO billing time must include its timezone')
        return value.timestamp()

def boot_start():
    base=int(next(x.split()[1] for x in Path('/proc/stat').read_text().splitlines() if x.startswith('btime ')))
    ticks=int(Path('/proc/1/stat').read_text().split(') ',1)[1].split()[19])
    return base+ticks/os.sysconf('SC_CLK_TCK')

def active_pid(lock,needles):
    if not lock.exists():return False
    try:
        pid=int(lock.read_text().strip());path=Path('/proc')/str(pid)/'cmdline'
        text=path.read_bytes() if path.exists() else b''
    except (ValueError,OSError):text=b''
    if text and all(needle.encode() in text for needle in needles):return True
    # Preserve stale control evidence; never remove data, checkpoints or ledger.
    target=lock.with_name(lock.name+'.stale.'+str(time.time_ns()))
    lock.replace(target);return False

def remaining_hours(bundle,work):
    cost=c.read(bundle/'frozen/cost_estimate.json');total_tokens=0
    for arm in c.ARMS[1:]:
        rows=c.rows(bundle/'data/train'/(arm+'.jsonl'));ids=[r['id'] for r in rows]
        lengths={r['id']:r['total_tokens'] for r in c.rows(bundle/'frozen/train_token_lengths.jsonl') if r['arm']==arm}
        plan=training_plan(ids);pointer=work/'train'/arm/'resume.json'
        state=c.read(pointer) if pointer.exists() else dict(step=0,consumed=0)
        for step in validate_cursor(plan,state['step'],state['consumed']):total_tokens+=sum(lengths[i] for i in step['ids'])
    seconds=total_tokens/cost['historical_training_tokens_per_second']*1.35
    rates=dict(base_judge=cost['label_base_500_seconds']/500,label_only=cost['label_only_500_seconds']/500,
               evidence_brief=max(cost['conservative_brief_seconds'],cost['empirical_batch_fit']['projected_brief_seconds'])/500)
    for arm in c.ARMS:
        completed=set()
        for path in (work/'eval'/arm).glob('batch-*.json'):
            if '.inflight.' in path.name:continue
            saved=c.read(path)
            if saved['bundle_sha256']!=c.sha(bundle/'manifest.json'):raise ValueError('Existing evaluation belongs to another bundle')
            completed.update(r['id'] for r in saved['records'])
        seconds+=(500-len(completed))*rates[arm]
    return (seconds+cost['model_load_compile_checkpoint_backup_allowance_seconds'])*1.15/3600

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('/root/autodl-tmp/verifact105'))
    p.add_argument('--gpu-hourly',type=float,required=True);p.add_argument('--billing-start',type=epoch)
    p.add_argument('--previous-end',type=epoch,help='Platform-confirmed previous no-GPU stop time; never infer from SSH disconnect')
    p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    root=a.root.resolve();bundle=root/'bundle';work=root/'results';ledger=root/'budget/ledger.json'
    verify_bundle(bundle);check=c.read(work/'nogpu_preflight.json')
    assert check['bundle_sha256']==c.sha(bundle/'manifest.json') and check['all_weights_SHA_match']
    assert check['all_392_train_answer_maps_and_500_eval_prompt_tokens_verified']
    if a.gpu_hourly<0:raise ValueError('Use the actual nonnegative platform quote')
    state=c.read(ledger);previous=state.get('active');prior=sum(s['cost_cny'] for s in state['closed_sessions'])+state.get('adjustments_cny',0)
    if previous:
        if a.previous_end is not None:
            if not previous['billing_start_epoch']<=a.previous_end<=time.time():raise ValueError('Invalid platform-confirmed previous interval end')
            prior+=(a.previous_end-previous['billing_start_epoch'])/3600*previous['hourly_cny']
        else:prior=budget.total(state)
    hours=remaining_hours(bundle,work);projection=prior+hours*a.gpu_hourly
    summary=dict(ready_for_GPU=True,dry_run=a.dry_run,estimated_remaining_GPU_hours=hours,actual_quote_cny_per_hour=a.gpu_hourly,
                 prior_or_current_compute_estimate_cny=prior,projected_total_cny=projection,operating_line_cny=18,hard_cap_cny=20,
                 current_nvidia_devices=[str(x) for x in Path('/dev').glob('nvidia[0-9]*')],model_imported=False)
    if a.dry_run:print(c.canonical(summary));return
    if os.name!='posix' or not summary['current_nvidia_devices']:raise RuntimeError('GPU mode not present; do not switch modes automatically')
    if projection>18:raise RuntimeError('The complete fixed remaining task does not fit the operating line; do not shrink samples')
    if previous and a.previous_end is not None:
        budget.end(ledger,a.previous_end,True);previous=None
    if previous and (previous['kind']=='nogpu' or state.get('shutdown_requested') or boot_start()>previous['billing_start_epoch']+60):
        raise RuntimeError('Previous billing interval remains unconfirmed; supply --previous-end from platform')
    if previous and previous['kind']!='gpu':raise RuntimeError('Unexpected active billing mode')
    if previous and previous['hourly_cny']!=a.gpu_hourly:raise RuntimeError('Existing active GPU interval quote differs; settle it before a new interval')
    if not previous:budget.begin(ledger,'gpu',a.gpu_hourly,a.billing_start if a.billing_start is not None else boot_start())
    for lock,needles in [(work/'supervisor.lock',['run_all105.py']),(work/'gpu_worker.lock',['worker105.py'])]:
        if active_pid(lock,needles):raise RuntimeError('An existing task105 GPU worker/supervisor is already running')
    watch_lock=root/'budget/watchdog.lock'
    if not active_pid(watch_lock,['budget105.py','watch']):
        log=(root/'budget/watchdog_gpu.log').open('ab')
        subprocess.Popen([sys.executable,'-u',str(bundle/'tasks/105_brief_supervision/budget105.py'),'watch','--ledger',str(ledger)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True);log.close()
    for _ in range(40):
        try:budget.require(ledger,300,watchdog=True);break
        except (OSError,RuntimeError):time.sleep(.25)
    else:raise RuntimeError('Independent watchdog did not become ready; no model launched')
    log=(root/'run105.log').open('ab')
    env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',OMP_NUM_THREADS='8',MAX_JOBS='8',TORCHINDUCTOR_COMPILE_THREADS='8',TORCH_DISABLE_ADDR2LINE='1')
    proc=subprocess.Popen([sys.executable,'-u',str(bundle/'tasks/105_brief_supervision/run_all105.py'),'--bundle',str(bundle),'--work',str(work),
         '--model-dir',check['model_dir'],'--ledger',str(ledger)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=env);log.close()
    c.put(root/'start_receipt.json',dict(summary,supervisor_pid=proc.pid,utc=c.utc(),ledger=str(ledger),bundle_sha256=c.sha(bundle/'manifest.json')))
    print(c.canonical(dict(started=True,pid=proc.pid,log=str(root/'run105.log'),queue='gate -> train label_only -> train evidence_brief -> evaluate three arms -> save -> shutdown')))

if __name__=='__main__':main()
