"""Persist the one candidate's private result archive; no upload/cloud action."""
from pathlib import Path
import tarfile
import common109 as c

def collect(work):
    work=Path(work).resolve();pointer=c.read(work/'train/resume.json')
    done=c.read(work/'train/training_done.json')
    if pointer['step']!=24 or done['step']!=24 or pointer['fingerprint']!=done['fingerprint']:raise ValueError('Fixed final109 state required')
    folder=work/'train'/pointer['slot'];files=[]
    for name in ('identity.json','selected_manifest.jsonl','selection_summary.json','supported_request.json','train.jsonl','progress.json'):
        if (work/name).is_file():files.append(work/name)
    for phase in ('mining_a','mining_s','evaluation'):
        files.extend(p for p in (work/phase).glob('*') if p.is_file())
    for name in ('resume.json','training_done.json','gpu_gate.json','steps.jsonl'):files.append(work/'train'/name)
    files.extend(p for p in folder.iterdir() if p.is_file() and not p.name.endswith('.tmp'))
    files.extend(work.glob('*.log'));files.extend([work/'loads.jsonl'])
    files=sorted(set(files))
    if any(not p.resolve().is_relative_to(work) or not p.is_file() for p in files):raise ValueError('Return archive escaped/missing own result files')
    receipt=dict(task=109,final_step=24,global_step=74,checkpoint_slot=pointer['slot'],
        files={p.relative_to(work).as_posix():p.stat().st_size for p in files},
        includes_final_optimizer_scheduler_RNG=True,includes_private_clinical_material=True,
        include_credentials=False,include_original9B_weights=False,include_compiler_cache=False,
        storage='private_only_never_GitHub',GPU_billing_not_stopped_by_archiving=True)
    c.put(work/'return_manifest.json',receipt)
    archive=work/'return109.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for path in files+[work/'return_manifest.json']:tar.add(path,arcname=path.relative_to(work).as_posix(),recursive=False)
    c.put(work/'return_ready.json',dict(archive='return109.tar.gz',bytes=archive.stat().st_size,
        next='download_critical_results_and_stop_GPU_billing_after_tasks_end_per_user_instruction',private_only=True))
    return receipt

def collect_partial(work):
    """Keep real first mining receipts/last committed state even if quotas fail."""
    work=Path(work).resolve();files=[]
    for phase in ('mining_a','mining_s','evaluation'):
        files.extend(p for p in (work/phase).glob('*') if p.is_file())
    files.extend(work.glob('*.json'));files.extend(work.glob('*.jsonl'));files.extend(work.glob('*.log'))
    if (work/'train/resume.json').exists():
        pointer=c.read(work/'train/resume.json')
        if pointer['slot'] not in {'checkpoint_a','checkpoint_b'}:raise ValueError('Unsafe partial checkpoint slot')
        files.extend(p for p in (work/'train'/pointer['slot']).glob('*') if p.is_file())
        files.extend(p for p in (work/'train').glob('*') if p.is_file())
    files=[p for p in sorted(set(files)) if p.suffix not in {'.tmp','.gz'} and p.name!='SESSION_REQUIRED.template.json' and p.name!='session.json']
    if any(not p.resolve().is_relative_to(work) for p in files):raise ValueError('Partial archive escaped work')
    with tarfile.open(work/'partial_return109.tar.gz','w:gz',compresslevel=1) as tar:
        for path in files:tar.add(path,arcname=path.relative_to(work).as_posix(),recursive=False)
