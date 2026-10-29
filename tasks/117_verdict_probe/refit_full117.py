"""Refit117's two frozen head recipes on all40 training patients, CPU only.

There is no validation split, epoch selection or hyperparameter search here.
The previously selected16-epoch balanced MLP is the primary candidate.  The
previously selected balanced linear head is a fixed reference.  Screen labels
are used only after the two models are fitted and saved.
An optional fixed ID list restricts evaluation; the remaining development
examples are not passed through either prediction head.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import random
import tempfile
import time

import numpy as np
import torch
from torch.nn import functional as F
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from fit_probe117 import (LABELS, ROOT, fit_model, head_arrays, metrics,
                          predict_head, write_json)
from fit_mlp117 import CONFIG, MLPHead, load_head, predict

REFIT_EPOCHS = 16
LINEAR_C = .0001


def read_metadata(path: Path, expected_n=(3675, 1817), expected_patients=(40, 20)):
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines()
            if line.strip()]
    if len(rows) != len({row['id'] for row in rows}):
        raise ValueError('Refit metadata contains duplicate IDs')
    for row in rows:
        if (row['role'] not in {'train', 'screen'} or row['GT'] not in LABELS or
                not isinstance(row['id'], str) or not row['id'] or not str(row['sid'])):
            raise ValueError('Only valid original-label train/screen metadata is permitted')
    parts = {role: [row for row in rows if row['role'] == role]
             for role in ('train', 'screen')}
    patients = {role: {str(row['sid']) for row in part} for role, part in parts.items()}
    if patients['train'] & patients['screen']:
        raise ValueError('Training and development patients must be disjoint')
    if tuple(len(parts[role]) for role in ('train', 'screen')) != tuple(expected_n):
        raise ValueError('Full3675 training and1817 development features are required')
    if tuple(len(patients[role]) for role in ('train', 'screen')) != tuple(expected_patients):
        raise ValueError('Expected original40 training and20 development patients')
    if tuple(expected_n) == (3675, 1817) and tuple(expected_patients) == (40, 20):
        roles = json.loads((ROOT / 'outputs/103_lora_selection/patient_roles.json').read_text())['patients']
        if (patients['train'] != set(map(str, roles['train'])) or
                patients['screen'] != set(map(str, roles['selection']))):
            raise ValueError('Refit patient roles differ from the original40/20 boundary')
    if {row['GT'] for row in parts['train']} != set(LABELS):
        raise ValueError('All three original classes are required in full training data')
    return rows, parts


def load_features(directories: list[Path], rows: list[dict]):
    """Combine existing extraction shards; keep their exact stored FP32 states."""
    wanted = {row['id'] for row in rows}
    found = {}
    width = None
    files = 0
    unused = set()
    seen_paths = set()
    for directory in directories:
        for path in sorted((directory / 'batches').glob('*.npz')):
            resolved = path.resolve()
            if resolved in seen_paths:
                raise ValueError('The same extraction file was supplied twice')
            seen_paths.add(resolved)
            files += 1
            with np.load(path, allow_pickle=False) as source:
                ids = np.asarray(source['ids']).astype(str)
                values = np.asarray(source['verdict_prefix'], dtype=np.float32)
                if (ids.ndim != 1 or len(set(ids.tolist())) != len(ids) or
                        values.ndim != 2 or values.shape[0] != len(ids) or
                        not np.isfinite(values).all()):
                    raise ValueError(f'Invalid prefix feature shard: {path.name}')
                if width is None:
                    width = values.shape[1]
                if width != values.shape[1] or not width:
                    raise ValueError('Feature dimensions changed across extraction shards')
                for i, identifier in enumerate(ids.tolist()):
                    if identifier not in wanted:
                        unused.add(identifier)
                        continue
                    if identifier in found:
                        raise ValueError(f'Duplicate feature ID: {identifier}')
                    found[identifier] = values[i].copy()
    missing = wanted - set(found)
    if missing:
        raise ValueError(f'Missing{len(missing)} full-refit features; do not fit partial data')
    return np.stack([found[row['id']] for row in rows]), dict(
        batch_files=files, feature_width=width, N=len(rows), unused_feature_IDs=len(unused))


def frozen_recipes(mlp_source: Path, linear_source: Path, width: int):
    source_model, mlp_saved = load_head(mlp_source)
    mlp_config = dict(mlp_saved['config'])
    if (mlp_saved['selected_epoch'] != REFIT_EPOCHS or
            mlp_config.get('class_weight') != 'balanced' or
            source_model.mean.numel() != width):
        raise ValueError('Expected the frozen balanced MLP selected at epoch16')
    for key in ('feature', 'hidden', 'activation', 'dropout', 'optimizer',
                'learning_rate', 'weight_decay', 'batch_size', 'seed'):
        if mlp_config.get(key) != CONFIG[key]:
            raise ValueError(f'The frozen MLP recipe changed: {key}')
    selection = json.loads((linear_source / 'selection.json').read_text(encoding='utf-8'))
    chosen = selection['representations']['verdict_prefix']
    if chosen['C'] != LINEAR_C or chosen['class_weight'] != 'balanced':
        raise ValueError('Expected the frozen C=.0001 balanced linear head')
    with np.load(linear_source / 'verdict_prefix_head.npz', allow_pickle=False) as head:
        if (tuple(head['classes'].astype(str).tolist()) != tuple(LABELS) or
                str(head['representation'].item()) != 'verdict_prefix' or
                head['coef'].shape != (3, width)):
            raise ValueError('The frozen linear source is incompatible with the full features')
    return dict(mlp=mlp_config, mlp_epochs=REFIT_EPOCHS,
                linear=dict(C=LINEAR_C, class_weight='balanced'),
                source_mlp=str(mlp_source), source_linear=str(linear_source),
                source_weights_used_as_initialization=False)


def selected_screen_rows(source: Path | None, full_rows: list[dict]):
    if source is None:
        return full_rows, dict(name=f'selection{len(full_rows)}', restricted=False,
                               available_N=len(full_rows), scored_N=len(full_rows), unscored_N=0)
    supplied = json.loads(Path(source).read_text(encoding='utf-8-sig'))
    ids = supplied.get('screen_ids') if isinstance(supplied, dict) else supplied
    if (not isinstance(ids, list) or not ids or
            any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids))):
        raise ValueError('--screen-ids must contain a nonempty, unique JSON ID list')
    by_id = {row['id']: row for row in full_rows}
    if not set(ids) <= set(by_id):
        raise ValueError('--screen-ids contains a training or unknown ID')
    rows = [by_id[i] for i in ids]
    return rows, dict(name=f'screen_subset{len(rows)}', restricted=True,
                      available_N=len(full_rows), scored_N=len(rows),
                      unscored_N=len(full_rows) - len(rows), source=str(source))


def save_predictions(directory: Path, rows: list[dict], labels, probability, scope: dict):
    records = []
    for row, label, values in zip(rows, labels, probability):
        item = {key: row[key] for key in ('id', 'sid', 'GT', 'author', 'role',
                                         'panel', 'old_panel', 'subset') if key in row}
        item.update(verdict=str(label), valid=True,
                    probabilities=dict(zip(LABELS, values.tolist())),
                    probabilities_calibrated=False)
        records.append(item)
    (directory / 'screen_predictions.jsonl').write_bytes(
        ('\n'.join(json.dumps(row, ensure_ascii=False, allow_nan=False)
                   for row in records) + '\n').encode())
    sections = {scope['name']: metrics(rows, labels)}
    for section in ('natural', 'pressure', 'new1317'):
        if section == 'new1317':
            keep = [i for i, row in enumerate(rows) if row.get('subset') == 'new']
        else:
            keep = [i for i, row in enumerate(rows)
                    if (row.get('panel') or row.get('old_panel')) == section]
        if keep:
            sections[section] = metrics([rows[i] for i in keep], labels[keep])
    return sections


def refit(features, metadata, mlp_source, linear_source, out, threads=4,
          expected_n=(3675, 1817), expected_patients=(40, 20), screen_ids=None):
    rows, parts = read_metadata(metadata, expected_n, expected_patients)
    scored_rows, screen_scope = selected_screen_rows(screen_ids, parts['screen'])
    values, feature_info = load_features(features, rows)
    recipe = frozen_recipes(mlp_source, linear_source, values.shape[1])
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new output directory; preserve previous refit results')
    out.mkdir(parents=True, exist_ok=True)
    positions = {row['id']: i for i, row in enumerate(rows)}
    index = dict(train=np.asarray([i for i, row in enumerate(rows) if row['role'] == 'train']),
                 screen=np.asarray([positions[row['id']] for row in scored_rows]))
    training = parts['train']
    counts = np.asarray([sum(row['GT'] == label for row in training) for label in LABELS])
    weights = len(training) / (3 * counts)
    summary = dict(task=117, recipe=recipe, feature_info=feature_info,
                   train_N=len(training), train_patients=len({str(r['sid']) for r in training}),
                   train_GT=dict(zip(LABELS, counts.tolist())),
                   class_weights=dict(zip(LABELS, weights.tolist())),
                   validation_used=False, screen_used_for_selection=False,
                   screen_scope=screen_scope,
                   class_weight_mean_over_training=float(np.dot(counts, weights) / counts.sum()))
    write_json(out / 'frozen_refit_recipe.json', summary)
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(threads)
    started = time.perf_counter()
    try:
        with threadpool_limits(limits=threads):
            scaler = StandardScaler().fit(values[index['train']])
            np.savez_compressed(out / 'scaler.npz', mean=scaler.mean_, scale=scaler.scale_,
                                classes=np.asarray(LABELS))
            random.seed(recipe['mlp']['seed'])
            np.random.seed(recipe['mlp']['seed'])
            torch.manual_seed(recipe['mlp']['seed'])
            order_rng = torch.Generator(device='cpu').manual_seed(recipe['mlp']['seed'])
            model = MLPHead(scaler.mean_, scaler.scale_)
            train_x = torch.from_numpy(np.ascontiguousarray(values[index['train']])).float()
            screen_x = torch.from_numpy(np.ascontiguousarray(values[index['screen']])).float()
            y = torch.tensor([LABELS.index(row['GT']) for row in training], dtype=torch.long)
            class_weights = torch.as_tensor(weights, dtype=torch.float32)
            optimizer = torch.optim.AdamW(model.parameters(), lr=recipe['mlp']['learning_rate'],
                                          weight_decay=recipe['mlp']['weight_decay'])
            mlp_out = out / 'balanced_mlp_full'
            linear_out = out / 'balanced_linear_full'
            mlp_out.mkdir(); linear_out.mkdir()
            # Exactly16 epochs, no validation evaluation or early stopping.
            for epoch in range(1, REFIT_EPOCHS + 1):
                model.train()
                total_loss = 0.
                for batch in torch.randperm(len(y), generator=order_rng).split(recipe['mlp']['batch_size']):
                    optimizer.zero_grad(set_to_none=True)
                    per_example = F.cross_entropy(model(train_x[batch]), y[batch], reduction='none')
                    loss = (per_example * class_weights[y[batch]]).mean()
                    if not bool(torch.isfinite(loss)):
                        raise FloatingPointError('Nonfinite full-refit MLP loss')
                    loss.backward(); optimizer.step()
                    total_loss += float(loss.detach()) * len(batch)
                with (mlp_out / 'curve.jsonl').open('ab') as stream:
                    row = dict(epoch=epoch, training_loss=total_loss / len(y),
                               elapsed_seconds=time.perf_counter() - started)
                    stream.write((json.dumps(row) + '\n').encode())
            state = copy.deepcopy(model.state_dict())
            torch.save(dict(config=recipe['mlp'], labels=list(LABELS), state_dict=state,
                            selected_epoch=REFIT_EPOCHS, fixed_refit=True), mlp_out / 'model.pt')
            write_json(mlp_out / 'selection.json', dict(
                candidate='balanced_mlp_full', fixed_epoch=REFIT_EPOCHS,
                epoch_selected_here=False, validation_used=False, screen_used_for_selection=False))
            restored, _ = load_head(mlp_out / 'model.pt')
            # One frozen linear fit, no C or class-weight search.
            linear, convergence = fit_model(scaler.transform(values[index['train']]),
                                             np.asarray([row['GT'] for row in training]),
                                             LINEAR_C, 'balanced')
            arrays = head_arrays(linear, scaler, 'verdict_prefix')
            np.savez_compressed(linear_out / 'verdict_prefix_head.npz', **arrays)
            write_json(linear_out / 'selection.json', dict(
                candidate='balanced_linear_full', C=LINEAR_C, class_weight='balanced',
                convergence=convergence, hyperparameters_selected_here=False,
                validation_used=False, screen_used_for_selection=False))
            # Both frozen fitted states exist before any development scoring.
            mlp_labels, mlp_probability = predict(restored, screen_x)
            linear_labels, linear_probability = predict_head(arrays, values[index['screen']])
            summary['results'] = {
                'balanced_mlp_full': save_predictions(mlp_out, scored_rows, mlp_labels, mlp_probability, screen_scope),
                'balanced_linear_full': save_predictions(linear_out, scored_rows, linear_labels, linear_probability, screen_scope)}
            summary['elapsed_seconds'] = time.perf_counter() - started
            for name, sections in summary['results'].items():
                write_json(out / name / 'fit_summary.json', dict(
                    candidate=name, train_N=len(training), validation_used=False,
                    screen_used_for_selection=False, screen_scope=screen_scope, screen_metrics=sections))
            write_json(out / 'refit_summary.json', summary)
            return summary
    finally:
        torch.set_num_threads(previous_threads)


def self_test():
    """Tiny synthetic isolation/serialization test; no real dataset is fitted."""
    rng = np.random.default_rng(117)
    with tempfile.TemporaryDirectory(prefix='refit117_') as temporary:
        root = Path(temporary)
        mlp_source = root / 'mlp_source'
        linear_source = root / 'linear_source'
        mlp_source.mkdir(); linear_source.mkdir()
        config = dict(CONFIG, class_weight='balanced',
                      loss='class-balanced three-class CE, ordinary sample mean')
        initial = MLPHead(np.zeros(6), np.ones(6))
        torch.save(dict(config=config, labels=list(LABELS), state_dict=initial.state_dict(),
                        selected_epoch=REFIT_EPOCHS), mlp_source / 'model.pt')
        np.savez_compressed(linear_source / 'verdict_prefix_head.npz', coef=np.zeros((3, 6)),
                            intercept=np.zeros(3), mean=np.zeros(6), scale=np.ones(6),
                            classes=np.asarray(LABELS), representation=np.asarray('verdict_prefix'))
        write_json(linear_source / 'selection.json', dict(representations=dict(
            verdict_prefix=dict(C=LINEAR_C, class_weight='balanced'))))
        rows, x = [], []
        for role, count in [('train', 3), ('screen', 2)]:
            for k, label in enumerate(LABELS):
                for j in range(count):
                    rows.append(dict(id=f'{role}-{k}-{j}', sid=f'{role}-{j}',
                                     GT=label, author='synthetic', role=role))
                    point = rng.normal(0, .1, 6); point[k] += 3; x.append(point)
        x = np.asarray(x, dtype=np.float32)
        dirs = [root / 'a', root / 'b']
        for number, indices in enumerate(np.array_split(np.arange(len(rows)), 2)):
            (dirs[number] / 'batches').mkdir(parents=True)
            np.savez_compressed(dirs[number] / 'batches/0000.npz',
                                ids=np.asarray([rows[i]['id'] for i in indices]),
                                verdict_prefix=x[indices])
        metadata = root / 'metadata.jsonl'
        metadata.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        selected_ids = [row['id'] for row in rows if row['role'] == 'screen'][::2][:2]
        screen_file = root / 'screen_ids.json'
        screen_file.write_text(json.dumps(selected_ids), encoding='utf-8')
        first = refit(dirs, metadata, mlp_source / 'model.pt', linear_source, root / 'first',
                      threads=1, expected_n=(9, 6), expected_patients=(3, 2), screen_ids=screen_file)
        for row in rows:
            if row['role'] == 'screen' and row['id'] not in selected_ids:
                row['GT'] = LABELS[(LABELS.index(row['GT']) + 1) % 3]
        metadata.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        screen_file.write_text(json.dumps(dict(screen_ids=selected_ids)), encoding='utf-8')
        refit(dirs, metadata, mlp_source / 'model.pt', linear_source, root / 'second',
              threads=1, expected_n=(9, 6), expected_patients=(3, 2), screen_ids=screen_file)
        a, _ = load_head(root / 'first/balanced_mlp_full/model.pt')
        b, _ = load_head(root / 'second/balanced_mlp_full/model.pt')
        if any(not torch.equal(a.state_dict()[key], b.state_dict()[key]) for key in a.state_dict()):
            raise AssertionError('Screen labels changed the fully refitted MLP')
        for name in ('coef', 'intercept', 'mean', 'scale'):
            with np.load(root / 'first/balanced_linear_full/verdict_prefix_head.npz') as before, \
                    np.load(root / 'second/balanced_linear_full/verdict_prefix_head.npz') as after:
                if not np.array_equal(before[name], after[name]):
                    raise AssertionError('Screen labels changed the fully refitted linear head')
        if first['class_weight_mean_over_training'] != 1.:
            raise AssertionError('Balanced weights must average1 over full training examples')
        for name in ('balanced_mlp_full', 'balanced_linear_full'):
            before = (root / 'first' / name / 'screen_predictions.jsonl').read_bytes()
            after = (root / 'second' / name / 'screen_predictions.jsonl').read_bytes()
            records = [json.loads(line) for line in before.splitlines()]
            if before != after or [row['id'] for row in records] != selected_ids:
                raise AssertionError('Unselected screen labels affected outputs or were scored')
            if set(first['results'][name]) != {'screen_subset2'}:
                raise AssertionError('Partial screening was mislabeled as the complete cohort')
        all_rows, all_scope = selected_screen_rows(None, [row for row in rows if row['role'] == 'screen'])
        if len(all_rows) != 6 or all_scope['restricted']:
            raise AssertionError('Default full-screen compatibility changed')
        return dict(status='PASS', two_feature_directories=True,
                    screen_labels_do_not_change_fits=True, fixed_epoch16=True,
                    fixed_linear_C=LINEAR_C, restricted_predictions_only=True,
                    list_and_dict_screen_ids=True, full_default_preserved=True,
                    real_training_run=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', nargs='+', type=Path)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--mlp-source', type=Path)
    parser.add_argument('--linear-source', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--screen-ids', type=Path,
                        help='Optional frozen JSON ID list or object containing screen_ids; only these IDs are scored')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False)); return
    if not all((args.features, args.metadata, args.mlp_source, args.linear_source, args.out)) or args.threads < 1:
        parser.error('Require features, metadata, frozen model sources, out and positive threads')
    result = refit(args.features, args.metadata, args.mlp_source, args.linear_source, args.out,
                   args.threads, screen_ids=args.screen_ids)
    print(json.dumps(dict(train_N=result['train_N'], elapsed_seconds=result['elapsed_seconds'],
                          results=result['results']), ensure_ascii=False))


if __name__ == '__main__':
    main()
