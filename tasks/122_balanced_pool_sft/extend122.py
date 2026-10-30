"""Conditional122 missing-ID preparation and reuse of the original120 inference.

Only explicit ``run`` can load a model. The unchanged shared worker retains its
legacy fingerprint task=120 implementation field; experiment_task=122 and the
fixed92-step122 adapter are bound in this job and a separate provenance record.
No receipt is rewritten, retried for content, or filled from another model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models/122_balanced_pool_sft'
sys.path.insert(0, str(ROOT/'tasks/120_full_pool_sft'))
import extend120 as shared
from extend_midpoint120 import make_runtime_session

common = shared.common
collect = shared.collect


def validate_final(done):
    if (done.get('steps'), done.get('consumed')) != (92, 729):
        raise ValueError('Only the actual fixed-final92/729122 checkpoint is eligible')
    if (done.get('fingerprint', {}).get('task'), done.get('fingerprint', {}).get('candidate')) != (122, 'balanced_pool_sft'):
        raise ValueError('Training completion is not balanced_pool_sft122')
    sha = done.get('adapter_sha256')
    if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha) or not done.get('final_checkpoint'):
        raise ValueError('Actual final122 adapter path and identity are required')
    return sha


def prepare(a):
    source = common.read(a.training_job)
    if (source.get('task'), source.get('candidate'), source['training']['N'],
            source['training']['total_steps']) != (122, 'balanced_pool_sft', 729, 92):
        raise ValueError('Source job must be the unchanged fixed122 training plan')
    done_path = a.training_result/'training_done.json' if a.training_result.is_dir() else a.training_result
    done = common.read(done_path)
    sha = validate_final(done)
    if done['fingerprint'].get('job') != common.digest(common.canonical(source)):
        raise ValueError('Training completion does not bind the frozen122 source job')
    keys = common.rows(a.keys)
    by_id = {r['id']: r for r in keys}
    if len(keys) != len(by_id) or len(keys) != 1817:
        raise ValueError('Expected the unique original1817 development cohort')
    if tuple(sum(r.get('old_panel') == p for r in keys) for p in ('natural', 'pressure')) != (400, 100):
        raise ValueError('Frozen400/100 panel membership differs')
    target = sorted(r['id'] for r in keys if a.scope == 'selection1817'
                    or r.get('old_panel') in ('natural', 'pressure'))
    prior = collect(a.prior)
    if not prior or any(r['source_adapter_sha256'] != sha for r in prior):
        raise ValueError('Prior first receipts must use the actual final122 adapter')
    needed = shared.remaining_ids(target, prior)
    all_inputs = common.rows(a.inputs)
    inputs = {r['id']: r for r in all_inputs}
    if len(inputs) != len(all_inputs) or set(inputs) != set(by_id):
        raise ValueError('Complete original1817 GT-free inputs differ')
    for r in all_inputs:
        if {'GT', 'human_gt', 'answer', 'verdict', 'panel', 'sid'} & set(r):
            raise ValueError('Inference input contains an evaluation label')
    for r in prior:
        if r['source_prompt_sha256_104'] != inputs[r['id']]['expected_prompt_sha256']:
            raise ValueError('Prior122 prompt differs from unchanged104/107 input')
    selected = [{key: inputs[i][key] for key in ('id', 'claim', 'reference', 'expected_prompt_sha256')}
                for i in needed]
    bundle = a.bundle.resolve()
    session_path = shared.resolve(source['session_path'])
    if not session_path.exists():
        session_path = bundle/source['session_path']
    session = common.read(session_path)
    if session['start_epoch'] != 1793321709 or session['duration_seconds'] != 21600:
        raise ValueError('This extension must retain the current08:55:09–14:55:09 session')
    session_bytes = session_path.read_bytes()
    metadata, suffix = {}, ''
    if a.resource_window:
        session, session_bytes, metadata, suffix = make_runtime_session(
            session, common.sha(session_path), a.resource_window)
    deadline = shared.session_deadline(session)
    relative = Path('data')/('balanced_pool_sft122_'+a.scope+suffix)
    folder = bundle/relative
    job = dict(name='balanced_pool_sft_'+a.scope+suffix, task=122, experiment_task=122,
        candidate='balanced_pool_sft', implementation_origin_task=120,
        shared_worker_fingerprint_task=120, final_training_steps=92, final_training_presentations=729,
        checkpoint_role='fixed_final92', training_completed_fingerprint=done['fingerprint'],
        model_dir=source['model_dir'], final_adapter=done['final_checkpoint'], adapter_sha256=sha,
        inputs_path=str(relative/'inputs.jsonl').replace('\\', '/'),
        session_path=str(relative/'session.json').replace('\\', '/'),
        session_sha256=common.digest(session_bytes.decode('utf-8')), training_done_sha256=common.sha(done_path),
        scope=a.scope, ids=needed, N=len(needed), target_N=len(target), prior_N=len(prior),
        prior_invalid_N=sum(not r['valid'] for r in prior),
        max_seq_length=source['max_seq_length'], seed=source['seed'],
        evaluation=dict(batch_size=2, max_new_tokens=384, do_sample=False, num_beams=1,
                        repetition_penalty=1., parser='parse105.parse'),
        phase_limit_seconds=source['phase_limit_seconds'], save_reserve_seconds=180,
        no_training=True, no_shutdown=True, first_receipts_only=True)
    job.update(metadata)
    folder.mkdir(parents=True, exist_ok=True)
    common.frozen(folder/'session.json', session_bytes)
    common.frozen(folder/'inputs.jsonl', ''.join(common.canonical(r)+'\n' for r in selected).encode('utf-8'))
    common.frozen(folder/'job.json', (json.dumps(job, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    summary = dict(scope=a.scope, target_N=len(target), prior_N=len(prior), new_calls=len(needed),
                   invalid_first_receipts_not_retried=job['prior_invalid_N'],
                   job_path=str(folder/'job.json'), session_deadline_epoch=deadline,
                   final_training_steps=92, final_training_presentations=729,
                   shared_worker_unchanged=True, GPU_started=False)
    common.put(PRIVATE/('extension_'+a.scope+suffix+'_prepared.json'), summary)
    print(common.canonical(summary))


def run(job_path):
    if sys.platform != 'linux':
        raise RuntimeError('Explicit GPU run belongs only on the authorized Linux instance')
    job_path = shared.resolve(job_path)
    job = common.read(job_path)
    if (job.get('task'), job.get('candidate'), job.get('final_training_steps'),
            job.get('final_training_presentations'), job.get('checkpoint_role')) != (122, 'balanced_pool_sft', 92, 729, 'fixed_final92'):
        raise ValueError('Not a fixed final122 extension job')
    if (job.get('training_completed_fingerprint', {}).get('task'),
            job.get('training_completed_fingerprint', {}).get('candidate')) != (122, 'balanced_pool_sft'):
        raise ValueError('Missing actual122 training-completion fingerprint')
    # Shared worker preserves its exact original metadata; this sidecar states
    # the scientific experiment without editing any first raw receipt.
    provenance = dict(experiment_task=122, candidate='balanced_pool_sft', steps=92,
                      presentations=729, adapter_sha256=job['adapter_sha256'],
                      checkpoint_role='fixed_final92',
                      training_completed_fingerprint=job['training_completed_fingerprint'],
                      shared_implementation_task=120, job_sha256=common.sha(job_path))
    common.frozen(ROOT/'results'/job['name']/'experiment122.json',
                  (json.dumps(provenance, indent=2)+'\n').encode('utf-8'))
    shared.guarded_run(job_path)


def self_test():
    good = dict(steps=92, consumed=729, adapter_sha256='a'*64, final_checkpoint='/synthetic',
                fingerprint=dict(task=122, candidate='balanced_pool_sft'))
    assert validate_final(good) == 'a'*64
    for change in (dict(steps=91), dict(consumed=728), dict(fingerprint={'task': 120, 'candidate': 'full_pool_sft'})):
        try:
            validate_final(dict(good, **change))
        except ValueError:
            continue
        raise AssertionError('Wrong checkpoint was accepted')
    assert shared.remaining_ids(['a', 'b', 'c'], [dict(id='a', valid=False), dict(id='b', valid=True)]) == ['c']
    session = dict(start_epoch=1793321709, duration_seconds=21600, GPU_cap_CNY=9.48,
                   hourly_CNY=1.58, no_shutdown=True)
    assert shared.session_deadline(session) == 1793343309
    print(common.canonical(dict(PASS=True, final92_729_checked=True, invalid_not_retried=True,
                               original_session_deadline=True, GPU_started=False)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('self-test')
    a = sub.add_parser('prepare')
    a.add_argument('--scope', choices=('old500', 'selection1817'), required=True)
    a.add_argument('--training-result', type=Path, required=True)
    a.add_argument('--prior', type=Path, nargs='+', required=True)
    a.add_argument('--training-job', type=Path, default=PRIVATE/'job.json')
    a.add_argument('--bundle', type=Path, default=PRIVATE/'bundle')
    a.add_argument('--resource-window', type=Path,
                   help='Optional explicit new authorization; preserves old job/session and cumulative ledger')
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
