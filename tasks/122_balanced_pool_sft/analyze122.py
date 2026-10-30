"""CPU analysis of fixed-final92-step122 first receipts; no model calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models'
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/120_full_pool_sft'))
from analyze120 import collect
sys.path.insert(0, str(ROOT/'tasks/119_warm_head_ft'))
from analyze119 import analyze

SCOPES = {'160': 'screen160', '500': 'old500', '1817': 'selection1817'}


def fixed_final(path, rows):
    if path.is_dir() and path.name == 'batches':
        path = path.parent
    path = path/'training_done.json' if path.is_dir() else path
    done = common.read(path)
    if (done.get('steps'), done.get('consumed')) != (92, 729):
        raise ValueError('122 is fixed-final92 with exactly729 presentations; no intermediate substitute')
    if (done.get('fingerprint', {}).get('task'), done.get('fingerprint', {}).get('candidate')) != (122, 'balanced_pool_sft'):
        raise ValueError('Training completion belongs to another experiment')
    sha = done.get('adapter_sha256')
    if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
        raise ValueError('Missing final122 adapter identity')
    if any(row['source_adapter_sha256'] != sha for row in rows):
        raise ValueError('Receipts do not come from the fixed final122 adapter')
    return sha


def self_test():
    ids = ['a', 'b', 'c', 'd']
    labels = ['Supported', 'Not Supported', 'Not Addressed', 'Supported']
    keys = {i: dict(id=i, sid=str(n), GT=g, author='synthetic', old_panel='natural',
                    subset='old500', paper_r1=g) for n, (i, g) in enumerate(zip(ids, labels))}
    baseline = {i: dict(id=i, valid=True, verdict=g) for i, g in zip(ids, labels)}
    rows = [dict(id='a', valid=True, verdict='Supported', selected_step=92),
            dict(id='b', valid=True, verdict='Not Supported', selected_step=92),
            dict(id='c', valid=False, verdict=None, selected_step=92)]
    result, paired = analyze(rows, keys, baseline, ids, 'screen160', 'synthetic122', 'balanced_pool_sft')
    panel = result['models']['balanced_pool_sft']['panels']['screen160_enriched']
    assert (panel['N'], panel['invalid_N'], panel['missing_N']) == (2, 1, 1)
    assert paired[-1]['verdict'] is None and result['selected_steps_in_receipts'] == [92]
    assert result['missing_or_invalid_filled_from_baseline'] is False
    return dict(PASS=True, invalid_missing_preserved=True, fixed_final92=True,
                no_real_results_generated=True, new_GPU=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--receipts', type=Path, nargs='+')
    p.add_argument('--training-result', type=Path)
    p.add_argument('--scope', choices=tuple(SCOPES), default='160')
    p.add_argument('--name')
    p.add_argument('--keys', type=Path, default=PRIVATE/'116_research_cycle/keys_selection1817.jsonl')
    p.add_argument('--baseline', type=Path, default=PRIVATE/'116_research_cycle/baseline107_selection1817.jsonl')
    p.add_argument('--screen-ids', type=Path, default=PRIVATE/'117_verdict_probe/data_selection.json')
    p.add_argument('--out-dir', type=Path, default=ROOT/'outputs/122_balanced_pool_sft')
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        print(common.canonical(self_test())); return
    if not a.receipts:
        p.error('--receipts requires returned raw batch directories')
    name = a.name or 'balanced_pool_sft'+a.scope
    if not re.fullmatch('[A-Za-z0-9_-]+', name):
        p.error('Use a simple output name')
    rows = collect(a.receipts)
    if not rows:
        raise ValueError('No committed122 first receipts; do not infer a classification result')
    source_sha = fixed_final(a.training_result or a.receipts[0], rows)
    for row in rows:
        row['selected_step'] = 92
    key_rows, baseline_rows = common.rows(a.keys), common.rows(a.baseline)
    keys = {r['id']: r for r in key_rows}
    baseline = {r['id']: r for r in baseline_rows}
    ids = common.read(a.screen_ids)
    ids = ids['screen_ids'] if isinstance(ids, dict) else ids
    if len(keys) != len(key_rows) or len(baseline) != len(baseline_rows) or len(keys) != 1817 or len(ids) != 160:
        raise ValueError('Fixed unique1817 cohort or nested160 differs')
    if tuple(sum(r.get('old_panel') == panel for r in key_rows) for panel in ('natural', 'pressure')) != (400, 100):
        raise ValueError('Original400/100 membership differs')
    result, paired = analyze(rows, keys, baseline, ids, SCOPES[a.scope], name, 'balanced_pool_sft')
    result.update(task=122, source_adapter_sha256=source_sha,
                  training_completion_verified=dict(steps=92, presentations=729),
                  checkpoint_selection='fixed_final92; no development checkpoint selection',
                  parser='unchanged parse105.parse')
    common.putl(PRIVATE/'122_balanced_pool_sft'/(name+'_receipts_gt_free.jsonl'), rows)
    common.put(a.out_dir/(name+'.json'), result)
    common.putl(a.out_dir/(name+'_predictions_sanitized.jsonl'), paired)
    print(common.canonical(dict(scope=a.scope, source_adapter_sha256=source_sha,
          coverage=result['models']['balanced_pool_sft']['coverage'],
          panels={name: {k: panel[k] for k in ('N', 'expected_N', 'invalid_N', 'missing_N',
                   'delta_MCC', 'delta_PA', 'delta_correct', 'delta_false_S')}
                  for name, panel in result['models']['balanced_pool_sft']['panels'].items()})))


if __name__ == '__main__':
    main()
