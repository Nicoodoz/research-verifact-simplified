"""Analyze actual141 first receipts; reuse140/138 evaluation and coverage helpers."""
from pathlib import Path
import argparse
import statistics
import sys

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'tasks/140_kl_anchor'))
from analyze140 import (c, checked_collect, valid_raw, indexed, flat_predictions,
                        common_table, paired_subset, coverage, screening, metrics, LABELS)

P = R / '.local_models/141_two_demos'
K = R / '.local_models/134_author_baselines'
O = R / 'outputs/141_two_demos'
SCOPES = ('screen160', 'old500', 'full1817')
SOURCE120_SHA = '47e129876475499628de7eca934ee9df156dbaef721f8de26abae31853c7a48a'
EXAMPLE_IDS = ('93cd2c13-0d5a-b617-eb23-a479e6549d9b',
               'e96580ee-ad16-3d5a-4b29-3739cd1b46bc')


def check_runtime(job):
    generation = job.get('generation', {})
    if (job.get('adapter_sha256') != SOURCE120_SHA or job.get('max_seq_length') != 32768
            or generation.get('batch_size') != 1 or generation.get('max_new_tokens') != 384
            or generation.get('do_sample') is not False or generation.get('num_beams') != 1
            or generation.get('thinking') is not False or generation.get('repetition_penalty') != 1.0):
        raise ValueError('Expected fixed120, batch1, capacity32768, greedy384 runtime')


def frozen_jobs(scope, keys):
    """Only metadata and frozen examples; no tokenizer/model operations."""
    lengths, records = {}, {}
    demos_sha = None
    for part in SCOPES[:SCOPES.index(scope) + 1]:
        folder = P / part / 'bundle/data'
        job_path = folder / 'job.json'
        if not job_path.exists():
            if part == scope:
                raise FileNotFoundError('Requested141 scope has no frozen job: ' + scope)
            continue
        job = c.read(job_path)
        check_runtime(job)
        if (job.get('task') != 141 or job.get('scope') != part or job.get('variant') != 'two_demos'
                or job.get('arm', 'two_demos') != 'two_demos'):
            raise ValueError('Wrong141 job identity')
        examples_path = folder / 'examples.jsonl'
        examples = c.rows(examples_path)
        if (tuple(r['id'] for r in examples) != EXAMPLE_IDS
                or tuple(r['GT'] for r in examples) != ('Supported', 'Not Supported')
                or tuple(job['example_ids']) != EXAMPLE_IDS):
            raise ValueError('Frozen S then NS example identity changed')
        if any(str(r['sid']) in {str(k['sid']) for k in keys.values()} for r in examples):
            raise ValueError('An evaluation patient was used as a demonstration')
        if any(r['answer'] != c.canonical({'verdict': r['GT']}) for r in examples):
            raise ValueError('Example answers must be original compact labels without reason')
        if c.sha(examples_path) != job['demos_sha256']:
            raise ValueError('Frozen examples file does not match job SHA')
        if demos_sha is not None and demos_sha != job['demos_sha256']:
            raise ValueError('Examples changed between141 scopes')
        demos_sha = job['demos_sha256']
        new = indexed(folder / 'lengths.jsonl')
        if len(new) != job['expected_N'] or set(new) != set(job['ids']):
            raise ValueError('Frozen job and full-prompt length manifest differ')
        for i, row in new.items():
            if i not in keys or row.get('demos_sha256') != demos_sha:
                raise ValueError('Unknown target ID or wrong demonstration SHA')
            if (not row.get('prompt_token_sha256') or not row.get('target_prompt_token_sha256')
                    or row['input_tokens'] + 384 > 32768):
                raise ValueError('Missing full/target prompt identity or oversized complete input')
            if i in lengths and lengths[i] != row:
                raise ValueError('Conflicting frozen141 target')
            lengths[i] = row
        records[part] = dict(job_sha256=c.sha(job_path), lengths_sha256=c.sha(folder / 'lengths.jsonl'),
                             demos_sha256=demos_sha, expected_N=len(new))
    return lengths, records, demos_sha


