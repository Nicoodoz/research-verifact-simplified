"""Stage an isolated220->369 continuation; explicit run delegates original code.

No old job, code, session, checkpoint, or receipt is modified. The new workspace
contains identical scientific files and a separate authorized resource session.
"""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common


def stage(source_results):
    recipe = common.read(ROOT/'resume_metadata/recipe.json')
    source_results = Path(source_results).resolve()
    out = ROOT/'results/full_pool_sft'
    if out.resolve() == source_results or out.resolve().is_relative_to(source_results):
        raise ValueError('Continuation output must be separate from original120 source')
    job = common.read(ROOT/'data/full_pool_sft120.json')
    identity = dict(task=120, candidate='full_pool_sft',
        train=common.sha(ROOT/job['train_path']), job=common.digest(common.canonical(job)),
        source107=job['source_adapter_sha256'], code=common.sha(ROOT/'tasks/120_full_pool_sft/worker120.py'))
    if identity != recipe['expected_fingerprint']:
        raise ValueError('Original scientific fingerprint was not preserved')
    session = common.read(ROOT/job['session_path'])
    if (session.get('old_session_sha256') != recipe['old_session_sha256']
            or session.get('resource_authorization_sha256') != recipe['resource_authorization_sha256']):
        raise ValueError('Separate runtime session is not bound to the declared authorization')
    source_train = source_results/'train'
    source_pointer = common.read(source_train/'resume.json')
    if (source_pointer['step'], source_pointer['consumed'], source_pointer['fingerprint']) != (220, 1760, identity):
        raise ValueError('Use exactly the saved220/1760 source, never another step')
    source_checkpoint = source_train/source_pointer['slot']
    complete = common.read(source_checkpoint/'checkpoint_complete.json')
    if complete != recipe['source_checkpoint_complete']:
        raise ValueError('Source checkpoint identity differs from the original220 backup')
    if common.sha(source_checkpoint/'checkpoint_complete.json') != source_pointer['complete_sha256']:
        raise ValueError('Source pointer does not bind the complete220 manifest')
    if not (source_checkpoint/'training_state.pt').is_file():
        raise FileNotFoundError('Full optimizer/scheduler/RNG checkpoint is required')
    source_steps = common.rows(source_results/'steps.jsonl')
    if (len(source_steps) != 220 or [r.get('step') for r in source_steps] != list(range(1, 221))
            or source_steps[-1].get('consumed') != 1760):
        raise ValueError('Original committed log must contain steps1..220 ending at1760 presentations')
    work = out/'train'
    if (work/'resume.json').exists():
        existing = common.read(work/'resume.json')
        if existing['fingerprint'] != identity or not 220 <= existing['step'] <= 369:
            raise ValueError('Do not overwrite unrelated/invalid continuation state')
        copied = False
    else:
        if work.exists() and any(work.iterdir()):
            raise FileExistsError('Destination has uncommitted unrelated files')
        work.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_checkpoint, work/source_pointer['slot'])
        shutil.copyfile(source_train/'resume.json', work/'resume.json')
        shutil.copyfile(source_results/'steps.jsonl', out/'steps.jsonl')
        copied = True
        # Existing real gate can be reused on the same user-supplied instance.
        # It is not presented as a newly executed gate; if absent, original code
        # runs its own longest-sample gate while restoring the RNG afterwards.
        gate = source_results/'gpu_gate.json'
        if gate.exists() and common.read(gate).get('fingerprint') == identity:
            shutil.copyfile(gate, out/'gpu_gate.json')
    if not (out/'steps.jsonl').exists():
        if common.read(work/'resume.json')['step'] != 220:
            raise ValueError('A progressed continuation cannot silently lose its committed training log')
        shutil.copyfile(source_results/'steps.jsonl', out/'steps.jsonl')
    common.put(out/'continuation_provenance.json', dict(
        original_task=120, original_checkpoint_step=220, original_presentations=1760,
        fixed_target_step=369, no_extra_epoch_or_config=True, source_results=str(source_results),
        expected_fingerprint=identity, source220_left_unchanged=True,
        full_optimizer_scheduler_rng_copy_preserved=True, copied_source_now=copied,
        original_committed_log_steps=220, original_log_copied_without_rewriting=True,
        state_recovery_delegated_to_original_loader=True,
        resource_session_only_changed=True, training_completion_claimed=False))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'run'))
    parser.add_argument('--source-results', type=Path,
                        default=Path('/root/autodl-tmp/verifact120/results/full_pool_sft'))
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise RuntimeError('Stage/run is for the existing authorized Linux instance')
    out = stage(args.source_results)
    if args.action == 'stage':
        print(common.canonical(dict(staged=str(out), GPU_started=False))); return
    result = subprocess.run([sys.executable, '-B', '-u', str(ROOT/'tasks/120_full_pool_sft/run120.py'),
                             '--job', 'data/full_pool_sft120.json', '--resume'], cwd=ROOT)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
