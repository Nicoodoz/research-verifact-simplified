"""Compare fixed108 predictions on the original500 IDs; CPU statistics only.

The same prewritten point signal/guards apply to the fixed-feature screen,
GPU-versus-cheap screen, and subsequent fresh same-split GPU-flat contrast.
Neither an old092 OOF arm nor the cheap frozen-feature head is a fair GPU control.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import common108 as c

sys.path.insert(0, str(c.ROOT/'src'))
from verifact_research.evaluation import evaluate

PANELS = {'natural': 400, 'pressure': 100}


def unique_rows(path):
    records = c.rows(path)
    identifiers = [r['id'] for r in records]
    if any(not isinstance(i, str) or not i.strip() for i in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError('Blank or duplicate IDs: ' + Path(path).name)
    return records


def load_predictions(path, expected):
    records = unique_rows(path)
    if {r['id'] for r in records} != set(expected):
        raise ValueError('Prediction IDs must exactly cover the fixed500; no filtering or fallback')
    arms = {r.get('arm') for r in records}
    if len(arms) != 1 or None in arms:
        raise ValueError('One explicit arm required per prediction file')
    result = {}
    for row in records:
        source = expected[row['id']]
        if str(row.get('sid')) != str(source['sid']):
            raise ValueError('Prediction patient differs from fixed metadata')
        if 'GT' in row and row['GT'] != source['GT']:
            raise ValueError('Prediction GT differs from original GT')
        if row.get('panel') is not None and row['panel'] != source['panel']:
            raise ValueError('Prediction panel differs from frozen metadata')
        if row.get('prediction') not in c.LABELS:
            raise ValueError('Missing or invalid prediction; preserve and report it separately')
        p = np.asarray(row.get('probabilities'), dtype=float)
        if p.shape != (3,) or not np.isfinite(p).all() or np.any(p < 0) or np.any(p > 1) or not np.isclose(p.sum(), 1, atol=1e-5, rtol=0):
            raise ValueError('Finite normalized S/NS/NA probabilities required')
        if row['prediction'] != c.LABELS[int(p.argmax())]:
            raise ValueError('Saved prediction differs from joint three-probability argmax')
        result[row['id']] = row['prediction']
    return result, next(iter(arms))


def metric(rows, predictions):
    cohort = [dict(proposition_id=r['id'], subject_id=str(r['sid']), human_gt=r['GT']) for r in rows]
    outputs = [dict(proposition_id=r['id'], verdict=predictions[r['id']]) for r in rows]
    result = evaluate(cohort, outputs, profile='none')
    false = sum(r['GT'] != 'Supported' and predictions[r['id']] == 'Supported' for r in rows)
    non_s = sum(r['GT'] != 'Supported' for r in rows)
    predicted_s = sum(predictions[r['id']] == 'Supported' for r in rows)
    result.update(correct=sum(r['GT'] == predictions[r['id']] for r in rows), false_S=false,
        non_S=non_s, false_S_rate=false/non_s if non_s else None, predicted_S=predicted_s,
        predicted_S_FDR=false/predicted_s if predicted_s else None,
        macro_F1=sum(result['per_class'][g]['f1'] or 0 for g in c.LABELS)/3)
    return result


def transitions(rows, baseline, candidate):
    by_class = {}
    for label in c.LABELS:
        by_class[label] = dict(N=sum(r['GT'] == label for r in rows),
            rescued=sum(r['GT'] == label and baseline[r['id']] != label == candidate[r['id']] for r in rows),
            harmed=sum(r['GT'] == label and baseline[r['id']] == label != candidate[r['id']] for r in rows))
    return dict(by_GT=by_class,
        false_S_new=sum(r['GT'] != 'Supported' and baseline[r['id']] != 'Supported' == candidate[r['id']] for r in rows),
        false_S_avoided=sum(r['GT'] != 'Supported' and baseline[r['id']] == 'Supported' != candidate[r['id']] for r in rows),
        by_GT_prediction={gt:{before:{after:sum(r['GT'] == gt and baseline[r['id']] == before and candidate[r['id']] == after for r in rows)
            for after in c.LABELS} for before in c.LABELS} for gt in c.LABELS})


def point_rule(baseline, candidate, panel):
    """Frozen protocol thresholds; no fitted weights or posthoc new conditions."""
    dm = candidate['mcc'] - baseline['mcc']
    dp = candidate['percent_agreement'] - baseline['percent_agreement']
    df = candidate['false_S'] - baseline['false_S']
    dr = {g:(candidate['per_class'][g]['recall'] - baseline['per_class'][g]['recall'])
        if baseline['per_class'][g]['recall'] is not None else None for g in c.LABELS}
    guards = dict(MCC=dm >= -.03-1e-12, PA=dp >= -.03-1e-12, false_S=df <= 2,
        NS_recall=dr['Not Supported'] is not None and dr['Not Supported'] >= -.10-1e-12,
        NA_recall=dr['Not Addressed'] is not None and dr['Not Addressed'] >= -.10-1e-12)
    if panel == 'natural':
        guards['S_recall'] = dr['Supported'] is not None and dr['Supported'] >= -.03-1e-12
    return dict(delta_MCC=dm, delta_PA=dp, delta_false_S=df, delta_recall=dr,
        signal=dm >= .015-1e-12 or (df <= -2 and dp >= -.02-1e-12),
        guards=guards, guard=all(guards.values()))


def compare(rows_path, baseline_path, candidate_path, scope):
    if scope not in {'fixed_feature', 'gpu_vs_cheap', 'fair_gpu'}:
        raise ValueError('Explicit comparison scope required')
    records = unique_rows(rows_path)
    rows = [r for r in records if r.get('panel') in PANELS]
    if len(rows) != 500 or any(sum(r['panel'] == panel for r in rows) != n for panel, n in PANELS.items()):
        raise ValueError('Fixed metadata must identify natural400 and pressure100')
    if any(r.get('GT') not in c.LABELS or not r.get('sid') for r in rows):
        raise ValueError('Original legal GT and patient IDs required')
    expected = {r['id']:r for r in rows}
    baseline, baseline_arm = load_predictions(baseline_path, expected)
    candidate, candidate_arm = load_predictions(candidate_path, expected)
    if scope == 'fair_gpu' and ('oof' in str(baseline_arm).lower() or '092' in str(baseline_arm).lower()):
        raise ValueError('Old092 OOF cannot serve as the fair GPU control')
    panels = {}
    for panel in PANELS:
        part = [r for r in rows if r['panel'] == panel]
        a, b = metric(part, baseline), metric(part, candidate)
        panels[panel] = dict(N=len(part), patients=len({r['sid'] for r in part}),
            baseline=a, candidate=b, changes=transitions(part, baseline, candidate), **point_rule(a, b, panel))
    keep = all(p['guard'] for p in panels.values()) and any(p['signal'] for p in panels.values())
    return dict(task=108, comparison_scope=scope, baseline_arm=baseline_arm, candidate_arm=candidate_arm,
        direction='candidate minus baseline', all_fixed500_IDs_complete=True, panels=panels,
        prewritten_point_signal=any(p['signal'] for p in panels.values()), all_prewritten_guards_pass=all(p['guard'] for p in panels.values()),
        retains_followup_value_by_fixed_point_rule=keep,
        fair_GPU_method_increment_preserved=keep if scope == 'fair_gpu' else None,
        fair_GPU_configuration_equivalence_requires_external_training_records=True,
        cheap_fixed_feature_or_old_OOF_not_fair_GPU_control=True,
        paired_bootstrap_executed=False, statistical_confirmation_claimed=False,
        new_training=False, model_calls=0, automatic_default_upgrade=False,
        further_selection1317_or_seed2_requires_recorded_protocol_and_remaining_budget=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rows', 'baseline', 'candidate', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--scope', choices=['fixed_feature', 'gpu_vs_cheap', 'fair_gpu'], required=True)
    a = parser.parse_args()
    result = compare(a.rows, a.baseline, a.candidate, a.scope)
    c.put(a.output, result)
    print(c.canonical(dict(output=str(a.output), scope=a.scope, retains_followup_value=result['retains_followup_value_by_fixed_point_rule'],
        panels={name:{key:p[key] for key in ('delta_MCC','delta_PA','delta_false_S','signal','guard')} for name,p in result['panels'].items()})))


if __name__ == '__main__':
    main()