def collect141(paths):
    raw = checked_collect(paths)
    seen = {}
    for folder in paths:
        for path in Path(folder).glob('*.json'):
            row = c.read(path)
            if 'id' not in row:
                continue
            signature = {k: row.get(k) for k in ('target_prompt_token_sha256', 'demos_sha256',
                                                'finish_reason', 'input_tokens', 'batch_size',
                                                'max_seq_length', 'max_new_tokens')}
            if row['id'] in seen and signature != seen[row['id']]:
                raise ValueError('Conflicting extended first-receipt identity: ' + row['id'])
            seen[row['id']] = signature
    return raw


def historical_predictions(keys):
    specs = [
        ('full_pool120', R / 'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl', 'verdict', 'valid'),
        ('label_only107', R / '.local_models/116_research_cycle/baseline107_selection1817.jsonl', 'verdict', 'valid'),
        ('midpoint132', R / 'outputs/132_midpoint_update/selection1817_predictions_sanitized.jsonl', 'midpoint132', 'midpoint_valid'),
        ('extra_steps137', R / 'outputs/137_extra_steps/full1817_predictions_sanitized.jsonl', 'extra_steps', None),
        ('rationale_tasks138', R / 'outputs/138_rationale_tasks/rationale_tasks_full1817_predictions_sanitized.jsonl', 'prediction', None),
    ]
    models = {name: flat_predictions(indexed(path), keys, field, flag)
              for name, path, field, flag in specs}
    models['paper_r1'] = {i: r['paper_r1'] for i, r in keys.items() if r.get('paper_r1') in LABELS}
    # Optional140: use only actually analyzed valid outputs; it is not a required dependency.
    extra = {}
    for scope in SCOPES:
        path = R / 'outputs/140_kl_anchor' / ('kl_anchor_' + scope + '_predictions_sanitized.jsonl')
        for i, row in indexed(path).items():
            if i in extra and extra[i] != row:
                raise ValueError('Conflicting140 analyzed prediction: ' + i)
            extra[i] = row
    optional = {'kl_anchor140': flat_predictions(extra, keys, 'kl_anchor')} if extra else {}
    return models, optional


def matched_control(valid, target, screen, candidate, old, baseline, keys, bootstrap):
    folder = R / '.local_models/139_full_repeat/claim_control160'
    raw = checked_collect([folder / 'evidence/claim_control'])
    if set(raw) - screen:
        raise ValueError('claim_control160 includes an ID outside its fixed160')
    if raw:
        check_runtime(c.read(folder / 'bundle/data/job.json'))
    for i, row in raw.items():
        if (row.get('arm') != 'claim_control' or row.get('adapter_sha256') != SOURCE120_SHA
                or row.get('batch_size') != 1 or i not in baseline
                or row.get('prompt_token_sha256') != baseline[i].get('prompt_token_sha256')):
            raise ValueError('Wrong139 runtime-control identity: ' + i)
    pred = {i: r['parsed']['verdict'] for i, r in raw.items() if valid_raw(r)}
    eligible = sorted(set(valid) & screen)
    comparison = paired_subset(eligible, pred, candidate, 'claim_control139', keys, bootstrap)
    joint = sorted(screen & pred.keys() & old.keys())
    changed = [i for i in joint if pred[i] != old[i]]
    comparison.update(fixed_scope='screen160_only', expected_N=160,
                      coverage=coverage(screen, raw), candidate_overlap_N=len(eligible),
                      valid_vs136_N=len(joint), control_vs136_changed_ids=changed,
                      all160_labels_equal136=(len(joint) == 160 and not changed),
                      no_extrapolation_to_old500_or_full1817=True)
    return comparison


