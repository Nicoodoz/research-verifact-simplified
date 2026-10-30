"""CPU packaging only for the unchanged120 scientific plan's saved220 endpoint."""
from pathlib import Path
import ast
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models/120_full_pool_sft'
SOURCE = PRIVATE/'bundle'
OUT = PRIVATE/'resume369'
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
from extend_midpoint120 import make_runtime_session


def main():
    bundle = OUT/'bundle'
    if bundle.exists():
        raise FileExistsError('Preserve the prepared isolated continuation package')
    pointer = common.read(PRIVATE/'evidence/full_pool_sft/train/resume.json')
    source_checkpoint = PRIVATE/'evidence/full_pool_sft/train'/pointer['slot']
    complete = common.read(source_checkpoint/'checkpoint_complete.json')
    if (pointer['step'], pointer['consumed']) != (220, 1760) or complete['fingerprint'] != pointer['fingerprint']:
        raise ValueError('A real complete220/1760 checkpoint is required')
    if 'training_state.pt' not in complete['files'] or not (source_checkpoint/'training_state.pt').is_file():
        raise FileNotFoundError('Complete Adam/scheduler/RNG state is unavailable')
    job_path = SOURCE/'data/full_pool_sft120.json'
    job = common.read(job_path)
    files = ['data/full_pool_sft120.json', 'tasks/120_full_pool_sft/worker120.py',
             'tasks/120_full_pool_sft/run120.py', 'tasks/104_supervision_evidence/training104.py',
             'tasks/105_brief_supervision/common105.py', 'tasks/105_brief_supervision/data105.py',
             'tasks/105_brief_supervision/loss105.py', 'tasks/105_brief_supervision/parse105.py',
             'tasks/107_support_aux/checkpoint107.py']
    files += ['data/full_pool_sft120/'+name for name in
              ('train.jsonl', 'lengths.jsonl', 'plan.json', 'screen.jsonl', 'screen_lengths.jsonl')]
    for relative in files:
        destination = bundle/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE/relative, destination)
    destination = bundle/'tasks/120_full_pool_sft/resume369.py'
    shutil.copyfile(ROOT/'tasks/120_full_pool_sft/resume369.py', destination)
    ast.parse(destination.read_text(encoding='utf-8'))
    original_session = SOURCE/job['session_path']
    authorization = ROOT/'.local_models/122_balanced_pool_sft/resource_extension_active.json'
    runtime, body, metadata, _ = make_runtime_session(common.read(original_session), common.sha(original_session), authorization)
    (bundle/job['session_path']).write_bytes(body)
    meta = bundle/'resume_metadata'
    meta.mkdir()
    shutil.copyfile(original_session, meta/'original_session.json')
    shutil.copyfile(authorization, meta/'resource_extension.json')
    identity = dict(task=120, candidate='full_pool_sft', train=common.sha(bundle/job['train_path']),
        job=common.digest(common.canonical(job)), source107=job['source_adapter_sha256'],
        code=common.sha(bundle/'tasks/120_full_pool_sft/worker120.py'))
    if identity != pointer['fingerprint']:
        raise ValueError('Copied scientific files do not match the saved220 fingerprint')
    if common.sha(bundle/'data/full_pool_sft120.json') != common.sha(job_path):
        raise AssertionError('Original job bytes changed')
    recipe = dict(expected_fingerprint=identity, source_checkpoint_complete=complete,
        original_step=220, original_presentations=1760, fixed_target_step=369,
        fixed_total_presentations=2945, remaining_steps=149, remaining_presentations=1185,
        original_job_and_worker_bytes_preserved=True, old_session_sha256=metadata['old_session_sha256'],
        resource_authorization_sha256=metadata['resource_authorization_sha256'],
        runtime_deadline_epoch=runtime['deadline_epoch'], checkpoint_weights_not_in_archive=True,
        remote_checkpoint_reuse='/root/autodl-tmp/verifact120/results/full_pool_sft/train',
        no_new_training_started=True)
    common.put(meta/'recipe.json', recipe)
    archive = OUT/'bundle_resume369.tar.gz'
    with tarfile.open(archive, 'w:gz', compresslevel=1) as tar:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(bundle).as_posix(), recursive=False)
    summary = dict(status='CPU_PREPARED_NOT_STARTED', archive=str(archive), bytes=archive.stat().st_size,
        remote_unpack_directory='/root/autodl-tmp/verifact120_resume369',
        stage_command='python tasks/120_full_pool_sft/resume369.py stage',
        run_command='python -u tasks/120_full_pool_sft/resume369.py run',
        scientific_fingerprint_unchanged=True, optimizer_rng_copy_planned_on_instance=True,
        original_220_step_log_copied_at_stage=True,
        old220_source_preserved=True, runtime_deadline=runtime['deadline_beijing'],
        new_GPU=False, new_API=False)
    common.put(OUT/'preparation.json', summary)
    print(common.canonical(summary))


if __name__ == '__main__':
    main()
