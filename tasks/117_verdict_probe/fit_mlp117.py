"""One fixed CPU nonlinear probe to test linear-head capacity limitations.

No architecture or learning-rate search.  Only validation selects an epoch.
This does not adapt the language-model backbone or start GPU work.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import random
import tempfile
import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from fit_probe117 import (LABELS, feature_matrices, metadata_rows, metrics,
                          write_json)

CONFIG = dict(feature='verdict_prefix', hidden=128, activation='ReLU',
              dropout=.1, optimizer='AdamW', learning_rate=1e-3,
              weight_decay=1e-2, batch_size=64, max_epochs=40,
              early_stopping_patience=8, seed=117,
              loss='ordinary three-class CE; no class weighting',
              epoch_selection='validation MCC, then PA, then fewer false-S; earliest tie')


class MLPHead(nn.Module):
    def __init__(self, mean, scale):
        super().__init__()
        mean = torch.as_tensor(np.asarray(mean).copy(), dtype=torch.float32)
        scale = torch.as_tensor(np.asarray(scale).copy(), dtype=torch.float32)
        if mean.ndim != 1 or scale.shape != mean.shape or not bool((scale > 0).all()):
            raise ValueError('Invalid training-only scaler')
        self.register_buffer('mean', mean)
        self.register_buffer('scale', scale)
        self.net = nn.Sequential(nn.Linear(len(mean), CONFIG['hidden']), nn.ReLU(),
                                 nn.Dropout(CONFIG['dropout']), nn.Linear(CONFIG['hidden'], 3))

    def forward(self, features):
        if features.device.type != 'cpu':
            raise ValueError('This fixed probe is CPU only')
        return self.net((features.float() - self.mean) / self.scale)


def predict(model: MLPHead, features: torch.Tensor):
    model.eval()
    with torch.inference_mode():
        parts = [model(part).softmax(dim=-1) for part in features.split(512)]
        probability = torch.cat(parts).cpu().numpy()
    if not np.isfinite(probability).all():
        raise FloatingPointError('Nonfinite MLP probabilities')
    return np.asarray(LABELS)[probability.argmax(axis=1)], probability


def validation_key(value):
    return value['mcc'], value['percent_agreement'], -value['false_S']


def load_head(path: str | Path):
    saved = torch.load(path, map_location='cpu', weights_only=True)
    if tuple(saved['labels']) != tuple(LABELS) or saved['config'] != CONFIG:
        raise ValueError('Saved MLP has a different label order or fixed configuration')
    state = saved['state_dict']
    model = MLPHead(state['mean'].numpy(), state['scale'].numpy())
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, saved


def fit_mlp(features_dir: Path, metadata: Path, out: Path, threads: int = 4):
    rows = metadata_rows(metadata)
    matrices, feature_info = feature_matrices(features_dir, rows)
    values = matrices[CONFIG['feature']]
    index = {role: np.asarray([i for i, row in enumerate(rows) if row['role'] == role])
             for role in ('train', 'validation', 'screen')}
    split_rows = {role: [rows[i] for i in ids] for role, ids in index.items()}
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new output directory; preserve previous attempted results')
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / 'config.json', CONFIG)
    random.seed(CONFIG['seed'])
    np.random.seed(CONFIG['seed'])
    torch.manual_seed(CONFIG['seed'])
    order_rng = torch.Generator(device='cpu').manual_seed(CONFIG['seed'])
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(threads)
    started = time.perf_counter()
    try:
        with threadpool_limits(limits=threads):
            scaler = StandardScaler().fit(values[index['train']])
            np.savez_compressed(out / 'scaler.npz', mean=scaler.mean_, scale=scaler.scale_,
                                classes=np.asarray(LABELS))
            model = MLPHead(scaler.mean_, scaler.scale_)
            optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG['learning_rate'],
                                          weight_decay=CONFIG['weight_decay'])
            tensors = {role: torch.from_numpy(np.ascontiguousarray(values[ids])).float()
                       for role, ids in index.items()}
            train_y = torch.tensor([LABELS.index(row['GT']) for row in split_rows['train']],
                                   dtype=torch.long)
            best = None
            best_state = None
            patience = 0
            curves = []
            for epoch in range(1, CONFIG['max_epochs'] + 1):
                model.train()
                total_loss = 0.
                for indices in torch.randperm(len(train_y), generator=order_rng).split(CONFIG['batch_size']):
                    optimizer.zero_grad(set_to_none=True)
                    loss = F.cross_entropy(model(tensors['train'][indices]), train_y[indices])
                    if not bool(torch.isfinite(loss)):
                        raise FloatingPointError('Nonfinite MLP training loss')
                    loss.backward()
                    optimizer.step()
                    total_loss += float(loss.detach()) * len(indices)
                predicted, _ = predict(model, tensors['validation'])
                value = metrics(split_rows['validation'], predicted)
                row = dict(epoch=epoch, training_loss=total_loss / len(train_y),
                           validation_metrics=value, elapsed_seconds=time.perf_counter() - started)
                curves.append(row)
                with (out / 'curve.jsonl').open('ab') as stream:
                    stream.write((json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n').encode())
                if best is None or validation_key(value) > validation_key(best['validation_metrics']):
                    best = row
                    best_state = copy.deepcopy(model.state_dict())
                    patience = 0
                else:
                    patience += 1
                if patience >= CONFIG['early_stopping_patience']:
                    break
            if best is None or best_state is None:
                raise AssertionError('No validation-selected model state')
            model.load_state_dict(best_state, strict=True)
            model.eval()
            selection = dict(task=117, candidate='verdict_mlp', config=CONFIG,
                             feature_info=feature_info, selected_epoch=best['epoch'],
                             completed_epochs=len(curves), validation_metrics=best['validation_metrics'],
                             selection_uses_screen=False,
                             stop_reason='validation_patience' if patience >= 8 else 'fixed_epoch_cap',
                             split={role: dict(N=len(part),
                                               patients=len({str(row['sid']) for row in part}))
                                    for role, part in split_rows.items()})
            # Persist the selected model before any screen statistic is computed.
            write_json(out / 'selection.json', selection)
            torch.save(dict(config=CONFIG, labels=list(LABELS), state_dict=best_state,
                            selected_epoch=best['epoch']), out / 'model.pt')
            restored, _ = load_head(out / 'model.pt')
            _, expected = predict(model, tensors['validation'])
            _, actual = predict(restored, tensors['validation'])
            if not np.array_equal(expected, actual):
                raise AssertionError('Saved MLP changes CPU validation probabilities')
            predicted, probabilities = predict(restored, tensors['screen'])
            screen_rows = split_rows['screen']
            results = []
            for row, label, probability in zip(screen_rows, predicted, probabilities):
                item = {key: row[key] for key in ('id', 'sid', 'GT', 'author', 'role',
                                                  'panel', 'old_panel', 'subset') if key in row}
                item.update(verdict=str(label), valid=True,
                            probabilities=dict(zip(LABELS, probability.tolist())),
                            probabilities_calibrated=False,
                            probability_scope='fixed single-hidden-layer learned probe')
                results.append(item)
            (out / 'screen_predictions.jsonl').write_bytes(
                ('\n'.join(json.dumps(item, ensure_ascii=False, allow_nan=False)
                           for item in results) + '\n').encode())
            sections = {'all': metrics(screen_rows, predicted)}
            for panel in ('natural', 'pressure'):
                keep = [i for i, row in enumerate(screen_rows)
                        if (row.get('panel') or row.get('old_panel')) == panel]
                if keep:
                    sections[panel] = metrics([screen_rows[i] for i in keep], predicted[keep])
            summary = dict(selection, screen_metrics=sections,
                           elapsed_seconds=time.perf_counter() - started,
                           result_boundary='A fixed CPU capacity check; not backbone adaptation')
            write_json(out / 'fit_summary.json', summary)
            return summary
    finally:
        torch.set_num_threads(previous_threads)


def self_test():
    rng = np.random.default_rng(117)
    with tempfile.TemporaryDirectory(prefix='mlp117_') as temporary:
        root = Path(temporary)
        (root / 'features/batches').mkdir(parents=True)
        rows, values = [], []
        for role in ('train', 'validation', 'screen'):
            for label_index, label in enumerate(LABELS):
                for j in range(6):
                    rows.append(dict(id=f'{role}-{label_index}-{j}', sid=f'{role}-{j % 2}',
                                     GT=label, author='synthetic', role=role,
                                     panel='natural' if j % 2 else 'pressure'))
                    point = rng.normal(0, .1, 6)
                    point[label_index] += 3
                    values.append(point)
        values = np.asarray(values, dtype=np.float32)
        np.savez_compressed(root / 'features/batches/0000.npz',
                            ids=np.asarray([row['id'] for row in rows]),
                            prompt_end=values, verdict_prefix=values)
        source = root / 'metadata.jsonl'
        source.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        first = fit_mlp(root / 'features', source, root / 'first', threads=1)
        for row in rows:
            if row['role'] == 'screen':
                row['GT'] = LABELS[(LABELS.index(row['GT']) + 1) % 3]
        source.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        second = fit_mlp(root / 'features', source, root / 'second', threads=1)
        a, _ = load_head(root / 'first/model.pt')
        b, _ = load_head(root / 'second/model.pt')
        if first['selected_epoch'] != second['selected_epoch']:
            raise AssertionError('Screen labels changed epoch selection')
        for key in a.state_dict():
            if not torch.equal(a.state_dict()[key], b.state_dict()[key]):
                raise AssertionError('Screen labels changed the selected MLP')
        expected_mean = values[:18].mean(axis=0)
        if not np.allclose(a.mean.numpy(), expected_mean, atol=1e-6):
            raise AssertionError('Scaler was not fit on training examples alone')
        return dict(status='PASS', fixed_architecture=True, CPU_only=True,
                    validation_only_epoch_selection=True, train_only_scaler=True,
                    saved_probabilities_identical=True, screen_label_isolation=True,
                    max_epochs=CONFIG['max_epochs'], patience=CONFIG['early_stopping_patience'],
                    only_implementation_checked=True)


def main():
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
    summary = fit_mlp(args.features, args.metadata, args.out, args.threads)
    print(json.dumps(dict(selected_epoch=summary['selected_epoch'],
                          completed_epochs=summary['completed_epochs'],
                          screen_metrics=summary['screen_metrics']), ensure_ascii=False,
                     allow_nan=False))


if __name__ == '__main__':
    main()