def analyze(scope, paths=None, bootstrap=False):
    keys = indexed(K / 'keys.jsonl')
    screen = set(c.read(K / 'job.json')['phases'][0]['ids'])
    target = (screen if scope == 'screen160' else
              {i for i, r in keys.items() if scope == 'full1817' or r['old_panel'] in ('natural', 'pressure')})
    if len(target) != dict(screen160=160, old500=500, full1817=1817)[scope]:
        raise ValueError('Frozen134 target changed')
    lengths, jobs, demos_sha = frozen_jobs(scope, keys)
    if not target <= lengths.keys():
        raise ValueError('Requested target lacks frozen141 full-prompt manifests')
    paths = paths or [P / s / 'evidence/two_demos' for s in SCOPES[:SCOPES.index(scope) + 1]]
    raw = collect141(paths)
    if set(raw) - target:
        raise ValueError('141 receipts outside requested target')
    baseline = checked_collect([R / '.local_models/136_claim_repeat_transfer/evidence' / s / 'claim_repeat'
                                for s in SCOPES])
    unverified = []
    for i, row in raw.items():
        expected = lengths[i]
        if (row.get('arm') != 'two_demos' or row.get('adapter_sha256') != SOURCE120_SHA
                or row.get('demos_sha256') != demos_sha
                or row.get('prompt_token_sha256') != expected['prompt_token_sha256']
                or row.get('target_prompt_token_sha256') != expected['target_prompt_token_sha256']
                or row.get('input_tokens') != expected['input_tokens']
                or row.get('batch_size') != 1 or row.get('max_seq_length') != 32768
                or row.get('max_new_tokens') != 384):
            raise ValueError('141 first receipt does not match source/demos/full prompt/runtime: ' + i)
        if (i not in baseline or baseline[i].get('adapter_sha256') != SOURCE120_SHA
                or baseline[i].get('prompt_token_sha256') != expected['target_prompt_token_sha256']
                or baseline[i].get('input_tokens') != expected['target_input_tokens']):
            unverified.append(i)
    candidate = {i: row['parsed']['verdict'] for i, row in raw.items() if valid_raw(row)}
    old = {i: baseline[i]['parsed']['verdict'] for i in target & baseline.keys() if valid_raw(baseline[i])}
    valid = sorted(candidate.keys() & old.keys() - set(unverified))
    if not valid:
        raise ValueError('No verified jointly valid actual141/136 first outputs; no scores written')
    primary = paired_subset(valid, old, candidate, 'claim_repeat136', keys, bootstrap)
    cov = coverage(target, raw)
    history, optional = historical_predictions(keys)
    sources = dict(two_demos=candidate, claim_repeat136=old, **history)
    groups = dict(natural=[i for i in valid if keys[i]['old_panel'] == 'natural'],
                  pressure=[i for i in valid if keys[i]['old_panel'] == 'pressure'],
                  new1317=[i for i in valid if keys[i]['subset'] == 'new'],
                  history103_180=[i for i in valid if keys[i]['history103_panel'] in ('natural', 'pressure')])
    result = dict(task=141, arm='two_demos', scope=scope, adapter_sha256=SOURCE120_SHA,
                  source_adapter_sha256=SOURCE120_SHA, demos_sha256=demos_sha,
                  example_ids=list(EXAMPLE_IDS), expected_N=len(target), valid_N=len(candidate),
                  joint_valid_N=len(valid), primary=primary,
                  standalone_candidate=metrics([keys[i] for i in sorted(candidate)], candidate),
                  coverage=dict(candidate=cov, claim_repeat136=coverage(target, baseline),
                                prompt_unverified_ids=sorted(unverified)),
                  panels={name: paired_subset(ids, old, candidate, 'claim_repeat136', keys)
                          for name, ids in groups.items() if ids},
                  by_author={a: paired_subset([i for i in valid if keys[i]['author'] == a], old, candidate,
                                             'claim_repeat136', keys) for a in sorted({keys[i]['author'] for i in valid})},
                  historical_common=common_table(valid, sources, keys),
                  historical_comparisons={name: common_table(valid, dict(two_demos=candidate, claim_repeat136=old,
                                                                         **{name: values}), keys)
                                          for name, values in history.items()},
                  optional_historical={name: paired_subset(valid, values, candidate, name, keys, bootstrap)
                                       for name, values in optional.items()},
                  screening=screening(primary, cov, scope, unverified),
                  source_artifacts=jobs,
                  bootstrap=dict(performed=bootstrap, iterations=1000 if bootstrap else 0,
                                 method='existing final_compare120.paired / patient cluster bootstrap'),
                  input_cost=dict(received_N=len(raw), batch_size=1, capacity=32768, output_cap=384,
                                  mean_extra_tokens=statistics.mean(lengths[i]['input_tokens'] - lengths[i]['target_input_tokens']
                                                                   for i in raw) if raw else None,
                                  total_extra_tokens=sum(lengths[i]['input_tokens'] - lengths[i]['target_input_tokens'] for i in raw)),
                  new_training=False, new_supervision=False, new_API=0, no_label_rewrite=True,
                  no_postprocessing=True, no_NA_demonstration=True, unchanged_output_format=True,
                  reason_consistency_proven=False)
    result['matched_runtime_control'] = matched_control(valid, target, screen, candidate, old, baseline, keys, bootstrap)
    authors = {a: checked_collect([K / 'bundle/results' / a, K / 'evidence' / a])
               for a in ('author_base9b', 'author_lora9b')}
    author_pred = {a: {i: r['parsed']['verdict'] for i, r in rr.items() if valid_raw(r)} for a, rr in authors.items()}
    result['author_baseline_common'] = common_table(valid, dict(two_demos=candidate, claim_repeat136=old,
                                                               paper_r1=history['paper_r1'], **author_pred), keys)
    result['author_baseline_coverage'] = {a: coverage(target, rr) for a, rr in authors.items()}
    base104_raw = indexed(R / 'outputs/105_brief_supervision/predictions_sanitized.jsonl', 'base_judge')
    original107 = indexed(R / '.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    base104 = {i: row['parsed']['verdict'] for i, row in base104_raw.items()
               if i in original107 and valid_raw(row)
               and row.get('prompt_token_sha256') == original107[i].get('prompt_token_sha256')}
    result['same_prompt_unfinetuned_overlap'] = common_table(valid, dict(two_demos=candidate, claim_repeat136=old,
        base104_9b=base104, full_pool120=history['full_pool120'], label_only107=history['label_only107'],
        paper_r1=history['paper_r1']), keys)
    result['same_prompt_unfinetuned_overlap'].update(raw_coverage=coverage(target, base104_raw),
        prompt_scope='104 base prompt matched to107;136 adds claim_repeat and141 adds two full demonstrations')
    correct = result['standalone_candidate']['correct']
    result['PA_full_target_bounds'] = [correct / len(target), (correct + len(target) - len(candidate)) / len(target)]
    predictions = [dict(keys[i], two_demos=candidate[i], claim_repeat136=old.get(i),
                        primary_joint_valid=i in valid) for i in sorted(candidate)]
    receipts = [dict(id=i, GT=keys[i]['GT'], received=i in raw, valid=i in candidate,
                     primary_joint_valid=i in valid, verdict=candidate.get(i),
                     finish_reason=raw[i].get('finish_reason') if i in raw else None) for i in sorted(target)]
    return result, predictions, receipts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', choices=SCOPES, default='screen160')
    parser.add_argument('--results', type=Path, nargs='+')
    parser.add_argument('--out', type=Path, default=O)
    parser.add_argument('--bootstrap', action='store_true')
    args = parser.parse_args()
    result, predictions, receipts = analyze(args.scope, args.results, args.bootstrap)
    prefix = 'two_demos_' + args.scope
    c.put(args.out / (prefix + '.json'), result)
    c.putl(args.out / (prefix + '_predictions_sanitized.jsonl'), predictions)
    c.putl(args.out / (prefix + '_receipt_status_sanitized.jsonl'), receipts)
    p = result['primary']
    print(c.canonical(dict(scope=args.scope, N=p['N'], delta_MCC=p['delta_MCC'],
                           delta_correct=p['delta_correct'], delta_false_S=p['delta_false_S'],
                           screening=result['screening'])))


if __name__ == '__main__':
    main()
