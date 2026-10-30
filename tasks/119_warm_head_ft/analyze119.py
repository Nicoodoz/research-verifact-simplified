"""Join recovered GT-free119 receipts to fixed development metadata on CPU.

No inference, training, receipt repair, or imputation.  This analysis does not
establish that the remote training job finished; that needs its runtime files.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models'
OUTPUT = ROOT / 'outputs/119_warm_head_ft'
sys.path.insert(0, str(ROOT / 'tasks/116_research_cycle'))
from analyze_scores116 import section, metrics

LABELS = ('Supported', 'Not Supported', 'Not Addressed')


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines()
            if line.strip()]


def clean_receipt(row):
    if 'GT' in row or 'human_gt' in row:
        raise ValueError('Expected original GT-free screen receipts, not already joined labels')
    if not isinstance(row.get('id'), str) or not row['id']:
        raise ValueError('Receipt lacks a valid ID')
    label = row.get('verdict')
    reason = None
    if row.get('valid') is not True:
        reason = 'worker_reported_invalid' if row.get('valid') is False else 'missing_valid_flag'
    elif label not in LABELS:
        reason = 'invalid_original_label'
    elif 'class_index' in row and (type(row['class_index']) is not int or
                                  row['class_index'] != LABELS.index(label)):
        reason = 'class_index_label_mismatch'
    probabilities = row.get('probabilities')
    if probabilities is not None:
        good = (isinstance(probabilities, dict) and set(probabilities) == set(LABELS)
                and all(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1
                        for p in probabilities.values())
                and abs(sum(probabilities.values()) - 1) <= 1e-4)
        if good and label in LABELS:
            good = probabilities[label] >= max(probabilities.values()) - 1e-7
        if not good:
            reason = reason or 'invalid_probability_record'
            probabilities = None
    result = dict(id=row['id'], valid=reason is None,
                  verdict=label if reason is None else None,
                  receipt_status='valid' if reason is None else 'invalid', invalid_reason=reason,
                  probabilities=probabilities, probabilities_calibrated=False)
    # Whitelist numeric/provenance fields. Never copy content, error prose,
    # paths or the full worker fingerprint into public predictions.
    for name in ('input_tokens', 'selected_step'):
        if type(row.get(name)) is int and row[name] >= 0:
            result[name] = row[name]
    for name in ('source_prompt_sha256_104', 'internal_prompt_sha256',
                 'source_adapter_sha256', 'head_sha256'):
        value = row.get(name)
        if isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value):
            result[name] = value
    return result


def panel_result(rows, baseline, received):
    valid = [row for row in rows if row['id'] in received and received[row['id']]['valid']]
    missing = [row for row in rows if row['id'] not in received]
    invalid = [row for row in rows if row['id'] in received and not received[row['id']]['valid']]
    if valid:
        result = section(valid, baseline, received)
    else:
        result = dict(N=0, scores=None, changes=None, delta_MCC=None,
                      delta_PA=None, delta_correct=None, delta_false_S=None,
                      patient_directions=[], not_evaluable='no_jointly_valid_receipts')
    expected_non_s = sum(row['GT'] != 'Supported' for row in rows)
    unknown_non_s = sum(row['GT'] != 'Supported' for row in missing + invalid)
    observed_fs = result['scores']['candidate']['false_S'] if valid else 0
    result.update(expected_N=len(rows), received_N=len(rows) - len(missing),
                  missing_N=len(missing), invalid_N=len(invalid),
                  valid_fraction=len(valid) / len(rows) if rows else None,
                  missing_GT=dict(Counter(row['GT'] for row in missing)),
                  invalid_GT=dict(Counter(row['GT'] for row in invalid)),
                  expected_non_S=expected_non_s, unknown_non_S=unknown_non_s,
                  false_S_full_cohort_bounds=([observed_fs / expected_non_s,
                                               (observed_fs + unknown_non_s) / expected_non_s]
                                              if expected_non_s else None),
                  baseline_full_panel=metrics(rows, {row['id']: baseline[row['id']]['verdict']
                                                     for row in rows}))
    return result


def analyze(rows, keys, baseline, screen_ids, scope, name='recovered119', model_key='warm_head_ft'):
    if len(screen_ids) != len(set(screen_ids)) or not set(screen_ids) <= set(keys):
        raise ValueError('Invalid frozen screen ID set')
    old_ids = {i for i, row in keys.items() if row.get('old_panel') in ('natural', 'pressure')}
    if not set(screen_ids) <= old_ids:
        raise ValueError('The fixed screen must be nested within the original500')
    wanted = (list(screen_ids) if scope == 'screen160' else
              sorted(old_ids) if scope == 'old500' else sorted(keys))
    received = {}
    for row in rows:
        clean = clean_receipt(row)
        identifier = clean['id']
        if identifier not in wanted:
            raise ValueError('Out-of-scope prediction: ' + identifier)
        if identifier in received:
            raise ValueError('Duplicate first receipt; do not silently choose a replacement: ' + identifier)
        source_hash = clean.get('source_prompt_sha256_104')
        expected_hash = baseline[identifier].get('prompt_token_sha256') if identifier in baseline else None
        if source_hash and expected_hash and source_hash != expected_hash:
            raise ValueError('Recovered prompt differs from the cached107 input: ' + identifier)
        received[identifier] = clean
    steps = {row['selected_step'] for row in received.values() if 'selected_step' in row}
    if len(steps) > 1:
        raise ValueError('Recovered receipts mix selected checkpoints')
    for i in wanted:
        if i not in baseline or baseline[i].get('valid') is not True or baseline[i]['verdict'] not in LABELS:
            raise ValueError('A valid cached107 baseline is required for every requested ID')
    groups = dict(screen160_enriched=[keys[i] for i in screen_ids])
    groups.update({panel: [keys[i] for i in wanted if keys[i].get('old_panel') == panel]
                   for panel in ('natural', 'pressure')})
    if scope == 'selection1817':
        groups.update(selection1817=[keys[i] for i in wanted],
                      new1317=[keys[i] for i in wanted if keys[i].get('subset') == 'new'])
    panels = {panel: panel_result(group, baseline, received)
              for panel, group in groups.items() if group}
    clean_rows = []
    for i in wanted:
        key = keys[i]
        row = dict(id=i, sid=str(key['sid']), GT=key['GT'], author=key['author'],
                   old_panel=key.get('old_panel'), subset=key.get('subset'),
                   baseline107=baseline[i]['verdict'])
        row.update(received.get(i, dict(id=i, valid=False, verdict=None,
                                       receipt_status='missing', invalid_reason=None,
                                       probabilities=None, probabilities_calibrated=False)))
        clean_rows.append(row)
    coverage = dict(expected_N=len(wanted), received_N=len(received),
                    valid_N=sum(row['valid'] for row in received.values()),
                    invalid_N=sum(not row['valid'] for row in received.values()),
                    missing_N=len(wanted) - len(received))
    result = dict(name=name, primary=model_key, scope=scope, models={model_key: dict(
        N=coverage['valid_N'], coverage=coverage, panels=panels)},
        selected_steps_in_receipts=sorted(steps), new_GPU_in_analysis=False,
        confirmation40_used=False, raw_content_copied=False,
        missing_or_invalid_filled_from_baseline=False, bootstrap_performed=False,
        remote_training_completion_inferred=False,
        receipt_boundary='Only recovered predictions are analyzed; training/remote terminal state needs separate evidence')
    return result, clean_rows


def self_test():
    # Synthetic association/coverage only. Does not read or create119 results.
    ids = ('a', 'b', 'c', 'd')
    truth = ('Supported', 'Not Supported', 'Not Addressed', 'Supported')
    keys = {i: dict(id=i, sid=str(k), GT=gt, author='synthetic',
                    old_panel='natural' if k < 3 else 'pressure',
                    subset='old500', paper_r1=gt)
            for k, (i, gt) in enumerate(zip(ids, truth))}
    base = {i: dict(id=i, valid=True, verdict=gt) for i, gt in zip(ids, truth)}
    raw = [dict(id='b', valid=True, verdict='Not Supported', class_index=1,
                content='PRIVATE RAW CONTENT MUST NOT PROPAGATE'),
           dict(id='a', valid=True, verdict='Supported', class_index=0),
           dict(id='c', valid=False, verdict=None, content='PRIVATE INVALID CONTENT')]
    result, cleaned = analyze(raw, keys, base, list(ids), 'screen160')
    part = result['models']['warm_head_ft']['panels']['screen160_enriched']
    if (part['N'], part['invalid_N'], part['missing_N']) != (2, 1, 1):
        raise AssertionError('Invalid/missing coverage was not preserved')
    if 'PRIVATE' in json.dumps(cleaned) or any('content' in row for row in cleaned):
        raise AssertionError('Raw receipt content leaked into sanitized rows')
    if cleaned[-1]['verdict'] is not None or cleaned[-1]['receipt_status'] != 'missing':
        raise AssertionError('Missing prediction was filled with the baseline')
    empty, _ = analyze([], keys, base, list(ids), 'screen160')
    if empty['models']['warm_head_ft']['panels']['screen160_enriched']['scores'] is not None:
        raise AssertionError('No receipts must not create candidate metrics')
    return dict(status='PASS', joins_by_ID=True, raw_content_removed=True,
                invalid_and_missing_visible=True, no_imputation=True,
                no_real119_results_generated=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, nargs='+')
    parser.add_argument('--scope', choices=('screen160', 'old500', 'selection1817'), default='screen160')
    parser.add_argument('--name', default='recovered119')
    parser.add_argument('--model-key', default='warm_head_ft')
    parser.add_argument('--keys', type=Path, default=PRIVATE / '116_research_cycle/keys_selection1817.jsonl')
    parser.add_argument('--baseline', type=Path, default=PRIVATE / '116_research_cycle/baseline107_selection1817.jsonl')
    parser.add_argument('--screen-ids', type=Path, default=PRIVATE / '117_verdict_probe/data_selection.json')
    parser.add_argument('--out-dir', type=Path, default=OUTPUT)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test())); return
    if not args.predictions:
        parser.error('Provide recovered GT-free --predictions; no119 results are inferred')
    if not re.fullmatch('[a-zA-Z0-9_-]+', args.name):
        parser.error('Use a simple output name')
    keys_list = read_rows(args.keys)
    baseline_list = read_rows(args.baseline)
    keys = {row['id']: row for row in keys_list}
    baseline = {row['id']: row for row in baseline_list}
    ids = json.loads(args.screen_ids.read_text(encoding='utf-8-sig'))
    screen_ids = ids['screen_ids'] if isinstance(ids, dict) else ids
    if len(keys) != len(keys_list) or len(baseline) != len(baseline_list):
        raise ValueError('Metadata or baseline has duplicate IDs')
    if len(keys) != 1817 or len(screen_ids) != 160:
        raise ValueError('Expected the fixed1817 cohort and its nested160 screen')
    if sum(row.get('old_panel') == 'natural' for row in keys.values()) != 400 or \
            sum(row.get('old_panel') == 'pressure' for row in keys.values()) != 100:
        raise ValueError('Old400/100 panel membership changed')
    raw = [row for path in args.predictions for row in read_rows(path)]
    if not raw:
        raise ValueError('No recovered119 receipts; do not create an effect table')
    result, sanitized = analyze(raw, keys, baseline, screen_ids, args.scope, args.name, args.model_key)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    path = args.out_dir / (args.name + '.json')
    path.write_bytes((json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())
    (args.out_dir / (args.name + '_predictions_sanitized.jsonl')).write_bytes(
        ('\n'.join(json.dumps(row, ensure_ascii=False, allow_nan=False) for row in sanitized) + '\n').encode())
    print(json.dumps(dict(scope=args.scope, coverage=result['models'][args.model_key]['coverage'],
                          panels={p: {k: v[k] for k in ('N', 'expected_N', 'missing_N', 'invalid_N',
                                                       'delta_MCC', 'delta_PA', 'delta_false_S')}
                                  for p, v in result['models'][args.model_key]['panels'].items()}),
                     ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
