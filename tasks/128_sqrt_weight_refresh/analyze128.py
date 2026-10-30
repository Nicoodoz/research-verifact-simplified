"""Reuse first-receipt parsing and established paired statistics for128."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tasks/120_full_pool_sft'))
from analyze120 import collect, analysis_api
from final_compare120 import lookup, metrics, paired, LABELS
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipts', type=Path, nargs='+', required=True)
    parser.add_argument('--training-done', type=Path, required=True)
    parser.add_argument('--scope', choices=['screen160', 'old500', 'selection1817'], required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not args.tag.replace('_', '').isalnum():
        raise ValueError('Simple output tag required')
    done = common.read(args.training_done)
    if ((done['steps'], done['consumed'], done['additional_steps']) != (369, 2945, 149)
            or done['fingerprint']['task'] != 128):
        raise ValueError('Only the fixed128 final checkpoint may be evaluated')
    keys = lookup(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    base = lookup(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    old220 = lookup(ROOT/'outputs/120_full_pool_sft/midpoint220_1817_predictions_sanitized.jsonl')
    old369 = lookup(ROOT/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')
    raw = collect(args.receipts)
    if not raw or any(r['source_adapter_sha256'] != done['adapter_sha256'] for r in raw):
        raise ValueError('Receipts must come from the fixed128 checkpoint')
    if any(r['source_prompt_sha256_104'] != base[r['id']]['prompt_token_sha256'] for r in raw):
        raise ValueError('Original107 prompt changed')
    screen_data = common.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')
    screen = screen_data['screen_ids'] if isinstance(screen_data, dict) else screen_data
    result, sanitized = analysis_api()(raw, keys, base, screen, args.scope, args.tag, 'sqrt_weight_refresh')
    candidate = {r['id']: r for r in sanitized if r.get('valid')}
    all_ids = set(r['id'] for r in sanitized)
    original103 = lookup(ROOT/'outputs/103_lora_selection/final_paired_predictions.jsonl')
    original105 = {r['id']: r for r in common.rows(ROOT/'outputs/105_brief_supervision/predictions_sanitized.jsonl')
                   if r['arm'] == 'base_judge'}
    groups = {p: [i for i in all_ids if keys[i].get('old_panel') == p] for p in ('natural', 'pressure')}
    if args.scope == 'selection1817':
        if all_ids != set(keys):
            raise ValueError('Complete cohort must cover all1817 IDs')
        groups.update(selection1817=sorted(keys), new1317=[i for i in keys if keys[i].get('subset') == 'new'])
    for panel in ('natural', 'pressure'):
        groups['same103_'+panel] = [i for i in all_ids if i in original103
            and original103[i]['panel'] == panel and original103[i]['arms']['nine_native']['valid']]
        groups['same105_base_'+panel] = [i for i in all_ids if i in original105
            and keys[i].get('old_panel') == panel and original105[i]['parsed']['valid']]
    report = dict(task=128, candidate='sqrt_weight_refresh', training_step=369, additional_steps=149,
        source_adapter_sha256=done['adapter_sha256'], scope=args.scope,
        coverage=result['models']['sqrt_weight_refresh']['coverage'], panels={},
        cohort_role='historically exposed development/selection patients', confirmation40_used=False,
        source_checkpoints_unchanged=True, no_imputation=True)
    for panel, ids in groups.items():
        rows = [keys[i] for i in ids if i in candidate
                and all(model[i].get('valid') is True for model in (base, old220, old369))]
        if not rows:
            continue
        comparators = {'107_label_only': base, '120_step220': old220, '120_step369': old369}
        values = {'paper_r1': {r['id']: r['paper_r1'] for r in rows},
                  '128_sqrt_weight_refresh': {r['id']: candidate[r['id']]['verdict'] for r in rows}}
        values.update({name: {r['id']: model[r['id']]['verdict'] for r in rows} for name, model in comparators.items()})
        if panel.startswith('same103_'):
            values['103_original_prompt_unfinetuned9B'] = {r['id']: original103[r['id']]['predictions']['nine_native'] for r in rows}
        if panel.startswith('same105_base_'):
            values['105_same_prompt_unfinetuned9B'] = {r['id']: original105[r['id']]['parsed']['verdict'] for r in rows}
        report['panels'][panel] = dict(expected_N=len(ids), joint_valid_N=len(rows),
            scores={name: metrics(rows, values_) for name, values_ in values.items()},
            comparisons={name: paired(rows, model, candidate, name, panel == 'selection1817')
                         for name, model in comparators.items()},
            by_author={author: paired([r for r in rows if r['author'] == author], base, candidate, '107_label_only')
                       for author in sorted({r['author'] for r in rows})})
    out = ROOT/'outputs/128_sqrt_weight_refresh'; out.mkdir(parents=True, exist_ok=True)
    common.put(out/(args.tag+'.json'), result)
    common.putl(out/(args.tag+'_predictions_sanitized.jsonl'), sanitized)
    common.put(out/(args.tag+'_comparison.json'), report)
    lines = ['# 128固定平方根权重：实际结果', '',
        '107、120两个检查点及原作者历史结果复用；未微调9B仅列已有同ID覆盖。无效/缺失不补旧答案。', '',
        '|范围／模型|有效／范围|MCC|PA|正确|false-S/非S|S/NS/NA召回|',
        '|---|---:|---:|---:|---:|---:|---|']
    for panel, data in report['panels'].items():
        for name, m in data['scores'].items():
            recalls = '/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.1%}" for g in LABELS)
            lines.append(f"|{panel}/{name}|{data['joint_valid_N']}/{data['expected_N']}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{recalls}|")
    lines += ['', '|范围／参照|ΔMCC|Δ正确|Δfalse-S|S救回/误伤|NS救回/误伤|NA救回/误伤|',
              '|---|---:|---:|---:|---:|---:|---:|']
    for panel, data in report['panels'].items():
        for name, comparison in data['comparisons'].items():
            change = comparison['changes']['by_class']
            classes = '|'.join(f"{change[g]['rescued']}/{change[g]['harmed']}" for g in LABELS)
            lines.append(f"|{panel}/{name}|{comparison['delta_MCC']:+.4f}|{comparison['delta_correct']:+d}|{comparison['delta_false_S']:+d}|{classes}|")
    (out/(args.tag+'_comparison.md')).write_bytes(('\n'.join(lines)+'\n').encode())
    print(common.canonical({name: data['comparisons']['107_label_only']['delta_MCC'] for name, data in report['panels'].items()}))


if __name__ == '__main__':
    main()
