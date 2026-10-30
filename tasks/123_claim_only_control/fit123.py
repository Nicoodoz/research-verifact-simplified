"""Fixed118 head recipe on new claim-only107 features, after extraction."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import random
import sys
import tempfile
import time

import numpy as np
import torch
from torch.nn import functional as F
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/123_claim_only_control'
sys.path.insert(0, str(ROOT / 'tasks/117_verdict_probe'))
from refit_full117 import read_metadata, load_features
from fit_probe117 import LABELS, metrics, write_json
from fit_mlp117 import CONFIG, MLPHead, predict, load_head
from fit_sqrt_mlp117 import weighted_class_values
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT / 'tasks/116_research_cycle'))
from analyze_scores116 import section
sys.path.insert(0, str(ROOT / 'tasks/110_update_interpolation'))
from analyze110 import changes


def fixed_fit(values, labels, config, epochs, out):
    """The118 loop: FP32 scaler/head, sample-mean weighted CE, fixed seed/order."""
    random.seed(config['seed']); np.random.seed(config['seed']); torch.manual_seed(config['seed'])
    order = torch.Generator(device='cpu').manual_seed(config['seed'])
    scaler = StandardScaler().fit(values)
    model = MLPHead(scaler.mean_, scaler.scale_)
    _, weights = weighted_class_values(labels)
    weight = torch.from_numpy(weights)
    x = torch.from_numpy(np.ascontiguousarray(values)).float()
    y = torch.tensor([LABELS.index(g) for g in labels], dtype=torch.long)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config['learning_rate'], weight_decay=config['weight_decay'])
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    for epoch in range(1, epochs+1):
        if time.perf_counter()-started > 300:
            raise TimeoutError('Preserve partial fixed CPU fit after five minutes')
        model.train(); total = 0.
        for batch in torch.randperm(len(y), generator=order).split(config['batch_size']):
            optimizer.zero_grad(set_to_none=True)
            loss = F.cross_entropy(model(x[batch]), y[batch], weight=weight, reduction='none').mean()
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError('Nonfinite fixed head loss')
            loss.backward(); optimizer.step()
            total += float(loss.detach()) * len(batch)
        with (out / 'curve.jsonl').open('ab') as stream:
            stream.write((common.canonical(dict(epoch=epoch, training_loss=total/len(y)))+'\n').encode('utf-8'))
    torch.save(dict(config=config, labels=list(LABELS), state_dict=copy.deepcopy(model.state_dict()),
                    selected_epoch=epochs, fixed_refit=True), out / 'model.pt')
    return model, dict(zip(LABELS, weights.tolist()))


def checked_features(features, rows, private):
    protocol = common.read(private / 'protocol.json')
    lengths = {r['id']: r['input_tokens'] for r in common.rows(private / 'lengths.jsonl')}
    complete = common.read(features / 'complete.json')
    if (complete['N'] != len(rows) or complete['adapter_sha256'] != protocol['adapter_sha256'] or
            complete['prefix_token_ids'] != protocol['prefix_ids']):
        raise ValueError('Incomplete extraction or wrong frozen backbone/prefix')
    seen = set()
    for path in sorted((features / 'batches').glob('*.npz')):
        receipt = common.read(path.with_suffix('.json'))
        if (receipt['adapter_sha256'] != protocol['adapter_sha256'] or
                receipt['prefix_token_ids'] != protocol['prefix_ids']):
            raise ValueError('Feature source mismatch')
        with np.load(path, allow_pickle=False) as shard:
            ids = shard['ids'].astype(str).tolist()
        if receipt['ids'] != ids or seen & set(ids) or receipt['input_tokens'] != [lengths[i] for i in ids]:
            raise ValueError('Feature IDs or empty-reference input lengths differ')
        seen.update(ids)
    if seen != set(lengths):
        raise ValueError('Expected every claim-only feature once')
    return load_features([features], rows)


def fit(features, private, out):
    if out.exists() and any(out.iterdir()):
        raise FileExistsError('Preserve previous attempted123 results')
    protocol = common.read(private / 'protocol.json')
    rows, parts = read_metadata(private / 'metadata.jsonl')
    full = {r['id']: r for r in common.rows(ROOT / '.local_models/118_full_data_heads/reconsidered_refit/sqrt_weight_full/predictions.jsonl')}
    keys = {r['id']: r for r in common.rows(ROOT / '.local_models/116_research_cycle/keys_selection1817.jsonl')}
    baseline = {r['id']: r for r in common.rows(ROOT / '.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    if set(full) != set(keys) or set(keys) != {r['id'] for r in parts['screen']} or set(baseline) != set(keys):
        raise ValueError('Matched1817 predictions are missing')
    if any(full[i]['GT'] != keys[i]['GT'] or not full[i]['valid'] for i in keys):
        raise ValueError('Full-reference comparison labels/validity changed')
    selection = common.read(ROOT / '.local_models/118_full_data_heads/reconsidered_refit/sqrt_weight_full/selection.json')
    config = dict(selection['config'])
    if (selection['fixed_epochs'] != 10 or selection['beta'] != .5 or protocol['head']['fixed_epochs'] != 10 or
            any(config[k] != CONFIG[k] for k in ('feature','hidden','activation','dropout','optimizer',
                                                   'learning_rate','weight_decay','batch_size','seed'))):
        raise ValueError('The frozen matched118 recipe differs')
    config.update(epoch_selection='none; fixed10 matched to118', max_epochs=10,
                  early_stopping_patience=None)
    values, info = checked_features(features, rows, private)
    index = {r['id']: i for i, r in enumerate(rows)}
    train_x = np.stack([values[index[r['id']]] for r in parts['train']])
    train_labels = [r['GT'] for r in parts['train']]
    torch.set_num_threads(4)
    started = time.perf_counter()
    with threadpool_limits(limits=4):
        model, weights = fixed_fit(train_x, train_labels, config, 10, out)
        model, saved = load_head(out / 'model.pt')
        if saved['selected_epoch'] != 10:
            raise AssertionError('Only the fixed final10-epoch head is allowed')
        screen_x = torch.from_numpy(np.stack([values[index[r['id']]] for r in parts['screen']])).float()
        labels, probability = predict(model, screen_x)
    predictions = {r['id']: dict(id=r['id'], verdict=str(label), valid=True,
        probabilities=dict(zip(LABELS, probs.tolist())), probabilities_calibrated=False)
        for r, label, probs in zip(parts['screen'], labels, probability)}
    records = [dict(predictions[i], sid=str(keys[i]['sid']), GT=keys[i]['GT'], author=keys[i]['author'],
        old_panel=keys[i].get('old_panel'), subset=keys[i].get('subset'),
        full_reference=full[i]['verdict'], baseline107=baseline[i]['verdict']) for i in sorted(keys)]
    common.putl(out / 'predictions_sanitized.jsonl', records)
    groups = dict(selection1817=list(keys.values()),
        new1317=[r for r in keys.values() if r.get('subset') == 'new'],
        natural400=[r for r in keys.values() if r.get('old_panel') == 'natural'],
        pressure100=[r for r in keys.values() if r.get('old_panel') == 'pressure'])
    panels = {}
    for name, group in groups.items():
        side = section(group, baseline, predictions)
        full_scores = metrics(group, [full[r['id']]['verdict'] for r in group])
        scores = side['scores']['candidate']
        paired_rows = [dict(r, pred={'full_reference':full[r['id']]['verdict'],
                        'claim_only':predictions[r['id']]['verdict']}) for r in group]
        panels[name] = dict(N=len(group), scores=dict(claim_only=scores, full_reference=full_scores,
            label_only107=side['scores']['label_only107'], paper_r1=side['scores']['paper_r1']),
            claim_only_minus_full_reference=dict(MCC=scores['mcc']-full_scores['mcc'],
                PA=scores['percent_agreement']-full_scores['percent_agreement'],
                correct=scores['correct']-full_scores['correct'], false_S=scores['false_S']-full_scores['false_S']),
            full_reference_to_claim_only=changes(paired_rows, 'full_reference', 'claim_only'),
            claim_only_vs107=side)
    result = dict(task=123, diagnostic_only=True, train_N=3675, train_patients=40,
        screen_N=1817, screen_patients=20, feature_info=info, fixed_epochs=10, beta=.5,
        config=config, weights=weights, new_epoch_selection=False, no_backbone_training=True,
        reference_empty=True, original_GT_unchanged=True, confirmation40_used=False,
        full_reference_predictions_reused=True, CPU_seconds=time.perf_counter()-started,
        panels=panels, interpretation=protocol['interpretation'])
    write_json(out / 'result.json', result)
    print(common.canonical(dict(task=123, N=1817, CPU_seconds=result['CPU_seconds'],
                                paired=panels['selection1817']['claim_only_minus_full_reference'])))


def self_test():
    """Synthetic CPU math/save test only; never touch actual model features."""
    torch.set_num_threads(1)
    rng = np.random.default_rng(123)
    x = rng.normal(size=(12, 8)).astype(np.float32)
    labels = list(LABELS) * 4
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        model, weights = fixed_fit(x, labels, dict(CONFIG, class_weight='inverse_sqrt_training_frequency', beta=.5), 2, folder)
        a, p = predict(model, torch.from_numpy(x))
        restored, saved = load_head(folder / 'model.pt')
        b, q = predict(restored, torch.from_numpy(x))
        np.testing.assert_array_equal(a, b)
        np.testing.assert_allclose(p, q, atol=0, rtol=0)
        np.testing.assert_allclose(restored.mean.numpy(), x.mean(axis=0), atol=1e-7)
        if saved['selected_epoch'] != 2 or not np.isclose(sum(weights.values())/3, 1):
            raise AssertionError('Synthetic fixed head state differs')
    print('PASS: synthetic CPU fit/save/probability recovery; no real features fitted')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--features', type=Path)
    parser.add_argument('--private', type=Path, default=PRIVATE)
    parser.add_argument('--out', type=Path, default=PRIVATE / 'fit')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        if args.features is None:
            parser.error('--features is required after real extraction is complete')
        fit(args.features, args.private, args.out)
