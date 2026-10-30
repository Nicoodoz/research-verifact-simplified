"""Fixed two-seed probability means on the original160 IDs only.

No model, GPU, training, weight tuning, cross-family fusion, or extension.
The averaging function takes probability vectors only and cannot access GT.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT/'outputs/124_seed_mean_readout/pilot160.json'
LABELS = ('Supported', 'Not Supported', 'Not Addressed')
SOURCES = {
    'unweighted_workflow': {
        'seed117': 'outputs/117_verdict_probe/reconsidered_extension_verdict_mlp_predictions.jsonl',
        'seed118': 'outputs/118_full_data_heads/unweighted_workflow_seed118_predictions.jsonl'},
    'sqrt_weight_full': {
        'seed117': 'outputs/118_full_data_heads/reconsidered_refit_sqrt_weight_full_predictions.jsonl',
        'seed118': 'outputs/118_full_data_heads/seed_stability_full3675_sqrt_seed118_predictions.jsonl'}}
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/109_boundary_replay'))
from analyze109 import metrics
sys.path.insert(0, str(ROOT/'tasks/110_update_interpolation'))
from analyze110 import changes


def selected_rows(path, wanted):
    """Skip off-pilot lines using only their ID; deserialize wanted records only."""
    found = {}
    with Path(path).open(encoding='utf-8-sig') as stream:
        for line in stream:
            match = re.search(r'"id"\s*:\s*"([^"]+)"', line)
            if not match or match[1] not in wanted:
                continue
            record = json.loads(line)
            if record['id'] in found:
                raise ValueError('Duplicate pilot ID: '+record['id'])
            found[record['id']] = record
    if set(found) != wanted:
        raise ValueError('Missing pilot IDs from '+str(path))
    return found


def vector(record):
    p = record.get('probabilities')
    if (record.get('valid') is not True or not isinstance(p, dict) or tuple(p) != LABELS
            or any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in p.values())
            or abs(sum(p.values())-1.) > 1e-5):
        raise ValueError('Missing/invalid actual probability or different label order')
    result = [p[label] for label in LABELS]
    if record.get('verdict') != LABELS[max(range(3), key=lambda i: result[i])]:
        raise ValueError('Saved single-seed label does not match its probability argmax')
    return result


def mean_decision(first, second):
    mean = [(x+y)/2 for x, y in zip(first, second)]
    index = max(range(3), key=lambda i: mean[i])  # First fixed label wins an exact tie.
    return LABELS[index], dict(zip(LABELS, mean))


def compare(keys, source, target):
    rows = [dict(r, pred={'source': source[r['id']]['verdict'], 'target': target[r['id']]['verdict']}) for r in keys]
    old = metrics(keys, {r['id']: source[r['id']]['verdict'] for r in keys})
    new = metrics(keys, {r['id']: target[r['id']]['verdict'] for r in keys})
    return dict(delta_MCC=new['mcc']-old['mcc'], delta_PA=new['percent_agreement']-old['percent_agreement'],
                delta_correct=new['correct']-old['correct'], delta_false_S=new['false_S']-old['false_S'],
                class_and_false_S_changes=changes(rows, 'source', 'target'))


def self_test():
    assert mean_decision([.5, .5, 0], [.5, .5, 0])[0] == 'Supported'
    assert mean_decision([0, .5, .5], [0, .5, .5])[0] == 'Not Supported'
    assert vector(dict(valid=True, verdict='Not Addressed', probabilities=dict(zip(LABELS, [0, 0, 1])))) == [0, 0, 1]
    try:
        vector(dict(valid=True, verdict='Supported', probabilities={'Supported': 1}))
    except ValueError:
        pass
    else:
        raise AssertionError('Incomplete probabilities must fail')


def run():
    self_test()
    if OUTPUT.exists():
        raise FileExistsError('Keep the first fixed160 attempt; do not overwrite or extend it')
    ids = common.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids']
    wanted = set(ids)
    if len(ids) != len(wanted) or len(ids) != 160:
        raise ValueError('Expected the pre-existing fixed160 pilot')
    families = {}
    for family, paths in SOURCES.items():
        seeds = {name: selected_rows(ROOT/path, wanted) for name, path in paths.items()}
        means = {}
        for i in ids:
            label, probability = mean_decision(vector(seeds['seed117'][i]), vector(seeds['seed118'][i]))
            means[i] = dict(id=i, verdict=label, probabilities=probability, valid=True,
                            probabilities_calibrated=False)
        families[family] = dict(seeds=seeds, mean=means)
    # GT enters only after all two-family mean predictions are frozen.
    keys = selected_rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl', wanted)
    base = selected_rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl', wanted)
    if tuple(sum(keys[i].get('old_panel') == p for i in ids) for p in ('natural', 'pressure')) != (128, 32):
        raise ValueError('The original128/32 pilot panel membership changed')
    result = dict(task=124, name='seed_mean_readout', N=160,
        families={}, weights=[.5, .5], label_order=list(LABELS), exact_tie='first label in fixed order',
        true_head_probabilities=True, calibrated_probabilities=False, sources=SOURCES,
        no_cross_family_fusion=True, GT_used_in_rule=False,
        evaluated_other1657=False, no_auto_expansion=True, new_GPU_CNY=0, new_API_CNY=0,
        deployment='Each family: one shared frozen107 full input prefill, then two CPU heads and their mean; not two9B passes')
    for family, data in families.items():
        components = dict(label_only107=base, **data['seeds'], seed_mean=data['mean'])
        for seed in ('seed117', 'seed118'):
            if any(data['seeds'][seed][i]['GT'] != keys[i]['GT'] for i in ids):
                raise ValueError('Single-seed GT/ID association differs')
        panels = {}
        for panel in ('natural', 'pressure'):
            rows = [keys[i] for i in ids if keys[i]['old_panel'] == panel]
            panels[panel] = dict(N=len(rows), scores={name: metrics(rows, {r['id']: records[r['id']]['verdict'] for r in rows})
                for name, records in components.items()}, mean_vs={name: compare(rows, records, data['mean'])
                for name, records in components.items() if name != 'seed_mean'})
        result['families'][family] = dict(panels=panels,
            predictions_GT_free=[data['mean'][i] for i in ids],
            probability_checks=dict(complete_N=160, label_order_identical=True, sums_within_1e_5=True))
    common.put(OUTPUT, result)
    print(common.canonical({family: {panel: dict(
        mean={k: value['scores']['seed_mean'][k] for k in ('mcc', 'percent_agreement', 'correct', 'false_S', 'non_S')},
        versus={name: {k: pair[k] for k in ('delta_MCC', 'delta_correct', 'delta_false_S')}
                for name, pair in value['mean_vs'].items()}) for panel, value in f['panels'].items()}
        for family, f in result['families'].items()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    self_test() if args.self_test else run()
