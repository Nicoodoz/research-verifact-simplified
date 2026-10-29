"""Fit small three-class probes; validation alone chooses hyperparameters.

Features come from a frozen backbone and contain no answer tokens.  This module
does not load an LLM, connect to a server, call an API, or alter source labels.
The saved NPZ is a self-contained scaler and linear softmax head.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import matthews_corrcoef
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from verifact_research.evaluation import LABELS, evaluate

REPRESENTATIONS = ('verdict_prefix', 'prompt_end')
PRIMARY = 'verdict_prefix'
CS = (.01, .1, 1.)
CLASS_WEIGHTS = (None, 'balanced')


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2,
                                 allow_nan=False) + '\n').encode('utf-8'))


def metadata_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines()
            if line.strip()]
    if not rows or len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Metadata requires nonempty, unique sample IDs')
    for row in rows:
        if (not isinstance(row['id'], str) or not row['id'] or
                row['GT'] not in LABELS or not str(row['sid']) or
                row['role'] not in {'train', 'validation', 'screen'}):
            raise ValueError('Invalid ID, patient, original label, or probe role')
    sets = {role: {str(row['sid']) for row in rows if row['role'] == role}
            for role in ('train', 'validation', 'screen')}
    if any(not values for values in sets.values()):
        raise ValueError('Train, validation and screen must all be represented')
    if (sets['train'] & sets['validation'] or sets['train'] & sets['screen'] or
            sets['validation'] & sets['screen']):
        raise ValueError('This probe fit requires disjoint patient roles')
    for role in ('train', 'validation'):
        present = {row['GT'] for row in rows if row['role'] == role}
        if present != set(LABELS):
            raise ValueError(f'All original classes are required in {role}')
    return rows


def feature_matrices(directory: Path, rows: list[dict]) -> tuple[dict, dict]:
    wanted = {row['id'] for row in rows}
    values = {name: {} for name in REPRESENTATIONS}
    files = sorted((directory / 'batches').glob('*.npz'))
    if not files:
        raise ValueError('No features/batches/*.npz files found')
    ignored = set()
    dimensions = {}
    for path in files:
        with np.load(path, allow_pickle=False) as data:
            ids = np.asarray(data['ids']).astype(str)
            if ids.ndim != 1 or len(ids) != len(set(ids.tolist())):
                raise ValueError(f'Nonunique or nonvector IDs in {path.name}')
            matrices = {}
            for name in REPRESENTATIONS:
                matrix = np.asarray(data[name], dtype=np.float32)
                if (matrix.ndim != 2 or matrix.shape[0] != len(ids) or
                        not matrix.shape[1] or not np.isfinite(matrix).all()):
                    raise ValueError(f'Invalid {name} feature shape or values')
                if dimensions.setdefault(name, matrix.shape[1]) != matrix.shape[1]:
                    raise ValueError(f'Changing feature width for {name}')
                matrices[name] = matrix
            for index, identifier in enumerate(ids.tolist()):
                if identifier not in wanted:
                    ignored.add(identifier)
                    continue
                if identifier in values[PRIMARY]:
                    raise ValueError(f'Duplicate feature ID: {identifier}')
                for name in REPRESENTATIONS:
                    values[name][identifier] = matrices[name][index].copy()
    absent = wanted - set(values[PRIMARY])
    if absent:
        raise ValueError(f'Missing {len(absent)} requested feature IDs')
    matrices = {name: np.stack([values[name][row['id']] for row in rows])
                for name in REPRESENTATIONS}
    return matrices, dict(batch_files=len(files), requested_N=len(rows),
                          unused_feature_IDs=len(ignored), dimensions=dimensions)


def metrics(rows: list[dict], labels) -> dict:
    labels = [str(label) for label in labels]
    if len(rows) != len(labels):
        raise ValueError('Prediction count does not match the explicit cohort')
    cohort = [dict(proposition_id=row['id'], subject_id=str(row['sid']),
                   human_gt=row['GT']) for row in rows]
    predictions = [dict(proposition_id=row['id'], verdict=label)
                   for row, label in zip(rows, labels)]
    result = evaluate(cohort, predictions, profile='none')
    correct = sum(row['GT'] == label for row, label in zip(rows, labels))
    false_s = sum(row['GT'] != 'Supported' and label == 'Supported'
                  for row, label in zip(rows, labels))
    non_s = sum(row['GT'] != 'Supported' for row in rows)
    predicted_s = labels.count('Supported')
    result.update(correct=correct, false_S=false_s, non_S=non_s,
                  false_S_rate=false_s / non_s if non_s else None,
                  predicted_S=predicted_s,
                  predicted_S_FDR=false_s / predicted_s if predicted_s else None,
                  macro_F1=sum(result['per_class'][g]['f1'] or 0 for g in LABELS) / 3)
    independent_mcc = float(matthews_corrcoef([row['GT'] for row in rows], labels))
    if not np.isclose(result['mcc'], independent_mcc, atol=1e-12):
        raise AssertionError('Project and sklearn MCC disagree')
    return result


def fit_model(x, y, c, class_weight) -> tuple[LogisticRegression, dict]:
    """A convergence retry keeps exactly the same statistical configuration."""
    attempts = []
    for max_iter in (1000, 4000):
        model = LogisticRegression(C=c, class_weight=class_weight, solver='lbfgs',
                                   max_iter=max_iter, tol=1e-6, random_state=117)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ConvergenceWarning)
            model.fit(x, y)
        converged = not any(issubclass(w.category, ConvergenceWarning) for w in caught)
        attempts.append(dict(max_iter=max_iter, iterations=model.n_iter_.tolist(),
                             converged=converged))
        if converged:
            break
    return model, dict(attempts=attempts, converged=converged)


def head_arrays(model: LogisticRegression, scaler: StandardScaler, name: str) -> dict:
    if set(model.classes_.tolist()) != set(LABELS) or model.coef_.shape[0] != 3:
        raise ValueError('Expected an ordinary three-class multinomial head')
    order = [model.classes_.tolist().index(label) for label in LABELS]
    return dict(coef=model.coef_[order], intercept=model.intercept_[order],
                mean=scaler.mean_, scale=scaler.scale_,
                classes=np.asarray(LABELS), representation=np.asarray(name))


def predict_head(arrays, features) -> tuple[np.ndarray, np.ndarray]:
    """Deploy a saved scaler/head without sklearn or a vocabulary projection."""
    logits = ((np.asarray(features, dtype=np.float64) - arrays['mean']) /
              arrays['scale']) @ arrays['coef'].T + arrays['intercept']
    logits -= logits.max(axis=1, keepdims=True)
    probabilities = np.exp(logits)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    classes = np.asarray(arrays['classes']).astype(str)
    return classes[probabilities.argmax(axis=1)], probabilities


def selection_key(config: dict) -> tuple:
    value = config['validation_metrics']
    return value['mcc'], value['percent_agreement'], -value['false_S'], -config['index']


def fit_probes(features_dir: Path, metadata: Path, out: Path, threads: int = 4) -> dict:
    rows = metadata_rows(metadata)
    matrices, feature_info = feature_matrices(features_dir, rows)
    index = {role: np.asarray([i for i, row in enumerate(rows) if row['role'] == role])
             for role in ('train', 'validation', 'screen')}
    split_rows = {role: [rows[i] for i in idx] for role, idx in index.items()}
    y_train = np.asarray([row['GT'] for row in split_rows['train']])
    out.mkdir(parents=True, exist_ok=True)
    selected = {}
    # Neither metadata screen labels nor screen features enter scaler/model fit
    # or validation ranking.  The screen is evaluated only after both are frozen.
    with threadpool_limits(limits=threads):
        for name in REPRESENTATIONS:
            x = matrices[name]
            scaler = StandardScaler().fit(x[index['train']])
            train_x = scaler.transform(x[index['train']])
            val_x = scaler.transform(x[index['validation']])
            configs = []
            models = []
            for c in CS:
                for weight in CLASS_WEIGHTS:
                    model, convergence = fit_model(train_x, y_train, c, weight)
                    value = dict(index=len(configs), C=c, class_weight=weight,
                                 convergence=convergence,
                                 validation_metrics=metrics(split_rows['validation'],
                                                            model.predict(val_x)))
                    configs.append(value)
                    models.append(model)
            best = max(configs, key=selection_key)
            model = models[best['index']]
            arrays = head_arrays(model, scaler, name)
            saved = out / f'{name}_head.npz'
            np.savez_compressed(saved, **arrays)
            with np.load(saved, allow_pickle=False) as restored:
                restored_labels, restored_p = predict_head(restored, x[index['validation']])
                expected_p = model.predict_proba(val_x)
                order = [model.classes_.tolist().index(label) for label in LABELS]
                if not np.array_equal(restored_labels, model.predict(val_x)):
                    raise AssertionError('Saved head changes validation labels')
                if not np.allclose(restored_p, expected_p[:, order], atol=1e-10):
                    raise AssertionError('Saved head changes validation probabilities')
            selected[name] = dict(selected_config_index=best['index'], C=best['C'],
                                  class_weight=best['class_weight'],
                                  validation_metrics=best['validation_metrics'],
                                  configurations=configs, head_file=saved.name)
        selection = dict(task=117, primary=PRIMARY, selection_uses_screen=False,
                         selection_rule='validation MCC, then PA, then fewer false-S; fixed-order tie',
                         representations=selected, feature_info=feature_info,
                         split={role: dict(N=len(part),
                                           patients=len({str(r['sid']) for r in part}),
                                           GT=dict(Counter(r['GT'] for r in part)))
                                for role, part in split_rows.items()})
        write_json(out / 'selection.json', selection)
        # No screen statistic is calculated above this point.
        screen_rows = split_rows['screen']
        for name in REPRESENTATIONS:
            with np.load(out / f'{name}_head.npz', allow_pickle=False) as arrays:
                labels, probabilities = predict_head(arrays, matrices[name][index['screen']])
            predictions = []
            for row, label, probability in zip(screen_rows, labels, probabilities):
                result = {key: row[key] for key in ('id', 'sid', 'GT', 'author', 'role')
                          if key in row}
                result.update(verdict=str(label), valid=True,
                              probabilities=dict(zip(LABELS, probability.tolist())),
                              probabilities_calibrated=False,
                              probability_scope='learned three-class linear head')
                for key in ('panel', 'old_panel', 'subset'):
                    if key in row:
                        result[key] = row[key]
                predictions.append(result)
            path = out / f'{name}_screen_predictions.jsonl'
            path.write_bytes(('\n'.join(json.dumps(row, ensure_ascii=False, allow_nan=False)
                                        for row in predictions) + '\n').encode('utf-8'))
            sections = {'all': metrics(screen_rows, labels)}
            for panel in ('natural', 'pressure'):
                keep = [i for i, row in enumerate(screen_rows)
                        if (row.get('panel') or row.get('old_panel')) == panel]
                if keep:
                    sections[panel] = metrics([screen_rows[i] for i in keep], labels[keep])
            write_json(out / f'{name}_screen_metrics.json', sections)
            selected[name]['screen_metrics'] = sections
    summary = dict(selection, representations=selected,
                   result_boundary='Frozen-backbone learned probes, not a claim of clinical efficacy')
    write_json(out / 'fit_summary.json', summary)
    return summary


def self_test() -> dict:
    """Geometry, save/restore, label alignment and screen-label isolation only."""
    rng = np.random.default_rng(117)
    with tempfile.TemporaryDirectory(prefix='probe117_') as temporary:
        root = Path(temporary)
        (root / 'features/batches').mkdir(parents=True)
        rows = []
        features = []
        for role in ('train', 'validation', 'screen'):
            for class_index, label in enumerate(LABELS):
                for j in range(12):
                    identifier = f'{role}-{class_index}-{j}'
                    rows.append(dict(id=identifier, sid=f'{role}-{j % 3}',
                                     GT=label, author='synthetic', role=role,
                                     panel='natural' if j % 2 else 'pressure'))
                    center = np.zeros(5)
                    center[class_index] = 5
                    features.append(center + rng.normal(0, .15, 5))
        features = np.asarray(features, dtype=np.float32)
        np.savez_compressed(root / 'features/batches/0000.npz',
                            ids=np.asarray([row['id'] for row in rows]),
                            prompt_end=features, verdict_prefix=features * 1.3 + .5)
        metadata = root / 'metadata.jsonl'
        metadata.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        one = fit_probes(root / 'features', metadata, root / 'first', threads=1)
        for row in rows:
            if row['role'] == 'screen':
                row['GT'] = LABELS[(LABELS.index(row['GT']) + 1) % len(LABELS)]
        metadata.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        two = fit_probes(root / 'features', metadata, root / 'second', threads=1)
        for name in REPRESENTATIONS:
            a, b = one['representations'][name], two['representations'][name]
            if a['selected_config_index'] != b['selected_config_index']:
                raise AssertionError('Screen label changes model selection')
            with np.load(root / 'first' / f'{name}_head.npz') as before, \
                    np.load(root / 'second' / f'{name}_head.npz') as after:
                for key in ('mean', 'scale', 'coef', 'intercept'):
                    if not np.array_equal(before[key], after[key]):
                        raise AssertionError('Screen label changes fitted head')
            if a['screen_metrics']['all']['correct'] != len([r for r in rows if r['role'] == 'screen']):
                raise AssertionError('Synthetic separated geometry should be classified exactly')
        return dict(status='PASS', geometry=True, scaler_and_head_roundtrip=True,
                    canonical_label_order=True, screen_labels_do_not_select=True,
                    only_implementation_checked=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False))
        return
    if not all((args.features, args.metadata, args.out)) or args.threads < 1:
        parser.error('--features, --metadata, --out and positive --threads are required')
    result = fit_probes(args.features, args.metadata, args.out, args.threads)
    print(json.dumps(dict(primary=PRIMARY, split=result['split'],
                          selected={name: {key: value[key] for key in
                                           ('C', 'class_weight', 'screen_metrics')}
                                    for name, value in result['representations'].items()}),
                     ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
