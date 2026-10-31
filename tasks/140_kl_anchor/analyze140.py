"""Score actual fixed48 KL outputs with the existing138 evaluation functions."""
from pathlib import Path
import argparse
import sys

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'tasks/138_rationale_tasks'))
from analyze138 import c, collect, metrics, paired, LABELS

P = R / '.local_models/140_kl_anchor'
P138 = R / '.local_models/138_rationale_tasks'
K = R / '.local_models/134_author_baselines'
O = R / 'outputs/140_kl_anchor'
SCOPES = ('screen160', 'old500', 'full1817')


def indexed(path, arm=None):
    rows = c.rows(path) if path.exists() else []
    if arm is not None:
        rows = [r for r in rows if r.get('arm') == arm]
    result = {r['id']: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate IDs: ' + str(path))
    return result


def valid_raw(row):
    parsed = row.get('parsed', {})
    return parsed.get('valid') is True and parsed.get('verdict') in LABELS


def checked_collect(paths):
    """Retain138 first-output collection, additionally reject identity conflicts."""
    result = collect(paths)
    seen = {}
    for folder in paths:
        for path in Path(folder).glob('*.json'):
            row = c.read(path)
            if 'id' not in row:
                continue
            signature = {k: row.get(k) for k in
                         ('content', 'parsed', 'arm', 'adapter_sha256', 'prompt_token_sha256')}
            if row['id'] in seen and seen[row['id']] != signature:
                raise ValueError('Conflicting first receipt identity: ' + row['id'])
            seen[row['id']] = signature
    return result


def completed(path, arm):
    done = c.read(path)
    if (done.get('steps'), done.get('consumed')) != (48, 384):
        raise ValueError('Only actual completed48/384 training is eligible')
    if done.get('arm') != arm or not done.get('adapter_sha256'):
        raise ValueError('Training identity does not match ' + arm)
    return done


def verify_receipts(raw, done, arm, keys, reference):
    if set(raw) - set(keys):
        raise ValueError('Unknown evaluation IDs in ' + arm)
    for i, row in raw.items():
        if row.get('arm') != arm or row.get('adapter_sha256') != done['adapter_sha256']:
            raise ValueError('Wrong fixed adapter or arm: ' + i)
        if i in reference and row.get('prompt_token_sha256') != reference[i].get('prompt_token_sha256'):
            raise ValueError('Not the exact136 evaluation prompt: ' + i)


def coverage(target, raw):
    received = target & raw.keys()
    return dict(expected_N=len(target), received_N=len(received),
                valid_N=sum(valid_raw(raw[i]) for i in received),
                missing_ids=sorted(target - raw.keys()),
                invalid_ids=sorted(i for i in received if not valid_raw(raw[i])))


def flat_predictions(rows, keys, field, validity=None):
    result = {}
    for i, row in rows.items():
        if i not in keys:
            continue
        for name in ('GT', 'sid', 'claim_sha256', 'reference_sha256'):
            if name in row and str(row[name]) != str(keys[i][name]):
                raise ValueError('Historical identity changed: ' + i)
        if (validity is None or row.get(validity) is True) and row.get(field) in LABELS:
            if row.get('receipt_status') not in ('missing', 'invalid'):
                result[i] = row[field]
    return result


def common_table(ids, sources, keys):
    joint = sorted(set(ids).intersection(*(set(v) for v in sources.values())))
    return dict(N=len(joint), missing_by_model={name: sorted(set(ids) - values.keys())
                for name, values in sources.items()},
                scores={name: metrics([keys[i] for i in joint], values)
                        for name, values in sources.items()} if joint else {})


def paired_subset(ids, reference, candidate, name, keys, bootstrap=False):
    joint = sorted(set(ids) & reference.keys() & candidate.keys())
    if not joint:
        return dict(N=0, scores={})
    return paired([keys[i] for i in joint],
                  {i: {'verdict': reference[i]} for i in joint},
                  {i: {'verdict': candidate[i]} for i in joint}, name, bootstrap=bootstrap)


def screening(primary, cov, scope, prompt_unverified):
    small = scope == 'screen160'
    before, after = primary['scores']['claim_repeat136'], primary['scores']['candidate']
    quality = primary['delta_MCC'] >= (.015 if small else .01) or (
        primary['delta_correct'] >= (3 if small else 5) and primary['delta_MCC'] >= -.01)
    risk = (primary['delta_false_S'] <= (-2 if small else -5)
            and primary['delta_correct'] >= (-3 if small else -5)
            and primary['delta_MCC'] >= (-.03 if small else -.02))
    guards = dict(complete_coverage=not cov['missing_ids'],
                  valid_coverage=primary['N'] / cov['expected_N'] >= .95,
                  all_prompts_verified=not prompt_unverified,
                  false_S_increase=primary['delta_false_S'] <= (3 if small else 5),
                  no_major_class_loss=all(after['per_class'][g]['tp'] >= .5 * before['per_class'][g]['tp']
                                          for g in LABELS if before['per_class'][g]['tp'] >= 6))
    return dict(quality_signal=quality, risk_signal=risk, guards=guards,
                continue_signal=all(guards.values()) and (quality or risk))


def analyze(scope, paths=None, bootstrap=False):
    done_path = P / 'evidence/training_done.json'
    done = completed(done_path, 'kl_anchor')
    keys = indexed(K / 'keys.jsonl')
    target = (set(c.read(K / 'job.json')['phases'][0]['ids']) if scope == 'screen160' else
              {i for i, r in keys.items() if scope == 'full1817' or r['old_panel'] in ('natural', 'pressure')})
    expected = dict(screen160=160, old500=500, full1817=1817)[scope]
    if len(target) != expected or not target <= keys.keys():
        raise ValueError('The frozen134 evaluation set changed')
    paths = paths or [P / 'evidence/predictions', *[
        P / 'extension' / name / 'evidence/kl_anchor' for name in SCOPES]]
    raw = checked_collect(paths)
    baseline = checked_collect([R / '.local_models/136_claim_repeat_transfer/evidence' / name / 'claim_repeat'
                                for name in SCOPES])
    verify_receipts(raw, done, 'kl_anchor', keys, baseline)
    candidate = {i: raw[i]['parsed']['verdict'] for i in target & raw.keys() if valid_raw(raw[i])}
    old = {i: baseline[i]['parsed']['verdict'] for i in target & baseline.keys() if valid_raw(baseline[i])}
    prompt_unverified = sorted(target & raw.keys() - baseline.keys())
    valid = sorted(candidate.keys() & old.keys())
    if not valid:
        raise ValueError('No jointly valid actual140/136 first outputs; no scoring artifacts written')
    primary = paired_subset(valid, old, candidate, 'claim_repeat136', keys, bootstrap)
    cov = coverage(target, raw)
    groups = dict(natural=[i for i in valid if keys[i]['old_panel'] == 'natural'],
                  pressure=[i for i in valid if keys[i]['old_panel'] == 'pressure'],
                  new1317=[i for i in valid if keys[i]['subset'] == 'new'],
                  history103_180=[i for i in valid if keys[i]['history103_panel'] in ('natural', 'pressure')])
    historical = {}
    for name, path, field, flag in [
        ('full_pool120', R / 'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl', 'verdict', 'valid'),
        ('label_only107', R / '.local_models/116_research_cycle/baseline107_selection1817.jsonl', 'verdict', 'valid'),
        ('midpoint132', R / 'outputs/132_midpoint_update/selection1817_predictions_sanitized.jsonl', 'midpoint132', 'midpoint_valid'),
        ('extra_steps137', R / 'outputs/137_extra_steps/full1817_predictions_sanitized.jsonl', 'extra_steps', None)]:
        historical[name] = flat_predictions(indexed(path), keys, field, flag)
    historical['paper_r1'] = {i: keys[i]['paper_r1'] for i in target if keys[i]['paper_r1'] in LABELS}
    history_sources = dict(claim_repeat136=old, kl_anchor=candidate, **historical)
    result = dict(task=140, arm='kl_anchor', scope=scope, expected_N=len(target),
                  valid_N=len(candidate), joint_valid_N=len(valid),
                  source_adapter_sha256=done['adapter_sha256'], training_steps=48, training_consumed=384,
                  coverage=dict(candidate=cov, claim_repeat136=coverage(target, baseline),
                                prompt_unverified_ids=prompt_unverified),
                  primary=primary, standalone_candidate=metrics([keys[i] for i in sorted(candidate)], candidate),
                  panels={name: paired_subset(ids, old, candidate, 'claim_repeat136', keys)
                          for name, ids in groups.items() if ids},
                  by_author={a: paired_subset([i for i in valid if keys[i]['author'] == a], old, candidate,
                                             'claim_repeat136', keys) for a in sorted({keys[i]['author'] for i in valid})},
                  historical_common=common_table(valid, history_sources, keys),
                  historical_comparisons={name: common_table(valid, dict(claim_repeat136=old, kl_anchor=candidate,
                                                                         **{name: values}), keys)
                                          for name, values in historical.items()},
                  screening=screening(primary, cov, scope, prompt_unverified),
                  bootstrap=dict(performed=bootstrap, iterations=1000 if bootstrap else 0,
                                 method='existing final_compare120.paired / patient cluster bootstrap'),
                  source_artifacts=dict(training_done_sha256=c.sha(done_path),
                                        keys134_sha256=c.sha(K / 'keys.jsonl'),
                                        job134_sha256=c.sha(K / 'job.json')),
                  new_training=False, new_inference=False, no_label_rewrite=True)
    author_raw = {name: checked_collect([K / 'bundle/results' / name, K / 'evidence' / name])
                  for name in ('author_base9b', 'author_lora9b')}
    author_sources = {name: {i: row['parsed']['verdict'] for i, row in data.items() if valid_raw(row)}
                      for name, data in author_raw.items()}
    result['author_baseline_common'] = common_table(valid, dict(claim_repeat136=old, kl_anchor=candidate,
                                                               paper_r1=historical['paper_r1'], **author_sources), keys)
    result['author_baseline_coverage'] = {name: coverage(target, rows) for name, rows in author_raw.items()}
    base104_raw = indexed(R / 'outputs/105_brief_supervision/predictions_sanitized.jsonl', 'base_judge')
    original107 = indexed(R / '.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    base104 = {i: row['parsed']['verdict'] for i, row in base104_raw.items()
               if i in original107 and valid_raw(row) and row.get('prompt_token_sha256')
               == original107[i].get('prompt_token_sha256')}
    result['same_prompt_unfinetuned_overlap'] = common_table(valid,
        dict(base104_9b=base104, claim_repeat136=old, kl_anchor=candidate,
             label_only107=historical['label_only107'], full_pool120=historical['full_pool120'],
             paper_r1=historical['paper_r1']), keys)
    result['same_prompt_unfinetuned_overlap']['prompt_scope'] = (
        'base104 SHA equals original107/120 base prompt;136/140 additionally use claim_repeat')
    result['same_prompt_unfinetuned_overlap']['raw_coverage'] = coverage(target, base104_raw)
    result['same_prompt_unfinetuned_overlap']['prompt_mismatch_or_unverified_ids'] = sorted(
        i for i in target & base104_raw.keys() if valid_raw(base104_raw[i]) and i not in base104)
    result['matched138'] = {}
    for arm in ('label_replay', 'rationale_tasks'):
        other = checked_collect([P138 / arm / 'evidence' / name for name in ('predictions', 'old500', 'full1817')]
                                + [P138 / 'extension' / arm / name / 'evidence' / arm for name in SCOPES])
        if other:
            other_done = completed(P138 / arm / 'evidence/training_done.json', arm)
            verify_receipts(other, other_done, arm, keys, baseline)
        other_pred = {i: other[i]['parsed']['verdict'] for i in target & other.keys()
                      if valid_raw(other[i]) and i in baseline}
        comparison = paired_subset(valid, other_pred, candidate, '138_' + arm, keys, bootstrap)
        comparison.update(coverage=coverage(target, other), descriptive_only=arm == 'rationale_tasks')
        if arm == 'label_replay' and other:
            files = ('train.jsonl', 'train_tokens.jsonl', 'plan.json')
            fingerprints = {name: c.sha(P / 'bundle/data' / name) for name in files}
            if any(fingerprints[name] != c.sha(P138 / arm / 'bundle/data' / name) for name in files):
                raise ValueError('140 and138 replay training inputs/order are not identical')
            comparison['matched_training_file_SHA256'] = fingerprints
        result['matched138'][arm] = comparison
    sanitized = [dict(keys[i], kl_anchor=candidate[i], claim_repeat136=old.get(i),
                      primary_joint_valid=i in old) for i in sorted(candidate)]
    receipts = [dict(id=i, GT=keys[i]['GT'], received=i in raw,
                     valid=i in candidate, verdict=candidate.get(i),
                     baseline_received=i in baseline, baseline_valid=i in old,
                     primary_joint_valid=i in candidate and i in old) for i in sorted(target)]
    return result, sanitized, receipts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', choices=SCOPES, default='screen160')
    parser.add_argument('--results', type=Path, nargs='+')
    parser.add_argument('--bootstrap', action='store_true')
    args = parser.parse_args()
    result, predictions, receipts = analyze(args.scope, args.results, args.bootstrap)
    prefix = 'kl_anchor_' + args.scope
    c.put(O / (prefix + '.json'), result)
    c.putl(O / (prefix + '_predictions_sanitized.jsonl'), predictions)
    c.putl(O / (prefix + '_receipt_status_sanitized.jsonl'), receipts)
    p = result['primary']
    print(c.canonical(dict(scope=args.scope, N=p['N'], delta_MCC=p['delta_MCC'],
                           delta_correct=p['delta_correct'], delta_false_S=p['delta_false_S'],
                           matched_replay_N=result['matched138']['label_replay']['N'],
                           screening=result['screening'])))


if __name__ == '__main__':
    main()
