"""Freeze the existing138 label-replay inputs for a KL-anchored update.

CPU only. Clinical inputs and model artifacts remain in .local_models.
"""
from pathlib import Path
from collections import Counter
import json, shutil, sys

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'tasks/105_brief_supervision'))
import common105 as c


def main():
    source = R / '.local_models/138_rationale_tasks/label_replay/bundle/data'
    target = R / '.local_models/140_kl_anchor/bundle/data'
    if (target / 'job.json').exists():
        raise RuntimeError('Frozen140 inputs already exist; preserve and inspect them')
    rows = c.rows(source / 'train_tokens.jsonl')
    raw = c.rows(source / 'train.jsonl')
    plan = c.read(source / 'plan.json')
    ev = c.rows(source / 'eval_tokens.jsonl')
    assert len(rows) == len(raw) == 192 and len(plan) == 48
    assert plan[-1]['consumed'] == 384 and len(ev) == 160
    assert all(x['kind'] == 'label' for x in rows)
    by_sample = {x['sample_id']: x for x in rows}
    assert len(by_sample) == 192
    assert set(by_sample) == {x['sample_id'] for x in raw}
    assert set(by_sample) == {i for p in plan for i in p['ids']}
    assert all(p['loss_divisor'] == 8 for p in plan)
    unique = {}
    for x in rows:
        assert len(x['input_ids']) == len(x['groups']) <= 16384
        assert 1 <= x['groups'].count(1) <= 3
        old = unique.setdefault(x['original_id'], x)
        assert old['input_ids'] == x['input_ids'] and old['groups'] == x['groups']
    assert len(unique) == 156
    train_patients = {str(x['sid']) for x in raw}
    keys = c.rows(R / '.local_models/134_author_baselines/keys.jsonl')
    eval_patients = {str(x['sid']) for x in keys}
    assert len(train_patients) == 32 and not train_patients & eval_patients
    assert not set(unique) & {x['id'] for x in keys}
    target.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in ['train_tokens.jsonl', 'train.jsonl', 'plan.json', 'eval_tokens.jsonl', 'session.json']:
        shutil.copy2(source / name, target / name)
        hashes[name] = c.sha(source / name)
        assert c.sha(target / name) == hashes[name]
    job = c.read(source / 'job.json')
    job.update(task=140, arm='kl_anchor', lambda_kl=0.5, temperature=1.0,
               phase_limit_seconds=4800, save_reserve_seconds=1200,
               reference_kind='120 final369 full-vocabulary conditional token distribution',
               matched_control='138 label_replay, same inputs/order/48updates/384presentations',
               compute_seconds=3600)
    c.put(target / 'job.json', job)
    c.put(target.parent.parent / 'job.json', job)
    summary = dict(status='CPU_INPUTS_FROZEN_NOT_RUN', task=140, arm='kl_anchor',
                   source='120 final369', source_sha256=job['source_sha256'],
                   original_training_patients=32, unique_train_IDs=156, slots=192,
                   presentations=384, updates=48, seed=138031,
                   slot_GT=dict(Counter(x['GT'] for x in raw)),
                   teacher_label_positions=sum(x['groups'].count(1) for x in unique.values()),
                   longest_training_tokens=max(len(x['input_ids']) for x in rows),
                   eval_N=160, lambda_kl=0.5, temperature=1.0,
                   matched_control='138 label_replay', unchanged_input_file_SHA256=hashes,
                   train_eval_patient_overlap=0, new_reason18_used=False,
                   compute_seconds=3600, save_reserve_seconds=1200,
                   maximum_phase_GPU_CNY=4800 * 1.58 / 3600, new_API_CNY=0,
                   classification_effect_tested=False, no_shutdown=True)
    c.put(target.parent.parent / 'prepared.json', summary)
    c.put(R / 'outputs/140_kl_anchor/preparation.json', summary)
    print(c.canonical(summary))


if __name__ == '__main__':
    main()
