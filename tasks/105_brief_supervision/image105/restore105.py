"""Restore standard105 paths from the private image; no GPU/startup/budget reset."""
from pathlib import Path
import json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
assert ROOT==Path('/root/verifact_image') and ROOT.stat().st_dev==Path('/').stat().st_dev
ready=json.loads((ROOT/'metadata/ready.json').read_text())
assert ready['status']=='READY_TO_SAVE_IMAGE'
DATA=Path('/root/autodl-tmp');WORK=DATA/'verifact105'
if not DATA.is_dir() or DATA.stat().st_dev==ROOT.stat().st_dev:raise RuntimeError('Existing separate AutoDL data mount required; do not fill system disk with results')
for name,script in [('supervisor.lock','run_all105.py'),('gpu_worker.lock','worker105.py')]:
    lock=WORK/'results'/name
    if lock.exists():
        try:
            pid=int(lock.read_text());command=Path('/proc')/str(pid)/'cmdline'
            if command.exists() and script.encode() in command.read_bytes():raise RuntimeError('105 worker is live; do not reconfigure its paths')
        except ValueError:raise RuntimeError('Unrecognized existing lock; inspect before restoration')
changes=[]
def link(target,source):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_symlink():
        if target.resolve()!=source.resolve():raise RuntimeError('Existing link points elsewhere: '+str(target))
        changes.append(dict(path=str(target),status='existing_image_link'));return
    if target.exists():
        if target.is_dir() and not any(target.iterdir()):target.rmdir()
        else:
            changes.append(dict(path=str(target),status='nonempty_existing_preserved'));return
    target.symlink_to(source,target_is_directory=source.is_dir());changes.append(dict(path=str(target),status='image_link_created'))
link(DATA/'verifact103/models/qwen3.5-9b',ROOT/'models/qwen3.5-9b')
link(DATA/'verifact103/venv103',ROOT/'envs/venv103')
link(WORK/'bundle',ROOT/'105/bundle')
WORK.mkdir(exist_ok=True)
launcher=WORK/'start105.sh'
if not launcher.exists():launcher.write_bytes((ROOT/'105/bundle/tasks/105_brief_supervision/start105.sh').read_bytes());launcher.chmod(0o700)
for name in ('results','budget'): (WORK/name).mkdir(exist_ok=True)
cache=WORK/'cache';cache.mkdir(exist_ok=True)
if not cache.resolve().is_relative_to(DATA.resolve()) or cache.stat().st_dev!=DATA.stat().st_dev:raise RuntimeError('Cache must remain on the data disk')
environment=WORK/'image_environment.sh'
cache_variables=dict(HF_HOME='huggingface',TORCH_HOME='torch',TORCHINDUCTOR_CACHE_DIR='torchinductor',
    TRITON_CACHE_DIR='triton',CUDA_CACHE_PATH='cuda',TORCH_EXTENSIONS_DIR='torch_extensions',XDG_CACHE_HOME='xdg')
lines=['# Image runtime caches; no model download or GPU startup.']
for variable,folder in cache_variables.items():
    path=cache/folder;path.mkdir(exist_ok=True);lines.append(f'export {variable}="{path}"')
lines.extend(['export HF_HUB_OFFLINE=1','export TRANSFORMERS_OFFLINE=1'])
if not environment.exists():environment.write_text('\n'.join(lines)+'\n')
image_launcher=WORK/'start_image105.sh'
if not image_launcher.exists():
    image_launcher.write_text('#!/bin/bash\nset -euo pipefail\nROOT=/root/autodl-tmp/verifact105\nsource "$ROOT/image_environment.sh"\ncd "$ROOT"\nexec bash "$ROOT/start105.sh" "$@"\n');image_launcher.chmod(0o700)
py=DATA/'verifact103/venv103/bin/python'
verify=WORK/'bundle/tasks/105_brief_supervision/verify105.py'
subprocess.run([str(py),'-B',str(verify),'--bundle',str(WORK/'bundle'),'--model-dir',str(DATA/'verifact103/models/qwen3.5-9b'),'--work',str(WORK/'results')],check=True)
ledger=WORK/'budget/ledger.json'
if not ledger.exists():
    note=('No new105 ledger initialized. Recover/reconcile the cumulative task105 ledger first. '
          'The prior cost/time/unknown reserve are in /root/verifact_image/105/cost_checkpoint. '
          'Do not reset20CNY or150minute limits when using a fresh image. '
          'This restoration command never starts training, GPU mode, or a paid instance.\n')
    (WORK/'budget/RECOVER_LEDGER_FIRST.txt').write_text(note)
result=dict(epoch=time.time(),status='PATHS_AND_CPU_PREFLIGHT_READY',changes=changes,live_ledger_exists=ledger.exists(),
    live_ledger_modified=False,training_started=False,model_loaded=False,instance_started_or_switched=False,
    results_path=str(WORK/'results'),budget_checkpoint=str(ROOT/'105/cost_checkpoint'),
    runtime_cache_path=str(cache),future_launcher=str(image_launcher),GPU_checks_still_required=True)
(WORK/'image_restore_receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
