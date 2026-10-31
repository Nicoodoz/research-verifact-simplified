"""CPU-only preparation from frozen inputs/lengths; never tokenize or score."""
from pathlib import Path
import argparse
import hashlib
import json
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


def source_data():
    original = indexed(ROOT / '.local_models/134_author_baselines/bundle/data/inputs.jsonl')
    legacy = indexed(ROOT / 'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')
    repeated = indexed(ROOT / '.local_models/138_rationale_tasks/extension/source/inputs.jsonl')
    repeated_len = indexed(ROOT / '.local_models/138_rationale_tasks/extension/source/lengths.jsonl')
    reordered, reordered_len = {}, {}
    for scope in ('screen160', 'old500', 'full1817'):
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
    if len(ids) != 1817 or any(set(x) != ids for x in (legacy, repeated, repeated_len, reordered, reordered_len)):
        raise ValueError('Require the same frozen1817 IDs for all three input forms')
    result = {name: {} for name in VARIANTS}
    for i in sorted(ids):
        if legacy[i].get('source_adapter_sha256') != SOURCE_SHA or not legacy[i].get('valid'):
            raise ValueError('120 original receipt model/validity mismatch')
        if any(original[i][k] != repeated[i][k] for k in ('claim', 'reference')):
            raise ValueError('120 and136 original clinical strings differ')
        if reordered[i]['claim'] != original[i]['claim']:
            raise ValueError('142 changed the claim')
        if reordered[i]['source_prompt_token_sha256'] != repeated[i]['prompt_token_sha256']:
            raise ValueError('142 source is not the frozen136 prompt')
        specs = [
            ('native120', original[i], legacy[i]['source_prompt_sha256_104'], legacy[i]['input_tokens']),
            ('claim_repeat136', repeated[i], repeated_len[i]['prompt_token_sha256'], repeated_len[i]['input_tokens']),
            ('relevance_order142', reordered[i], reordered_len[i]['prompt_token_sha256'], reordered_len[i]['input_tokens']),
        ]
        for name, row, sha, length in specs:
            if not sha or length + 4 > 16384:
                raise ValueError('Missing input fingerprint or no room for canonical prefix')
            result[name][i] = dict(id=i, variant=name, claim=row['claim'], reference=row['reference'],
                                   expected_prompt_token_sha256=sha, expected_prompt_tokens=length)
    settings = read(ROOT / '.local_models/142_relevance_order/full1817/bundle/data/job.json')
    return result, settings


def prepare(out, scope='pilot', check_only=False):
    if scope != 'pilot':
        raise ValueError('Only the 27-forward pilot is frozen; no full expansion is authorized')
    data, settings = source_data()
    ids = sorted(data['native120'], key=lambda i: (max(data[v][i]['expected_prompt_tokens'] for v in VARIANTS), i))
    # Nine fixed length ranks; neither labels, GT nor prediction errors are consulted.
    ranks = [round((len(ids) - 1) * n / 8) for n in range(9)]
    pilot = [ids[n] for n in ranks]
    chosen = pilot if scope == 'pilot' else ids
    records = [data[v][i] for i in chosen for v in VARIANTS]
    records.sort(key=lambda r: (-r['expected_prompt_tokens'], r['id'], r['variant']))
    rate3 = read(ROOT / '.local_models/113_label_path/evidence/results/pilot_complete.json')['warm_seconds_per_input_token']
    summaries = {}
    for v in VARIANTS:
        values = [r['expected_prompt_tokens'] for r in data[v].values()]
        summaries[v] = dict(N=len(values), tokens=sum(values), min=min(values), median=statistics.median(values), max=max(values))
    full_tokens = sum(x['tokens'] for x in summaries.values())
    pilot_tokens = sum(data[v][i]['expected_prompt_tokens'] for i in pilot for v in VARIANTS)
    summary = dict(status='CPU_PREPARED_NOT_RUN', scope=scope, full_IDs=1817, variants=list(VARIANTS),
                   pilot_IDs=pilot, pilot_length_ranks=ranks, selected_IDs=len(chosen), forwards=len(records),
                   source_adapter_sha256=SOURCE_SHA, per_variant=summaries,
                   pilot_prompt_tokens=pilot_tokens, full_prompt_tokens=full_tokens,
                   historical_three_path_seconds_per_prompt_token=rate3,
                   optimistic_one_forward_rate=rate3 / 3,
                   pilot_compute_seconds_linear_proxy=pilot_tokens * rate3 / 3,
                   full_compute_seconds_linear_proxy=full_tokens * rate3 / 3,
                   estimate_note='Linear113 proxy only; same architecture, different weights/kernel path. Loading, compilation and return excluded. Measure actual retained pilot first.',
                   no_tokenizer_model_GPU_API=True, no_GT_or_greedy_in_score_inputs=True)
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
               max_seq_length=16384, variants=list(VARIANTS), expected_N=len(records),
               evaluation_scope='full1817', evaluation_ids=sorted(ids),
               score_ids_by_variant={v: sorted(chosen) for v in VARIANTS}, evaluation_metrics_allowed=False,
               prefix='{"verdict":"', prefix_token_ids=[4754, 415, 8217, 3147], branch_ids={'S': 33490, 'Not': 2536},
               input='data/inputs.jsonl', first_results_reused=True, no_training=True, no_generation=True,
               compute_limit_seconds=600, save_reserve_seconds=180, logits_to_keep=1,
               output_hidden_states=False, fixed_referral_percent=[0, 5, 10, 20, 30],
               ranking='ascending logit_S_minus_Not then ID; native Supported only; no label changes')
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
    parser.add_argument('--scope', choices=('pilot',), default='pilot')
    parser.add_argument('--out', type=Path, default=HERE / 'pilot')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare(args.out, args.scope, args.check_only), ensure_ascii=False))


if __name__ == '__main__':
    main()
