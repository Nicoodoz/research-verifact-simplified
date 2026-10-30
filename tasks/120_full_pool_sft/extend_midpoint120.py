"""Prepare fixed220-step120 extensions; reuse original inference and time guard.

This is an interim diagnostic checkpoint, never a completed369-step model.
Only explicit ``run`` loads the model. No training or original receipt edits.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

import extend120 as shared

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models/120_full_pool_sft'
common = shared.common


def make_runtime_session(original, old_sha, resource_path):
    """Use a new explicit authorization without altering the frozen source session."""
    resource_path = Path(resource_path).resolve()
    authorization = common.read(resource_path)
    for key in ('start_epoch', 'duration_seconds', 'hourly_CNY', 'GPU_cap_CNY'):
        value = authorization.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError('Invalid resource authorization: '+key)
    if not authorization.get('authorization') or authorization.get('no_shutdown') is not True:
        raise ValueError('An explicit user authorization with no_shutdown is required')
    if (authorization.get('API_budget_reset') is not False
            or authorization.get('older_windows_retained_separately') is not True
            or authorization.get('previous_window_start_epoch') != original['start_epoch']
            or authorization.get('previous_window_closed_epoch') != authorization['start_epoch']):
        raise ValueError('Resource extension must preserve the old ledger and API budget')
    end = authorization['start_epoch']+authorization['duration_seconds']
    if authorization.get('deadline_epoch') != end or authorization['start_epoch'] < original['start_epoch']:
        raise ValueError('Resource authorization deadline is inconsistent')
    if (authorization.get('API_cap_CNY') != original.get('API_cap_CNY')
            or not 0 <= authorization.get('API_used_CNY', -1) <= authorization['API_cap_CNY']):
        raise ValueError('Cumulative API cap/usage must not be reset')
    reference = str(resource_path)
    metadata = dict(old_session_sha256=old_sha, resource_authorization_ref=reference,
                    resource_authorization_sha256=common.sha(resource_path))
    runtime = dict(authorization, **metadata)
    shared.session_deadline(runtime)
    suffix = '_window'+str(int(runtime['start_epoch']))
    encoded = (json.dumps(runtime, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    return runtime, encoded, metadata, suffix


def validate220(source, pointer, complete):
    if (source.get('task'), source.get('candidate'), source.get('checkpoint_role'),
            source.get('checkpoint_step')) != (120, 'full_pool_sft_interim', 'interim_diagnostic', 220):
        raise ValueError('Expected the actual fixed220 interim diagnostic job')
    if (pointer.get('step'), pointer.get('consumed')) != (220, 1760):
        raise ValueError('Saved training pointer is not220 steps/1760 presentations')
    if (complete.get('step'), complete.get('consumed')) != (220, 1760):
        raise ValueError('Checkpoint manifest is not220 steps/1760 presentations')
    fp = complete.get('fingerprint', {})
    if fp != pointer.get('fingerprint') or (fp.get('task'), fp.get('candidate')) != (120, 'full_pool_sft'):
        raise ValueError('Saved checkpoint and training pointer fingerprints differ')
    sha = complete.get('files', {}).get('adapter_model.safetensors')
    if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha) or sha != source.get('adapter_sha256'):
        raise ValueError('Midpoint job does not use the saved220 adapter')
    return sha


def prepare(a):
    source = common.read(a.source_job)
    pointer = common.read(a.training_root/'resume.json')
    checkpoint = a.training_root/pointer['slot']
    manifest_path = checkpoint/'checkpoint_complete.json'
    complete = common.read(manifest_path)
    sha = validate220(source, pointer, complete)
    if common.sha(manifest_path) != pointer['complete_sha256']:
        raise ValueError('Training pointer does not bind this checkpoint manifest')
    if common.sha(checkpoint/'adapter_model.safetensors') != sha:
        raise ValueError('Actual local220 adapter differs from saved manifest')
    initial_identity = common.read(a.initial_results/'identity.json')
    initial_complete = common.read(a.initial_results/'complete.json')
    if (initial_identity.get('job_sha256') != common.sha(a.source_job)
            or initial_identity.get('adapter_sha256') != sha
            or initial_complete.get('adapter_sha256') != sha or initial_complete.get('N') != 160):
        raise ValueError('Original160 results do not match the actual midpoint job/adapter')
    initial = shared.collect([a.initial_results])
    if (len(initial) != 160 or len(source['ids']) != 160
            or set(r['id'] for r in initial) != set(source['ids'])
            or any(r['source_adapter_sha256'] != sha for r in initial)):
        raise ValueError('Original160 first receipts are incomplete or use another checkpoint')
    keys = common.rows(a.keys)
    key_ids = {r['id'] for r in keys}
    if len(keys) != len(key_ids) or len(keys) != 1817:
        raise ValueError('Require the complete unique1817 development cohort')
    if tuple(sum(r.get('old_panel') == p for r in keys) for p in ('natural', 'pressure')) != (400, 100):
        raise ValueError('Original400/100 panel membership changed')
    target = sorted(r['id'] for r in keys if a.scope == 'selection1817'
                    or r.get('old_panel') in ('natural', 'pressure'))
    prior = shared.collect(a.prior or [a.initial_results])
    if not set(source['ids']) <= {r['id'] for r in prior} or any(r['source_adapter_sha256'] != sha for r in prior):
        raise ValueError('All original160 and any continuation must use the same220 adapter')
    needed = shared.remaining_ids(target, prior)
    all_inputs = common.rows(a.inputs)
    inputs = {r['id']: r for r in all_inputs}
    if len(inputs) != len(all_inputs) or set(inputs) != key_ids:
        raise ValueError('Original1817 inference inputs differ')
    if any({'GT', 'human_gt', 'answer', 'verdict', 'panel', 'sid'} & set(r) for r in all_inputs):
        raise ValueError('Inference inputs must be GT-free')
    if any(r['source_prompt_sha256_104'] != inputs[r['id']]['expected_prompt_sha256'] for r in prior):
        raise ValueError('A previous prompt differs from the unchanged104 input')
    selected = [{key: inputs[i][key] for key in ('id', 'claim', 'reference', 'expected_prompt_sha256')}
                for i in needed]
    session = common.read(a.session)
    if (common.sha(a.session) != source['session_sha256']
            or session['start_epoch'] != 1793321709 or session['duration_seconds'] != 21600):
        raise ValueError('Retain the original08:55:09–14:55:09 session; never reset budget')
    session_bytes = a.session.read_bytes()
    metadata, suffix = {}, ''
    if a.resource_window:
        session, session_bytes, metadata, suffix = make_runtime_session(
            session, source['session_sha256'], a.resource_window)
    deadline = shared.session_deadline(session)
    relative = Path('data')/('midpoint_220_'+a.scope+suffix)
    folder = a.bundle.resolve()/relative
    job = dict(name='midpoint_220_'+a.scope+suffix, task=120, experiment_task=120,
        candidate='full_pool_sft_interim', checkpoint_role='interim_diagnostic',
        checkpoint_step=220, training_presentations=1760, training_completed=False,
        planned_training_steps=369, training_saved_fingerprint=complete['fingerprint'],
        model_dir=source['model_dir'], final_adapter=source['final_adapter'],
        adapter_argument_role='fixed_interim220_not_final369', adapter_sha256=sha,
        inputs_path=str(relative/'inputs.jsonl').replace('\\', '/'),
        session_path=str(relative/'session.json').replace('\\', '/'),
        session_sha256=common.digest(session_bytes.decode('utf-8')), source_diagnostic_job_sha256=common.sha(a.source_job),
        scope=a.scope, ids=needed, N=len(needed), target_N=len(target), prior_N=len(prior),
        prior_invalid_N=sum(not r['valid'] for r in prior),
        max_seq_length=source['max_seq_length'], seed=source['seed'],
        evaluation=dict(batch_size=2, max_new_tokens=384, do_sample=False, num_beams=1,
                        repetition_penalty=1., parser='parse105.parse'),
        phase_limit_seconds=1800 if a.scope == 'old500' else 4200, save_reserve_seconds=180,
        no_training=True, no_shutdown=True, first_receipts_only=True)
    job.update(metadata)
    folder.mkdir(parents=True, exist_ok=True)
    common.frozen(folder/'session.json', session_bytes)
    common.frozen(folder/'inputs.jsonl', ''.join(common.canonical(r)+'\n' for r in selected).encode('utf-8'))
    common.frozen(folder/'job.json', (json.dumps(job, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    summary = dict(scope=a.scope, target_N=len(target), prior_N=len(prior), new_calls=len(needed),
        invalid_first_receipts_not_retried=job['prior_invalid_N'], checkpoint_step=220,
        training_presentations=1760, training_completed=False, adapter_sha256=sha,
        phase_limit_seconds=job['phase_limit_seconds'], session_deadline_epoch=deadline,
        job_path=str(folder/'job.json'), original160_unchanged=True, GPU_started=False)
    common.put(PRIVATE/('midpoint220_'+a.scope+suffix+'_prepared.json'), summary)
    print(common.canonical(summary))


def run(job_path):
    if sys.platform != 'linux':
        raise RuntimeError('Explicit GPU run belongs only on the authorized Linux instance')
    job_path = shared.resolve(job_path)
    job = common.read(job_path)
    if (job.get('task'), job.get('candidate'), job.get('checkpoint_role'), job.get('checkpoint_step'),
            job.get('training_presentations'), job.get('training_completed')) != (
            120, 'full_pool_sft_interim', 'interim_diagnostic', 220, 1760, False):
        raise ValueError('Not the fixed220 interim extension')
    phase_limit = {'old500': 1800, 'selection1817': 4200}.get(job['scope'])
    if job['phase_limit_seconds'] != phase_limit:
        raise ValueError('Fixed extension stage limit changed')
    common.frozen(ROOT/'results'/job['name']/'interim220.json',
        (json.dumps({k: job[k] for k in ('experiment_task', 'candidate', 'checkpoint_role', 'checkpoint_step',
          'training_presentations', 'training_completed', 'training_saved_fingerprint', 'adapter_sha256')}, indent=2)+'\n').encode('utf-8'))
    shared.guarded_run(job_path)


def self_test():
    source = dict(task=120, candidate='full_pool_sft_interim', checkpoint_role='interim_diagnostic',
                  checkpoint_step=220, adapter_sha256='a'*64)
    fp = dict(task=120, candidate='full_pool_sft')
    pointer = dict(step=220, consumed=1760, fingerprint=fp)
    manifest = dict(pointer, files={'adapter_model.safetensors': 'a'*64})
    assert validate220(source, pointer, manifest) == 'a'*64
    for bad in (dict(pointer, step=369), dict(pointer, consumed=2945), dict(pointer, step=192)):
        try:
            validate220(source, bad, manifest)
        except ValueError:
            continue
        raise AssertionError('Wrong training point accepted')
    assert shared.remaining_ids(['a', 'b', 'c'], [dict(id='a', valid=False), dict(id='b', valid=True)]) == ['c']
    print(common.canonical(dict(PASS=True, fixed220_1760_only=True, never_claim_final369=True,
                               invalid_first_receipts_not_retried=True, GPU_started=False)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('self-test')
    a = sub.add_parser('prepare')
    a.add_argument('--scope', choices=('old500', 'selection1817'), required=True)
    a.add_argument('--source-job', type=Path, default=PRIVATE/'midpoint220_job.json')
    a.add_argument('--training-root', type=Path, default=PRIVATE/'evidence/full_pool_sft/train')
    a.add_argument('--initial-results', type=Path, default=PRIVATE/'evidence/midpoint_220_screen160')
    a.add_argument('--prior', type=Path, nargs='+')
    a.add_argument('--bundle', type=Path, default=PRIVATE/'bundle')
    a.add_argument('--session', type=Path, default=PRIVATE/'bundle/data/full_pool_sft120/session.json')
    a.add_argument('--resource-window', type=Path,
                   help='Optional explicit new authorization; creates a separately named runtime job/session')
    a.add_argument('--keys', type=Path, default=ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    a.add_argument('--inputs', type=Path, default=ROOT/'.local_models/116_research_cycle/inputs_selection1817.jsonl')
    sub.add_parser('run').add_argument('--job', type=Path, required=True)
    args = p.parse_args()
    if args.action == 'prepare':
        prepare(args)
    elif args.action == 'self-test':
        self_test()
    else:
        run(args.job)


if __name__ == '__main__':
    main()
