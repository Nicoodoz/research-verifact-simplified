"""One user-requested interim check, using unchanged120 inference machinery.

Does not change/resume training or call an interim adapter the final369 model.
The legacy worker's ``final_adapter`` field names its input path only; here its
role is explicitly ``interim_diagnostic`` and the actual saved step is recorded.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
from extend120 import guarded_run, session_deadline


def resolve(value):
    p = Path(value)
    return p if p.is_absolute() else ROOT/p


def prepare(job_path):
    original = common.read(job_path)
    train = ROOT/'results'/original['name']/'train'
    pointer = common.read(train/'resume.json')
    source = train/pointer['slot']
    complete_path = source/'checkpoint_complete.json'
    complete = common.read(complete_path)
    if (common.sha(complete_path) != pointer['complete_sha256'] or
            (complete['step'], complete['consumed'], complete['fingerprint']) !=
            (pointer['step'], pointer['consumed'], pointer['fingerprint']) or
            not 1 <= pointer['step'] < 369):
        raise ValueError('A complete, actual interim120 checkpoint is required')
    if complete['fingerprint']['job'] != common.digest(common.canonical(original)):
        raise ValueError('Training configuration changed before interim check')
    step = pointer['step']
    name = f'midpoint_{step}_screen160'
    folder = ROOT/'data'/name
    adapter = ROOT/'diagnostics'/name/'adapter'
    if folder.exists() or adapter.exists():
        raise FileExistsError('One fixed interim checkpoint only; preserve the first check')
    adapter.mkdir(parents=True)
    for filename in ('adapter_model.safetensors', 'adapter_config.json', 'README.md'):
        if (source/filename).exists():
            shutil.copy2(source/filename, adapter/filename)
    common.put(adapter/'source_checkpoint.json', dict(step=step, consumed=pointer['consumed'],
               fingerprint=pointer['fingerprint'], checkpoint_role='interim_diagnostic'))
    screens = common.rows(resolve(original['screen_inputs_path']))
    lengths = {r['id']: r for r in common.rows(resolve(original['screen_lengths_path']))}
    if len(screens) != len({r['id'] for r in screens}) or len(screens) != 160:
        raise ValueError('The unchanged nested160 panel is required')
    inputs = []
    for row in screens:
        if {'GT', 'sid', 'panel', 'answer', 'verdict'} & set(row):
            raise ValueError('Interim inference input must remain GT-free')
        expected = lengths[row['id']]['prompt_token_sha256']
        if row.get('expected_prompt_sha256', expected) != expected:
            raise ValueError('Original prompt identity changed')
        inputs.append(dict(id=row['id'], claim=row['claim'], reference=row['reference'],
                           expected_prompt_sha256=expected))
    session_path = resolve(original['session_path'])
    session_deadline(common.read(session_path))
    folder.mkdir(parents=True)
    relative = folder.relative_to(ROOT).as_posix()
    common.frozen(folder/'session.json', session_path.read_bytes())
    common.frozen(folder/'inputs.jsonl', ''.join(common.canonical(r)+'\n' for r in inputs).encode())
    job = dict(name=name, task=120, candidate='full_pool_sft_interim',
        checkpoint_role='interim_diagnostic', checkpoint_step=step,
        model_dir=original['model_dir'], final_adapter=str(adapter),
        adapter_sha256=complete['files']['adapter_model.safetensors'],
        inputs_path=relative+'/inputs.jsonl', session_path=relative+'/session.json',
        session_sha256=common.sha(session_path), scope='screen160', ids=[r['id'] for r in inputs],
        target_N=160, prior_N=0, prior_invalid_N=0, N=160,
        max_seq_length=original['max_seq_length'], seed=original['seed'],
        evaluation=dict(batch_size=2, max_new_tokens=384, do_sample=False, num_beams=1,
                        repetition_penalty=1., parser='parse105.parse'),
        phase_limit_seconds=900, save_reserve_seconds=180,
        no_training=True, no_shutdown=True, first_receipts_only=True,
        reason='User requested early real classification check before remaining training')
    common.put(folder/'job.json', job)
    result = dict(name=name, checkpoint_step=step, consumed=pointer['consumed'],
                  job_path=str(folder/'job.json'), output_path=str(ROOT/'results'/name),
                  checkpoint_role='interim_diagnostic', N=160, no_training=True)
    common.put(ROOT/'results'/original['name']/'interim_check_prepared.json', result)
    print(common.canonical(result))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run'))
    p.add_argument('--job', type=Path, required=True)
    a = p.parse_args()
    path = resolve(a.job)
    if a.action == 'prepare':
        prepare(path)
    else:
        value = common.read(path)
        if value.get('checkpoint_role') != 'interim_diagnostic' or not 1 <= value['checkpoint_step'] < 369:
            raise ValueError('Not an explicitly identified interim checkpoint')
        guarded_run(path)
