"""CPU-only preparation from frozen inputs/lengths; never tokenize or score."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import statistics

CODE = Path(__file__).resolve().parent
ROOT = next(p for p in CODE.parents if (p / 'tasks/113_label_path').is_dir())
HERE = ROOT / '.local_models/parallel_20261031/selective_verification/native_score_preparation'
SOURCE_SHA = '47e129876475499628de7eca934ee9df156dbaef721f8de26abae31853c7a48a'
VARIANTS = ('native120', 'claim_repeat136', 'relevance_order142')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def indexed(path):
    data = rows(path)
    result = {r['id']: r for r in data}
    if len(data) != len(result):
        raise ValueError('Duplicate IDs: ' + str(path))
    return result


def source_data(include_reordered=True):
    original = indexed(ROOT / '.local_models/134_author_baselines/bundle/data/inputs.jsonl')
    legacy = indexed(ROOT / 'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')
    repeated = indexed(ROOT / '.local_models/138_rationale_tasks/extension/source/inputs.jsonl')
    repeated_len = indexed(ROOT / '.local_models/138_rationale_tasks/extension/source/lengths.jsonl')
    reordered, reordered_len = {}, {}
    for scope in (('screen160', 'old500', 'full1817') if include_reordered else ()):
        data = ROOT / '.local_models/142_relevance_order' / scope / 'bundle/data'
        job = read(data / 'job.json')
        if job['adapter_sha256'] != SOURCE_SHA or job['max_seq_length'] != 16384:
            raise ValueError('142 model identity/capacity differs')
        for i, value in indexed(data / 'inputs.jsonl').items():
            if i in reordered and reordered[i] != value:
                raise ValueError('Conflicting142 input')
            reordered[i] = value
        for i, value in indexed(data / 'lengths.jsonl').items():
            if i in reordered_len and reordered_len[i] != value:
                raise ValueError('Conflicting142 length')
            reordered_len[i] = value
    ids = set(original)
    sources = (legacy, repeated, repeated_len, reordered, reordered_len) if include_reordered else (legacy, repeated, repeated_len)
    if len(ids) != 1817 or any(set(x) != ids for x in sources):
        raise ValueError('Require the same frozen1817 IDs for the requested input forms')
    result = {name: {} for name in (VARIANTS if include_reordered else VARIANTS[:2])}
    for i in sorted(ids):
        if legacy[i].get('source_adapter_sha256') != SOURCE_SHA or not legacy[i].get('valid'):
            raise ValueError('120 original receipt model/validity mismatch')
        if any(original[i][k] != repeated[i][k] for k in ('claim', 'reference')):
            raise ValueError('120 and136 original clinical strings differ')
        if include_reordered:
            if reordered[i]['claim'] != original[i]['claim']:
                raise ValueError('142 changed the claim')
            if reordered[i]['source_prompt_token_sha256'] != repeated[i]['prompt_token_sha256']:
                raise ValueError('142 source is not the frozen136 prompt')
        specs = [
            ('native120', original[i], legacy[i]['source_prompt_sha256_104'], legacy[i]['input_tokens']),
            ('claim_repeat136', repeated[i], repeated_len[i]['prompt_token_sha256'], repeated_len[i]['input_tokens']),
        ]
        if include_reordered:
            specs.append(('relevance_order142', reordered[i], reordered_len[i]['prompt_token_sha256'], reordered_len[i]['input_tokens']))
        for name, row, sha, length in specs:
            if not sha or length + 4 > 16384:
                raise ValueError('Missing input fingerprint or no room for canonical prefix')
            result[name][i] = dict(id=i, variant=name, claim=row['claim'], reference=row['reference'],
                                   expected_prompt_token_sha256=sha, expected_prompt_tokens=length)
    settings = read(ROOT / '.local_models/134_author_baselines/job.json')
    return result, settings


def native_screen_selection(scope='screen160'):
    """Select original native S only; never consult GT for score inclusion."""
    original = read(ROOT / '.local_models/134_author_baselines/job.json')
    parts = ('screen160',) if scope == 'screen160' else ('screen160', 'old500')
    evaluation = [i for phase in original['phases'][:len(parts)] for i in phase['ids']]
    frozen136 = [read(ROOT / '.local_models/136_claim_repeat_transfer' / ('claim_repeat_'+part) / 'bundle/data/job.json') for part in parts]
    prior136 = [i for job in frozen136 for i in job['phases'][0]['ids']]
    expected = 160 if scope == 'screen160' else 500
    if len(evaluation) != expected or len(set(prior136)) != expected or set(evaluation) != set(prior136):
        raise ValueError('134/136 original '+scope+' IDs differ')
    specs = {
        'native120': dict(path='outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl', field='verdict', validity_field='valid'),
        'claim_repeat136': dict(path='outputs/136_claim_repeat_transfer/full1817_predictions_sanitized.jsonl', field='claim_repeat'),
    }
    status136 = indexed(ROOT / 'outputs/136_claim_repeat_transfer' / (scope+'_receipt_status_sanitized.jsonl'))
    selected = {}
    for variant, spec in specs.items():
        source = ROOT / spec['path']
        pred = indexed(source)
        for i in evaluation:
            row = pred[i]
            if row[spec['field']] not in ('Supported', 'Not Supported', 'Not Addressed'):
                raise ValueError('Invalid original prediction')
            if variant == 'native120':
                if row.get('valid') is not True or row['source_adapter_sha256'] != SOURCE_SHA:
                    raise ValueError('Invalid native120 identity')
            elif not status136[i]['valid'] or status136[i]['verdict'] != row[spec['field']]:
                raise ValueError('136 source and original '+scope+' receipt differ')
        selected[variant] = sorted(i for i in evaluation if pred[i][spec['field']] == 'Supported')
        spec['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    return evaluation, selected, specs


def reusable_scores(folders, records):
    expected = {(r['variant'], r['id']): r for r in records}
    found = {}
    for folder in map(Path, folders):
        if not folder.exists():
            raise FileNotFoundError('Explicit reuse source is missing: ' + str(folder))
        manifests = {(r['variant'], r['id']): r for r in rows(folder / 'encoded_manifest.jsonl')}
        cost_files = [dict(path=str((folder/name).resolve()),sha256=hashlib.sha256((folder/name).read_bytes()).hexdigest())
                      for name in ('attempts.jsonl','runtime.json','complete.json','run_exit.json','failure.json') if (folder/name).exists()]
        for key, target in expected.items():
            path = folder / key[0] / (key[1] + '.json')
            if not path.exists():
                continue
            record = read(path)
            encoded = manifests.get(key)
            if (record.get('adapter_sha256') != SOURCE_SHA or record.get('variant') != key[0]
                    or record.get('id') != key[1] or record.get('prompt_token_sha256') != target['expected_prompt_token_sha256']
                    or record.get('original_prompt_tokens') != target['expected_prompt_tokens']
                    or record.get('prefix_token_ids') != [4754, 415, 8217, 3147]
                    or record.get('batch_size') != 1 or record.get('dtype') != 'bfloat16'
                    or record.get('max_seq_length') != 16384 or encoded is None
                    or any(record.get(k) != encoded.get(k) for k in ('prompt_token_sha256', 'scoring_input_token_sha256', 'original_prompt_tokens', 'prefix_token_ids'))
                    or not math.isfinite(record.get('logit_S_minus_Not', float('nan')))):
                raise ValueError('Unverified reusable score: ' + str(path))
            if key in found and found[key]['record'] != record:
                raise ValueError('Conflicting first score in explicit reuse sources')
            found[key] = dict(record=record, encoded=encoded, path=path,source_results_root=str(folder.resolve()),cost_files=cost_files,
                              sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return found


def prepare(out, scope='pilot', check_only=False, reuse_results=(), compute_seconds=None, save_seconds=None):
    if scope not in ('pilot', 'screen160', 'old500'):
        raise ValueError('Only pilot, original screen160 or original old500 is authorized')
    data, settings = source_data(scope=='pilot')
    variants = VARIANTS if scope == 'pilot' else VARIANTS[:2]
    ids = sorted(data['native120'], key=lambda i: (max(data[v][i]['expected_prompt_tokens'] for v in variants), i))
    # Nine fixed length ranks; neither labels, GT nor prediction errors are consulted.
    ranks = [round((len(ids) - 1) * n / 8) for n in range(9)]
    pilot = [ids[n] for n in ranks]
    if scope == 'pilot':
        evaluation = sorted(ids)
        selected = {v: sorted(pilot) for v in variants}
        prediction_sources = None
        compute_seconds = 600 if compute_seconds is None else compute_seconds
        save_seconds = 180 if save_seconds is None else save_seconds
    else:
        evaluation, selected, prediction_sources = native_screen_selection(scope)
    records = [data[v][i] for v in variants for i in selected[v]]
    records.sort(key=lambda r: (-r['expected_prompt_tokens'], r['id'], r['variant']))
    reusable = reusable_scores(reuse_results, records)
    rate3 = read(ROOT / '.local_models/113_label_path/evidence/results/pilot_complete.json')['warm_seconds_per_input_token']
    summaries = {}
    for v in variants:
        values = [r['expected_prompt_tokens'] for r in data[v].values()]
        summaries[v] = dict(N=len(values), tokens=sum(values), min=min(values), median=statistics.median(values), max=max(values))
    full_tokens = sum(x['tokens'] for x in summaries.values())
    pilot_tokens = sum(data[v][i]['expected_prompt_tokens'] for i in pilot for v in variants)
    summary = dict(status='CPU_PREPARED_NOT_RUN', scope=scope, full_IDs=1817, variants=list(VARIANTS),
                   pilot_IDs=pilot, pilot_length_ranks=ranks, selected_IDs=len({r['id'] for r in records}), forwards=len(records),
                   source_adapter_sha256=SOURCE_SHA, per_variant=summaries,
                   pilot_prompt_tokens=pilot_tokens, full_prompt_tokens=full_tokens,
                   historical_three_path_seconds_per_prompt_token=rate3,
                   optimistic_one_forward_rate=rate3 / 3,
                   pilot_compute_seconds_linear_proxy=pilot_tokens * rate3 / 3,
                   full_compute_seconds_linear_proxy=full_tokens * rate3 / 3,
                   estimate_note='Linear113 proxy only; same architecture, different weights/kernel path. Loading, compilation and return excluded. Measure actual retained pilot first.',
                   no_tokenizer_model_GPU_API=True, no_GT_or_greedy_in_score_inputs=True)
    summary.update(variants=list(variants), evaluation_N=len(evaluation),
                   score_N_by_variant={v: len(selected[v]) for v in variants},
                   reusable_score_N=len(reusable), new_forwards=len(records)-len(reusable),
                   pilot_overlap_by_variant={v: sorted(set(selected[v]) & set(pilot)) for v in variants},
                   compute_limit_seconds=compute_seconds, save_reserve_seconds=save_seconds,
                   budget_status='UNFROZEN_DO_NOT_START' if compute_seconds is None or save_seconds is None else 'FROZEN',
                   scope_prompt_tokens=sum(r['expected_prompt_tokens'] for r in records),
                   new_forward_prompt_tokens=sum(r['expected_prompt_tokens'] for r in records if (r['variant'],r['id']) not in reusable))
    summary['reuse_by_variant'] = {v: dict(reused=sum(k[0]==v for k in reusable),
        new_forwards=len(selected[v])-sum(k[0]==v for k in reusable),
        reused_prompt_tokens=sum(data[v][i]['expected_prompt_tokens'] for variant,i in reusable if variant==v),
        new_forward_prompt_tokens=sum(data[v][i]['expected_prompt_tokens'] for i in selected[v] if (v,i) not in reusable)) for v in variants}
    summary['reused_prompt_tokens'] = summary['scope_prompt_tokens']-summary['new_forward_prompt_tokens']
    if scope != 'pilot':
        for field in ('full_IDs', 'pilot_IDs', 'pilot_length_ranks', 'pilot_prompt_tokens', 'full_prompt_tokens',
                      'pilot_compute_seconds_linear_proxy', 'full_compute_seconds_linear_proxy'):
            summary.pop(field)
        summary['source_cache_IDs'] = len(data['native120'])
        summary['scope_compute_seconds_linear_proxy'] = summary['scope_prompt_tokens'] * rate3 / 3
        summary['per_variant'] = {v: dict(N=len(selected[v]),
            tokens=sum(data[v][i]['expected_prompt_tokens'] for i in selected[v]),
            min=min(data[v][i]['expected_prompt_tokens'] for i in selected[v]),
            max=max(data[v][i]['expected_prompt_tokens'] for i in selected[v])) for v in variants}
    if check_only:
        return summary
    out = Path(out)
    if out.exists():
        raise FileExistsError('Prepared destination exists; preserve first outputs: ' + str(out))
    bundle = out / 'bundle'
    (bundle / 'data').mkdir(parents=True)
    (bundle / 'data/inputs.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records),
                                            encoding='utf-8', newline='\n')
    job = dict(name='native_branch_scores', scope=scope, model_dir=settings['model_dir'],
               adapter=settings['adapter'], adapter_bytes=settings['adapter_bytes'], adapter_sha256=SOURCE_SHA,
               max_seq_length=16384, variants=list(variants), expected_N=len(records),
               evaluation_scope='full1817' if scope=='pilot' else scope, evaluation_ids=evaluation,
               score_ids_by_variant=selected, evaluation_metrics_allowed=scope!='pilot',
               prefix='{"verdict":"', prefix_token_ids=[4754, 415, 8217, 3147], branch_ids={'S': 33490, 'Not': 2536},
               input='data/inputs.jsonl', first_results_reused=True, no_training=True, no_generation=True,
               compute_limit_seconds=compute_seconds, save_reserve_seconds=save_seconds, logits_to_keep=1,
               output_hidden_states=False, fixed_referral_percent=[0, 5, 10, 20, 30],
               ranking='ascending logit_S_minus_Not then ID; native Supported only; no label changes')
    if prediction_sources is not None:
        job['native_prediction_sources'] = prediction_sources
    job['reused_score_ids_by_variant'] = {v: sorted(i for variant,i in reusable if variant==v) for v in variants}
    job['reuse_results'] = 'reuse' if reusable else None
    job['new_forwards_expected'] = len(records)-len(reusable)
    job['budget_status'] = summary['budget_status']
    job['reuse_source_artifacts'] = list({item['source_results_root']:dict(results_root=item['source_results_root'],
        cost_files=item['cost_files'],cost_attribution='historical, not new forwards') for item in reusable.values()}.values())
    if reusable:
        provenance = []
        encoded = []
        for (variant, i), item in sorted(reusable.items()):
            target = bundle / 'reuse' / variant / (i + '.json')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item['path'], target)
            encoded.append(item['encoded'])
            provenance.append(dict(id=i, variant=variant, source_path=str(item['path'].resolve()),
                source_sha256=item['sha256'], copied_path=target.relative_to(bundle).as_posix(),
                source_results_root=item['source_results_root'],new_forward=False))
        (bundle/'reuse/encoded_manifest.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in encoded),encoding='utf-8',newline='\n')
        put(bundle / 'reuse/provenance.json', provenance)
    put(bundle / 'data/job.json', job)
    shutil.copy2(CODE / 'worker144.py', bundle / 'score_worker.py')
    for rel in ('tasks/104_supervision_evidence/training104.py', 'tasks/136_claim_repeat_transfer/prompt136.py',
                'tasks/105_brief_supervision/common105.py'):
        target = bundle / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    job['source_files_sha256'] = {str(p.relative_to(bundle)).replace(chr(92), '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(bundle.rglob('*.py'))}
    put(bundle / 'data/job.json', job)
    put(out / 'preparation.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', choices=('pilot','screen160','old500'), default='pilot')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--reuse-results', type=Path, nargs='*', default=[])
    parser.add_argument('--compute-seconds', type=int)
    parser.add_argument('--save-reserve-seconds', type=int)
    args = parser.parse_args()
    target = args.out or (HERE/'pilot' if args.scope=='pilot' else ROOT/'.local_models/144_native_confidence'/args.scope)
    print(json.dumps(prepare(target, args.scope, args.check_only, args.reuse_results,
                             args.compute_seconds, args.save_reserve_seconds), ensure_ascii=False))


if __name__ == '__main__':
    main()
