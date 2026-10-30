"""Prepare the frozen107 empty-reference diagnostic; no model execution."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/123_claim_only_control'
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as common
from tokenizer_cpu105 import CPUPinnedTokenizer
sys.path.insert(0, str(ROOT / 'tasks/104_supervision_evidence'))
import training104 as original

JOB_NAME = 'features123_claim_only'
PREFIX_IDS = [4754, 415, 8217, 3147]
SOURCE_SHA = '096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8'


def unique(rows, name):
    result = {r['id']: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate IDs in ' + name)
    return result


def inputs_and_metadata():
    """Only the reference string changes; do not use outcome-dependent selection."""
    metadata = common.rows(ROOT / '.local_models/117_verdict_probe/metadata_fulltrain.jsonl')
    by_id = unique(metadata, 'full40 metadata')
    train = unique(common.rows(ROOT / '.local_models/106_label_preparation/training_pool.jsonl'), 'training pool')
    screen = unique(common.rows(ROOT / '.local_models/116_research_cycle/inputs_selection1817.jsonl'), 'selection inputs')
    keys = unique(common.rows(ROOT / '.local_models/116_research_cycle/keys_selection1817.jsonl'), 'selection keys')
    parts = {role: [r for r in metadata if r['role'] == role] for role in ('train', 'screen')}
    if len(metadata) != 5492 or tuple(map(len, parts.values())) != (3675, 1817):
        raise ValueError('Expected all3675 original training and1817 development IDs')
    if {r['id'] for r in parts['train']} != set(train) or {r['id'] for r in parts['screen']} != set(screen) or set(screen) != set(keys):
        raise ValueError('The matched full-reference ID sets changed')
    patients = {role: {str(r['sid']) for r in rows} for role, rows in parts.items()}
    roles = common.read(ROOT / 'outputs/103_lora_selection/patient_roles.json')['patients']
    if (patients['train'] != set(map(str, roles['train'])) or
            patients['screen'] != set(map(str, roles['selection'])) or patients['train'] & patients['screen']):
        raise ValueError('Original40/20 patient isolation changed')
    inputs = []
    for row in metadata:
        source = train[row['id']] if row['role'] == 'train' else keys[row['id']]
        if (row['GT'] not in common.LABELS or row['GT'] != source['GT'] or
                str(row['sid']) != str(source['sid'])):
            raise ValueError('Original GT or patient association changed')
        raw = train[row['id']] if row['role'] == 'train' else screen[row['id']]
        if not isinstance(raw['claim'], str) or not raw['claim'].strip():
            raise ValueError('An original complete claim is required')
        inputs.append(dict(id=row['id'], claim=raw['claim'], reference=''))
    if set(by_id) != {r['id'] for r in inputs}:
        raise AssertionError('Input association failed')
    return inputs, metadata, parts


def prepare(tokenizer_dir: Path):
    if (PRIVATE / 'preparation.json').exists():
        raise FileExistsError('Preserve the existing123 preparation; do not silently overwrite')
    inputs, metadata, parts = inputs_and_metadata()
    tokenizer = CPUPinnedTokenizer(tokenizer_dir)
    if tokenizer.encode('{"verdict":"', add_special_tokens=False) != PREFIX_IDS:
        raise ValueError('The original common prefix tokenization changed')
    lengths = []
    role = {r['id']: r['role'] for r in metadata}
    for row in inputs:
        token_ids = original.prompt_ids(tokenizer, row)
        row['expected_prompt_sha256'] = common.digest(common.canonical(token_ids))
        lengths.append(dict(id=row['id'], role=role[row['id']], prompt_tokens=len(token_ids),
                            input_tokens=len(token_ids) + len(PREFIX_IDS)))
    if max(r['input_tokens'] for r in lengths) > 16384:
        raise ValueError('A complete claim exceeds the original maximum; never truncate')
    source_job = common.read(ROOT / '.local_models/117_verdict_probe/features_initial.json')
    if source_job['adapter_sha256'] != SOURCE_SHA:
        raise ValueError('The frozen107 source changed')
    source_selection = common.read(ROOT / '.local_models/118_full_data_heads/reconsidered_refit/sqrt_weight_full/selection.json')
    config = source_selection['config']
    if (source_selection['fixed_epochs'] != 10 or source_selection['beta'] != .5 or
            any(config[k] != v for k, v in dict(hidden=128, dropout=.1, learning_rate=.001,
                weight_decay=.01, batch_size=64, seed=117, feature='verdict_prefix').items())):
        raise ValueError('The matched118 recipe changed')
    bundle = PRIVATE / 'bundle'
    data = bundle / 'data/claim_only123'
    job = dict(source_job, name=JOB_NAME, ids=[r['id'] for r in inputs],
               inputs='data/claim_only123/inputs.jsonl', batch_size=8, phase_limit_seconds=3600)
    common.putl(data / 'inputs.jsonl', inputs)
    common.putl(PRIVATE / 'metadata.jsonl', metadata)
    common.putl(PRIVATE / 'lengths.jsonl', lengths)
    common.put(bundle / 'data' / (JOB_NAME + '.json'), job)
    common.put(PRIVATE / (JOB_NAME + '.json'), job)
    # The117 controller retains the old window. Isolate123 without editing it.
    runtime = common.read(ROOT / '.local_models/122_balanced_pool_sft/runtime_session.json')
    resource = common.read(ROOT / '.local_models/122_balanced_pool_sft/resource_extension_active.json')
    if (runtime['start_epoch'] != 1793336266 or runtime['duration_seconds'] != 28800 or
            runtime['start_epoch'] != resource['start_epoch'] or runtime['API_cap_CNY'] != 80 or
            resource['API_budget_reset'] is not False):
        raise ValueError('Expected the authorized12:57:46--20:57:46 resource window without API reset')
    common.put(bundle / 'session.json', runtime)
    common.put(bundle / 'runtime_session.json', runtime)
    common.put(bundle / 'resource_extension_active.json', resource)
    for rel in ('tasks/117_verdict_probe/extract117.py', 'tasks/104_supervision_evidence/training104.py',
                'tasks/105_brief_supervision/common105.py'):
        dest = bundle / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)
    protocol = dict(task=123, name='claim_only_control', status='PREPARED_NOT_RUN',
        purpose='Matched input-ablation diagnostic; not a clinical deployment candidate',
        train_N=3675, train_patients=40, screen_N=1817, screen_patients=20,
        train_GT=dict(Counter(r['GT'] for r in parts['train'])),
        screen_GT=dict(Counter(r['GT'] for r in parts['screen'])),
        original_GT_unchanged=True, only_input_change="reference=''", full_claim=True,
        prompt='unchanged training104.prompt_ids', prefix_ids=PREFIX_IDS,
        frozen_backbone='107 label_only', adapter_sha256=SOURCE_SHA,
        GPU_training=False, dtype='bfloat16', extraction_batch_size=8,
        OOM_policy='existing extractor halves batch only; never truncates or discards inputs',
        matched_full_reference='118 sqrt_weight_full, seed117, epoch10',
        head=dict(config, fixed_epochs=10, beta=.5, epoch_selection='none; fixed10',
                  early_stopping=False),
        scaler_fit='all3675 training examples only', source_head_weights_reused=False,
        screen_used_for_selection=False, confirmation40_used=False,
        remote_root='/root/autodl-tmp/verifact123',
        session_policy='isolated123 copy of authorized122 runtime; old117 unchanged; no clock/API reset or shutdown',
        resource_start_epoch=runtime['start_epoch'], resource_deadline=runtime['deadline_beijing'],
        interpretation='Reference utility diagnostic under matched recipe; not causal proof of grounding',
        method_source='https://aclanthology.org/S18-2023/')
    common.put(PRIVATE / 'protocol.json', protocol)
    archive = PRIVATE / 'bundle123.tar.gz'
    with tarfile.open(archive, 'w:gz', compresslevel=1) as stream:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():
                stream.add(path, arcname=path.relative_to(bundle).as_posix(), recursive=False)
    token_values = sorted(r['input_tokens'] for r in lengths)
    summary = dict(status='PREPARED_NOT_RUN', N=len(inputs), train_N=3675, screen_N=1817,
        total_input_tokens=sum(token_values), min_input_tokens=token_values[0],
        median_input_tokens=token_values[len(token_values)//2], max_input_tokens=token_values[-1],
        p95_input_tokens=token_values[int(.95*(len(token_values)-1))],
        batches_at8=(len(inputs)+7)//8, bundle_bytes=archive.stat().st_size,
        expected_feature_bytes_two_positions=len(inputs)*4096*4*2,
        original_GT_unchanged=True, reference_empty_for_all=all(r['reference']=='' for r in inputs),
        GT_free_GPU_inputs=all(not {'GT','sid','panel','verdict','answer'} & set(r) for r in inputs),
        tokenizer=str(tokenizer_dir), new_GPU_calls=0, new_API_calls=0,
        remote_root='/root/autodl-tmp/verifact123', resource_start_epoch=runtime['start_epoch'],
        resource_deadline=runtime['deadline_beijing'])
    common.put(PRIVATE / 'preparation.json', summary)
    print(common.canonical(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tokenizer', type=Path, default=ROOT / '.local_models/103_lora_selection/models/qwen3.5-9b')
    prepare(parser.parse_args().tokenizer)
