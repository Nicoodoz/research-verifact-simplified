"""Descriptive same-ID error intersections; no combined prediction or new model."""
from collections import Counter
from itertools import combinations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'outputs/118_full_data_heads/readout_complementarity.json'
LABELS = ('Supported', 'Not Supported', 'Not Addressed')
FILES = {
    'sqrt3675_seed117': 'outputs/118_full_data_heads/reconsidered_refit_sqrt_weight_full_predictions.jsonl',
    'sqrt3675_seed118': 'outputs/118_full_data_heads/seed_stability_full3675_sqrt_seed118_predictions.jsonl',
    'unweighted1024_seed117': 'outputs/117_verdict_probe/reconsidered_extension_verdict_mlp_predictions.jsonl',
    'unweighted1024_seed118': 'outputs/118_full_data_heads/unweighted_workflow_seed118_predictions.jsonl',
    'step220': 'outputs/120_full_pool_sft/midpoint220_1817_predictions_sanitized.jsonl',
}


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def main():
    metadata = rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    key = {r['id']: r for r in metadata}
    if len(key) != len(metadata) or len(key) != 1817:
        raise ValueError('Expected unique original1817 development IDs')
    models = {}
    for name, path in FILES.items():
        records = rows(ROOT/path)
        model = {r['id']: r for r in records}
        if len(model) != len(records) or set(model) != set(key):
            raise ValueError('Model coverage differs: '+name)
        if any(r.get('valid') is not True or r['verdict'] not in LABELS or r['GT'] != key[r['id']]['GT']
               or str(r['sid']) != str(key[r['id']]['sid']) for r in records):
            raise ValueError('Model ID/GT association differs: '+name)
        models[name] = model
    correct = {name: {i for i in key if models[name][i]['verdict'] == key[i]['GT']} for name in models}
    names = list(models)
    all_correct = set.intersection(*correct.values())
    any_correct = set.union(*correct.values())
    all_wrong = set(key)-any_correct
    result = dict(N=1817, labels=list(LABELS), models=FILES, all_correct_N=len(all_correct),
        all_wrong_N=len(all_wrong), mixed_correctness_N=len(key)-len(all_correct)-len(all_wrong),
        no_combined_predictor_created=True, diagnostic_intersections_are_not_deployable_gains=True,
        no_reference_text_read=True, no_training40_missing_evidence_flags_used=True,
        cannot_infer_missing_evidence_from_predictions=True, new_GPU_CNY=0, new_API_CNY=0,
        by_GT={}, pairs={}, family_intersections={})
    for g in LABELS:
        ids = {i for i in key if key[i]['GT'] == g}
        hard = ids & all_wrong
        histogram = Counter(sum(i in correct[name] for name in names) for i in ids)
        consensus = Counter(models[names[0]][i]['verdict'] for i in hard
                            if len({models[name][i]['verdict'] for name in names}) == 1)
        result['by_GT'][g] = dict(N=len(ids), correct_models_histogram={str(n): histogram[n] for n in range(6)},
            all_wrong_N=len(hard), all_correct_N=len(ids & all_correct),
            all_wrong_label_consensus=dict(consensus),
            all_wrong_with_prediction_disagreement=sum(len({models[name][i]['verdict'] for name in names}) > 1 for i in hard),
            all_wrong_each_model_predictions={name: dict(Counter(models[name][i]['verdict'] for i in hard)) for name in names})
    for left, right in combinations(names, 2):
        item = dict(left=left, right=right, by_GT={})
        for g in LABELS:
            ids = {i for i in key if key[i]['GT'] == g}
            item['by_GT'][g] = dict(N=len(ids), both_correct=len(ids & correct[left] & correct[right]),
                both_wrong=len(ids-correct[left]-correct[right]),
                left_rescues_right_error=len(ids & (correct[left]-correct[right])),
                left_harms_right_correct=len(ids & (correct[right]-correct[left])))
        non_s = {i for i in key if key[i]['GT'] != 'Supported'}
        item['false_S_left_relative_to_right'] = dict(
            new=sum(models[left][i]['verdict'] == 'Supported' and models[right][i]['verdict'] != 'Supported' for i in non_s),
            avoided=sum(models[left][i]['verdict'] != 'Supported' and models[right][i]['verdict'] == 'Supported' for i in non_s))
        result['pairs'][left+'__'+right] = item
    sqrt_both = correct[names[0]] & correct[names[1]]
    sqrt_neither = set(key)-correct[names[0]]-correct[names[1]]
    unweighted_both = correct[names[2]] & correct[names[3]]
    unweighted_neither = set(key)-correct[names[2]]-correct[names[3]]
    family_groups = dict(sqrt_both_correct_unweighted_both_wrong=sqrt_both & unweighted_neither,
        unweighted_both_correct_sqrt_both_wrong=unweighted_both & sqrt_neither,
        sqrt_both_correct_step220_wrong=sqrt_both-correct['step220'],
        step220_correct_sqrt_both_wrong=correct['step220'] & sqrt_neither,
        only_sqrt_family_stably_correct=sqrt_both & unweighted_neither-correct['step220'])
    for name, ids in family_groups.items():
        result['family_intersections'][name] = dict(N=len(ids), by_GT=dict(Counter(key[i]['GT'] for i in ids)))
    result['common_error_patients'] = [dict(sid=sid, N=sum(str(key[i]['sid']) == sid for i in all_wrong),
        by_GT=dict(Counter(key[i]['GT'] for i in all_wrong if str(key[i]['sid']) == sid)))
        for sid in sorted({str(key[i]['sid']) for i in all_wrong})]
    result['common_error_authors'] = {a: dict(Counter(key[i]['GT'] for i in all_wrong if key[i]['author'] == a))
        for a in sorted({key[i]['author'] for i in all_wrong})}
    OUT.write_bytes((json.dumps(result, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k: result[k] for k in ('all_correct_N', 'all_wrong_N', 'mixed_correctness_N',
        'by_GT', 'family_intersections', 'common_error_authors')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
