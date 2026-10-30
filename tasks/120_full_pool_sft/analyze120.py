"""CPU-only120 analysis of first raw receipts; no imputation or model calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models'
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as common
from parse105 import parse


def batch_files(folder):
    folder = Path(folder)
    if (folder / 'batches').is_dir():
        folder = folder / 'batches'
    return sorted(p for p in folder.glob('*.json')
                  if p.stem.isdigit() and '.inflight.' not in p.name)


def sanitize_record(row):
    """Drop raw output and private runtime metadata before analysis or publication."""
    if {'GT', 'human_gt'} & set(row):
        raise ValueError('Raw inference receipts must be GT-free')
    if not isinstance(row.get('id'), str) or not row['id']:
        raise ValueError('Receipt has no ID')
    parsed = parse(row.get('content'), row.get('finish_reason'))
    if parsed != row.get('parsed'):
        raise ValueError('Stored parser result differs from original parse105: ' + row['id'])
    source = row.get('adapter_sha256')
    prompt = row.get('source_prompt_sha256_104')
    if any(not isinstance(x, str) or not re.fullmatch('[0-9a-f]{64}', x)
           for x in (source, prompt)):
        raise ValueError('Missing adapter/prompt provenance: ' + row['id'])
    out = dict(id=row['id'], valid=parsed['valid'], verdict=parsed['verdict'],
               probabilities=None, source_adapter_sha256=source,
               source_prompt_sha256_104=prompt)
    if type(row.get('input_tokens')) is int and row['input_tokens'] >= 0:
        out['input_tokens'] = row['input_tokens']
    return out


def collect(folders):
    rows = []
    seen = set()
    for folder in folders:
        for path in batch_files(folder):
            batch = common.read(path)
            raw = batch.get('records', [])
            if batch.get('ids') != [row.get('id') for row in raw] or not raw:
                raise ValueError('Batch ID/record mismatch: ' + str(path))
            for row in raw:
                clean = sanitize_record(row)
                if clean['id'] in seen:
                    raise ValueError('Duplicate first receipt: ' + clean['id'])
                seen.add(clean['id'])
                rows.append(clean)
    if len({r['source_adapter_sha256'] for r in rows}) > 1:
        raise ValueError('Cannot combine predictions from different120 checkpoints')
    return rows


def analysis_api():
    sys.path.insert(0, str(ROOT / 'tasks/119_warm_head_ft'))
    from analyze119 import analyze
    return analyze


def self_test():
    labels = ('Supported', 'Not Supported', 'Not Addressed', 'Supported')
    keys = {str(n): dict(id=str(n), sid=str(n), GT=g, author='synthetic',
                        old_panel='natural' if n < 3 else 'pressure',
                        subset='old500', paper_r1=g) for n, g in enumerate(labels)}
    base = {i: dict(id=i, valid=True, verdict=r['GT']) for i, r in keys.items()}
    rows = []
    for i, text, finish in [('0', '{"verdict":"Supported"}', 'stop'),
                            ('1', '{"verdict":"Not Supported"}', 'stop'),
                            ('2', 'PRIVATE UNPARSEABLE TEXT', 'length')]:
        rows.append(sanitize_record(dict(id=i, content=text, finish_reason=finish,
                    parsed=parse(text, finish), adapter_sha256='a'*64,
                    source_prompt_sha256_104='b'*64, fingerprint={'private': 'path'})))
    result, paired = analysis_api()(rows, keys, base, list(keys), 'screen160',
                                    'synthetic120', 'full_pool_sft')
    part = result['models']['full_pool_sft']['panels']['screen160_enriched']
    assert (part['N'], part['invalid_N'], part['missing_N']) == (2, 1, 1)
    assert paired[-1]['verdict'] is None and paired[-1]['receipt_status'] == 'missing'
    assert 'PRIVATE' not in json.dumps(paired) and all('content' not in x for x in rows)
    assert result['missing_or_invalid_filled_from_baseline'] is False
    return dict(PASS=True, raw_content_removed=True, GT_free_receipt_conversion=True,
                invalid_missing_preserved=True, metrics_reuse119_116=True,
                new_GPU=False, real120_results_generated=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--receipts', type=Path, nargs='+')
    p.add_argument('--scope', choices=('screen160', 'old500', 'selection1817'), default='screen160')
    p.add_argument('--name', default='full_pool_sft160')
    p.add_argument('--keys', type=Path, default=PRIVATE/'116_research_cycle/keys_selection1817.jsonl')
    p.add_argument('--baseline', type=Path, default=PRIVATE/'116_research_cycle/baseline107_selection1817.jsonl')
    p.add_argument('--screen-ids', type=Path, default=PRIVATE/'117_verdict_probe/data_selection.json')
    p.add_argument('--out-dir', type=Path, default=ROOT/'outputs/120_full_pool_sft')
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        print(common.canonical(self_test())); return
    if not a.receipts or not re.fullmatch('[A-Za-z0-9_-]+', a.name):
        p.error('Provide --receipts and a simple output name')
    raw_keys, raw_base = common.rows(a.keys), common.rows(a.baseline)
    keys, baseline = ({r['id']: r for r in raw} for raw in (raw_keys, raw_base))
    selection = common.read(a.screen_ids)
    screen = selection['screen_ids'] if isinstance(selection, dict) else selection
    if (len(keys) != len(raw_keys) or len(baseline) != len(raw_base)
            or len(keys) != 1817 or len(screen) != 160 or len(set(screen)) != 160
            or sum(r.get('old_panel') == 'natural' for r in raw_keys) != 400
            or sum(r.get('old_panel') == 'pressure' for r in raw_keys) != 100):
        raise ValueError('Fixed1817, old400/100 or nested160 metadata changed')
    rows = collect(a.receipts)
    if not rows:
        raise ValueError('No committed120 receipts; no effect table is inferred')
    result, paired = analysis_api()(rows, keys, baseline, screen, a.scope, a.name, 'full_pool_sft')
    result.update(source_adapter_sha256=rows[0]['source_adapter_sha256'],
                  parser='unchanged parse105.parse', conditional_training_status='not_inferred_by_analysis')
    common.putl(PRIVATE/'120_full_pool_sft'/(a.name+'_receipts_gt_free.jsonl'), rows)
    common.put(a.out_dir/(a.name+'.json'), result)
    common.putl(a.out_dir/(a.name+'_predictions_sanitized.jsonl'), paired)
    print(common.canonical(dict(scope=a.scope, coverage=result['models']['full_pool_sft']['coverage'],
          panels={name: {k: v[k] for k in ('N', 'expected_N', 'missing_N', 'invalid_N',
                                         'delta_MCC', 'delta_PA', 'delta_correct', 'delta_false_S')}
                  for name, v in result['models']['full_pool_sft']['panels'].items()})))


if __name__ == '__main__':
    main()
