"""Score frozen recovered119 prefix states at an explicitly fixed step, CPU only.

No fitting, GPU, language-model replay or GT access.  This requires complete
already-extracted states for the requested IDs and the recovered head files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/117_verdict_probe'
sys.path.insert(0, str(ROOT / 'tasks/117_verdict_probe'))
from learned_head117 import LearnedHead, LABELS, PREFIX_IDS

SELECTED_STEP = 128


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def requested_ids(path):
    value = read(path)
    values = value.get('screen_ids') if isinstance(value, dict) else value
    if (not isinstance(values, list) or not values or len(values) != len(set(values)) or
            any(not isinstance(i, str) or not i for i in values)):
        raise ValueError('Expected a frozen unique ID list or dict.screen_ids')
    return values


def load_recovered_head(npz_path, state_path, metadata_path, expected_step=SELECTED_STEP):
    metadata = read(metadata_path)
    if type(expected_step) is not int or expected_step < 0:
        raise ValueError('Expected step must be a nonnegative integer')
    if metadata.get('step') != expected_step:
        raise ValueError(f'This scorer requires the explicitly fixed{expected_step}-step checkpoint')
    adapter_sha = metadata['files']['adapter_model.safetensors']
    if not isinstance(adapter_sha, str) or len(adapter_sha) != 64:
        raise ValueError('Recovered checkpoint lacks its adapter identity')
    head = LearnedHead.from_npz(npz_path)
    if head.representation != 'verdict_prefix':
        raise ValueError('Recovered119 uses only the verdict-prefix representation')
    state = torch.load(state_path, map_location='cpu', weights_only=True)
    head.load_state_dict(state, strict=True)
    if any(not bool(torch.isfinite(value).all()) for value in head.state_dict().values()):
        raise ValueError('Recovered head contains nonfinite parameters or scaler buffers')
    head.eval()
    head_sha = hashlib.sha256(Path(state_path).read_bytes()).hexdigest()
    expected_head_sha = metadata['files'].get('aux_head.pt')
    if expected_head_sha and expected_head_sha != head_sha:
        raise ValueError('Recovered head file differs from its committed checkpoint')
    return head, adapter_sha, head_sha


def load_states(directories, ids, adapter_sha):
    wanted = set(ids)
    found, lengths = {}, {}
    for directory in directories:
        for path in sorted((Path(directory) / 'batches').glob('*.npz')):
            with np.load(path, allow_pickle=False) as batch:
                batch_ids = np.asarray(batch['ids']).astype(str).tolist()
                indices = [k for k, i in enumerate(batch_ids) if i in wanted]
                if not indices:
                    continue
                meta = read(path.with_suffix('.json'))
                if (meta.get('adapter_sha256') != adapter_sha or
                        tuple(meta.get('prefix_token_ids', ())) != PREFIX_IDS or
                        meta.get('ids') != batch_ids):
                    raise ValueError('Extracted states do not match the frozen recovered checkpoint/prefix')
                states = np.asarray(batch['verdict_prefix'], dtype=np.float32)
                if states.ndim != 2 or states.shape[0] != len(batch_ids):
                    raise ValueError('Feature rows and ID list do not align')
                tokens = meta.get('input_tokens', [None] * len(batch_ids))
                if len(tokens) != len(batch_ids):
                    raise ValueError('Input lengths do not align with the extracted batch')
                for k in indices:
                    identifier = batch_ids[k]
                    if identifier in found:
                        raise ValueError('Duplicate recovered feature ID: ' + identifier)
                    found[identifier] = states[k].copy()
                    lengths[identifier] = tokens[k]
    missing = wanted - set(found)
    if missing:
        raise ValueError(f'Missing{len(missing)} requested recovered states; do not fabricate predictions')
    return np.stack([found[i] for i in ids]), lengths


def score(features, ids_file, head_npz, head_state, checkpoint_meta, output, threads=4,
          expected_step=SELECTED_STEP):
    ids = requested_ids(ids_file)
    if Path(output).exists():
        raise FileExistsError('Preserve existing first scored receipts; choose a new output path')
    head, adapter_sha, head_sha = load_recovered_head(head_npz, head_state, checkpoint_meta, expected_step)
    states, lengths = load_states(features, ids, adapter_sha)
    torch.set_num_threads(threads)
    records = []
    with torch.inference_mode():
        for start in range(0, len(ids), 256):
            logits = head(torch.from_numpy(states[start:start + 256]))
            for identifier, values in zip(ids[start:start + 256], logits):
                record = dict(id=identifier, selected_step=expected_step,
                              checkpoint_adapter_sha256=adapter_sha, head_sha256=head_sha,
                              prediction_origin='recovered_checkpoint_prefix_states')
                if type(lengths[identifier]) is int:
                    record['input_tokens'] = lengths[identifier]
                if not bool(torch.isfinite(values).all()):
                    record.update(verdict=None, class_index=None, valid=False,
                                  probabilities=None, error='nonfinite_logits')
                else:
                    index = int(values.argmax())
                    probabilities = values.float().softmax(-1).tolist()
                    record.update(verdict=LABELS[index], class_index=index, valid=True,
                                  probabilities=dict(zip(LABELS, probabilities)),
                                  probabilities_calibrated=False)
                records.append(record)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.tmp')
    temporary.write_bytes(('\n'.join(json.dumps(row, ensure_ascii=False, allow_nan=False)
                                      for row in records) + '\n').encode('utf-8'))
    temporary.replace(output)
    return dict(N=len(records), valid=sum(row['valid'] for row in records),
                selected_step=expected_step, fit_performed=False, GPU_used=False,
                output=str(output))


def self_test():
    with tempfile.TemporaryDirectory(prefix='score119_') as temporary:
        root = Path(temporary)
        feature_dir = root / 'features/batches'
        feature_dir.mkdir(parents=True)
        npz_path, state_path = root / 'warm.npz', root / 'aux_head.pt'
        np.savez_compressed(npz_path, coef=np.zeros((3, 5)), intercept=np.zeros(3),
                            mean=np.zeros(5), scale=np.ones(5), classes=np.asarray(LABELS),
                            representation=np.asarray('verdict_prefix'))
        head = LearnedHead.from_npz(npz_path)
        with torch.no_grad():
            head.linear.bias.copy_(torch.tensor([-2., 3., -1.]))
        torch.save(head.state_dict(), state_path)
        head_sha = hashlib.sha256(state_path.read_bytes()).hexdigest()
        metadata = dict(step=128, files={'adapter_model.safetensors': 'a' * 64,
                                        'aux_head.pt': head_sha})
        meta_path = root / 'checkpoint_complete.json'
        meta_path.write_text(json.dumps(metadata), encoding='utf-8')
        ids_path = root / 'ids.json'
        ids_path.write_text(json.dumps(dict(screen_ids=['b', 'a'])), encoding='utf-8')
        np.savez_compressed(feature_dir / '0000.npz', ids=np.asarray(['a', 'b']),
                            verdict_prefix=np.ones((2, 5), dtype=np.float32))
        (feature_dir / '0000.json').write_text(json.dumps(dict(
            ids=['a', 'b'], adapter_sha256='a' * 64, prefix_token_ids=list(PREFIX_IDS),
            input_tokens=[100, 200])), encoding='utf-8')
        output = root / 'scored.jsonl'
        result = score([root / 'features'], ids_path, npz_path, state_path, meta_path, output, threads=1)
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        if ([row['id'] for row in rows] != ['b', 'a'] or
                any(row['verdict'] != LABELS[1] or row['class_index'] != 1 for row in rows)):
            raise AssertionError('Saved head or requested ID order was not used')
        if any({'GT', 'human_gt', 'claim', 'reference', 'content'} & set(row) for row in rows):
            raise AssertionError('Scored receipts must remain GT-free and text-free')
        metadata['step'] = 272
        meta_path.write_text(json.dumps(metadata), encoding='utf-8')
        try:
            load_recovered_head(npz_path, state_path, meta_path)
        except ValueError:
            pass
        else:
            raise AssertionError('A different checkpoint was mislabeled as step128')
        metadata['step'] = 369
        meta_path.write_text(json.dumps(metadata), encoding='utf-8')
        terminal = score([root / 'features'], ids_path, npz_path, state_path, meta_path,
                         root / 'fixed369.jsonl', threads=1, expected_step=369)
        if terminal['selected_step'] != 369:
            raise AssertionError('Explicit terminal checkpoint was not preserved')
        return dict(status='PASS', restored_head_used=True, ID_order_preserved=True,
                    GT_free=True, fixed_step_checked=True, real_scoring_performed=False,
                    explicit_step369_supported=True,
                    synthetic_N=result['N'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, nargs='+')
    parser.add_argument('--ids', type=Path, default=PRIVATE / 'data_selection.json')
    parser.add_argument('--head-npz', type=Path, default=PRIVATE / 'lpft_full32_bundle/data/lpft_full32/head.npz')
    parser.add_argument('--head-state', type=Path, default=ROOT / '.local_models/119_warm_head_ft/checkpoints/selected_step128/aux_head.pt')
    parser.add_argument('--checkpoint-meta', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--expected-step', type=int, default=SELECTED_STEP,
                        help='Fixed checkpoint step to verify; no checkpoint search')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test())); return
    if not args.features or not args.output or args.threads < 1 or args.expected_step < 0:
        parser.error('Require --features, --output, positive --threads and nonnegative --expected-step')
    metadata = args.checkpoint_meta or args.head_state.with_name('checkpoint_complete.json')
    print(json.dumps(score(args.features, args.ids, args.head_npz, args.head_state,
                           metadata, args.output, args.threads, args.expected_step), ensure_ascii=False))


if __name__ == '__main__':
    main()
