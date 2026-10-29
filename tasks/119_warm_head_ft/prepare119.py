"""Prepare full32 LPFT only when explicitly run; never launch GPU or reset time.

The warm head is newly fit on the original32 training patients, not copied
from a full40 refit.  This script requires complete already-extracted features
before fitting anything.  Importing it has no side effects.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import math
import shutil
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/117_verdict_probe'
DEFAULT_FEATURES = [PRIVATE / 'evidence' / name for name in
                    ('features_initial', 'features500_missing',
                     'features1817_missing', 'features_pool_missing')]
sys.path.insert(0, str(ROOT / 'tasks/117_verdict_probe'))


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines()
            if line.strip()]


def put(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes((json.dumps(value, ensure_ascii=False, indent=2,
                                     allow_nan=False) + '\n').encode('utf-8'))


def put_rows(path, values):
    Path(path).write_bytes(('\n'.join(json.dumps(value, ensure_ascii=False, allow_nan=False)
                                    for value in values) + '\n').encode('utf-8'))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def fixed_order(identifier):
    return hashlib.sha256(('117/lpft_full32/train/' + identifier).encode()).hexdigest()


def prepare(feature_dirs, threads=4):
    import numpy as np
    import torch
    from sklearn.preprocessing import StandardScaler
    from threadpoolctl import threadpool_limits
    from fit_probe117 import LABELS, fit_model, head_arrays
    from learned_head117 import LearnedHead
    from refit_full117 import load_features

    source = read(PRIVATE / 'features_initial.json')
    split = read(ROOT / '.local_models/116_research_cycle/data_split.json')
    train_patients = set(map(str, split['gradient_patients']))
    validation_patients = set(map(str, split['internal_validation_patients']))
    if (len(train_patients), len(validation_patients)) != (32, 8) or train_patients & validation_patients:
        raise ValueError('Expected the unchanged116 32/8 patient split')
    original_roles = read(ROOT / 'outputs/103_lora_selection/patient_roles.json')['patients']
    if train_patients | validation_patients != set(map(str, original_roles['train'])):
        raise ValueError('The split differs from the original40 training patients')
    pool = rows(ROOT / '.local_models/106_label_preparation/training_pool.jsonl')
    pool_by_id = {row['id']: row for row in pool}
    if len(pool) != len(pool_by_id) or len(pool) != 3675:
        raise ValueError('Require the complete3675 original training pool')
    if any(row['GT'] not in LABELS or str(row['sid']) not in train_patients | validation_patients
           for row in pool):
        raise ValueError('Training pool label or patient boundary changed')
    train = sorted((row for row in pool if str(row['sid']) in train_patients),
                   key=lambda row: fixed_order(row['id']))
    validation = sorted((row for row in pool if str(row['sid']) in validation_patients),
                        key=lambda row: row['id'])
    if (len(train), len(validation)) != (2945, 730):
        raise ValueError('Expected2945 train and730 validation claims without sample filtering')
    screen_ids = read(PRIVATE / 'data_selection.json')['screen_ids']
    screen_by_id = {row['id']: row for row in rows(PRIVATE / 'lpft_data/screen.jsonl')}
    if len(screen_ids) != len(set(screen_ids)) or len(screen_ids) != 160 or set(screen_ids) != set(screen_by_id):
        raise ValueError('Require the original117 frozen160 GT-free screen inputs')
    forbidden = {'GT', 'human_gt', 'sid', 'panel', 'label', 'verdict', 'answer', 'answer_text'}
    if any(forbidden & set(row) for row in screen_by_id.values()):
        raise ValueError('Screen inputs must remain GT-free')
    if set(screen_ids) & set(pool_by_id):
        raise ValueError('Training-pool and screen IDs overlap')
    # Existing token lengths are reused, not recomputed or used to drop rows.
    index = {row['id']: row for row in rows(ROOT / 'outputs/106_label_preparation/data_pool_index.jsonl')}
    if not set(pool_by_id) <= set(index):
        raise ValueError('Missing original input metadata')
    if any(row['GT'] != index[row['id']]['GT'] or
           str(row['sid']) != str(index[row['id']]['sid']) for row in pool):
        raise ValueError('Original GT or patient association differs between pool and index')
    too_long = [row['id'] for row in pool if index[row['id']]['input_tokens'] + 4 > 16384]
    if too_long:
        raise ValueError('Full inputs exceed the fixed16384 context; do not omit them: ' + str(too_long[:5]))
    wanted = train + validation + [dict(id=i) for i in screen_ids]
    # Missing any requested feature is a hard preparation failure.
    features, feature_info = load_features(feature_dirs, wanted)
    source_sha = source['adapter_sha256']
    provenance_files = 0
    for folder in feature_dirs:
        for path in (folder / 'batches').glob('*.npz'):
            meta = path.with_suffix('.json')
            if not meta.exists() or read(meta).get('adapter_sha256') != source_sha:
                raise ValueError('Feature provenance is not the same source107 adapter: ' + str(path))
            provenance_files += 1
    if not provenance_files:
        raise ValueError('No source feature shards available')
    final_bundle = PRIVATE / 'lpft_full32_bundle'
    archive = PRIVATE / 'lpft_full32_bundle.tar.gz'
    job_path = PRIVATE / 'lpft_full32.json'
    if final_bundle.exists() or archive.exists() or job_path.exists():
        raise FileExistsError('Prepared full32 artifacts already exist; do not refit or overwrite silently')
    session = read(PRIVATE / 'session.json')
    if session['duration_seconds'] != 36000 or session['hourly_CNY'] != 1.58:
        raise ValueError('Expected the existing10-hour night session; do not create another origin')

    with tempfile.TemporaryDirectory(prefix='lpft_full32_', dir=PRIVATE) as temporary:
        bundle = Path(temporary) / 'bundle'
        data = bundle / 'data/lpft_full32'
        data.mkdir(parents=True)
        fit_x = features[:len(train)]
        fit_y = np.asarray([row['GT'] for row in train])
        with threadpool_limits(limits=threads):
            scaler = StandardScaler().fit(fit_x)
            model, convergence = fit_model(scaler.transform(fit_x), fit_y, .0001, 'balanced')
        arrays = head_arrays(model, scaler, 'verdict_prefix')
        np.savez_compressed(data / 'head.npz', **arrays)
        selection = dict(task=117, preparation='lpft_full32', train_N=len(train), train_patients=32,
                         validation_N=len(validation), validation_patients=8,
                         fit_used_validation=False, fit_used_screen=False,
                         representations=dict(verdict_prefix=dict(
                             C=.0001, class_weight='balanced', convergence=convergence)),
                         source_adapter_sha256=source_sha)
        put(data / 'head_selection.json', selection)

        def training_record(row):
            value = {key: row[key] for key in ('id', 'claim', 'reference', 'GT')}
            value['sid'] = str(row['sid'])
            value['expected_prompt_sha256'] = index[row['id']]['input_token_sha256']
            return value

        put_rows(data / 'train.jsonl', [training_record(row) for row in train])
        put_rows(data / 'validation.jsonl', [training_record(row) for row in validation])
        put_rows(data / 'screen.jsonl', [screen_by_id[i] for i in screen_ids])
        torch.set_num_threads(threads)
        head = LearnedHead.from_npz(data / 'head.npz')
        head.eval()
        head_sha = digest(data / 'head.npz')
        ranges = dict(validation=(len(train), len(train) + len(validation)),
                      screen=(len(train) + len(validation), len(wanted)))
        for role, (start, end) in ranges.items():
            chosen = validation if role == 'validation' else [dict(id=i) for i in screen_ids]
            with torch.inference_mode():
                probabilities = head(torch.from_numpy(features[start:end])).softmax(-1).numpy()
            records = []
            for row, probability in zip(chosen, probabilities):
                label_index = int(probability.argmax())
                record = dict(id=row['id'], class_index=label_index, verdict=LABELS[label_index],
                              valid=True, probabilities=dict(zip(LABELS, map(float, probability))))
                if role == 'validation':
                    record['GT'] = row['GT']
                records.append(record)
            put(data / f'initial_{role}_cache.json', dict(
                source_adapter_sha256=source_sha, head_sha256=head_sha,
                feature_source='Existing source107 BF16 prefix states; same four shards',
                head_compute='FP32 CPU; newly fitted on original32 patients only', records=records))
        steps = math.ceil(len(train) / 8)
        if steps != 369:
            raise AssertionError('Expected369 optimizer updates with the final1-example tail')
        job = dict(
            name='lpft_full32', worker='train_lpft117.py', model_dir=source['model_dir'],
            source107_adapter=source['adapter_path'], source_adapter_sha256=source_sha,
            selected_head_npz='data/lpft_full32/head.npz',
            selected_head_selection_json='data/lpft_full32/head_selection.json',
            train_path='data/lpft_full32/train.jsonl', validation_path='data/lpft_full32/validation.jsonl',
            screen_inputs_path='data/lpft_full32/screen.jsonl', screen_ids=screen_ids,
            session_path='session.json', max_seq_length=16384, phase_limit_seconds=21600,
            validation_steps=[0, 128, 256, 369], validation_batch_size=4, screen_batch_size=4,
            backup_best=True, retain_probe_l2=True, fresh_optimizer=True,
            initial_validation_cache='data/lpft_full32/initial_validation_cache.json',
            initial_screen_cache='data/lpft_full32/initial_screen_cache.json',
            training=dict(epochs=1, total_steps=369, learning_rate=1e-5,
                          head_learning_rate=1e-4, gradient_accumulation=8, microbatch=1,
                          betas=[.9, .999], eps=1e-8, weight_decay=0., gradient_clip=1.))
        put(bundle / 'data/lpft_full32.json', job)
        files = ['tasks/117_verdict_probe/train_lpft117.py',
                 'tasks/117_verdict_probe/learned_head117.py',
                 'tasks/107_support_aux/checkpoint107.py',
                 'tasks/104_supervision_evidence/training104.py',
                 'tasks/105_brief_supervision/common105.py']
        for name in files:
            target = bundle / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        summary = dict(
            train_N=len(train), validation_N=len(validation), screen_N=len(screen_ids),
            train_patients=32, validation_patients=8, training_GT=dict(Counter(fit_y.tolist())),
            full_original40_pool_retained=True, long_samples_dropped=0,
            max_original_prompt_tokens=max(index[row['id']]['input_tokens'] for row in pool),
            feature_info=feature_info, source_adapter_sha256=source_sha, head_sha256=head_sha,
            training_order='SHA256 of117/lpft_full32/train/ID, no prediction or label ranking',
            fresh_Adam=True, steps=369, final_accumulation_divisor=1,
            unchanged_night_start_epoch=session['start_epoch'], session_not_bundled=True,
            preparation_only=True, GPU_launched=False)
        put(data / 'preparation.json', summary)
        temporary_archive = Path(temporary) / 'bundle.tar.gz'
        with tarfile.open(temporary_archive, 'w:gz', compresslevel=1) as tar:
            for path in bundle.rglob('*'):
                if path.is_file():
                    tar.add(path, arcname=path.relative_to(bundle), recursive=False)
        shutil.copytree(bundle, final_bundle)
        shutil.copy2(temporary_archive, archive)
        put(job_path, job)
        put(PRIVATE / 'lpft_full32_preparation.json', summary)
    print(json.dumps(dict(prepared_job=str(job_path), bundle=str(archive),
                          train_N=2945, validation_N=730, steps=369, GPU_launched=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, nargs='+', default=DEFAULT_FEATURES)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('threads must be positive')
    prepare(args.features, args.threads)
