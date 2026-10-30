"""Repeat the original unweighted MLP selection algorithm at the same seed118.

Distinct from the preserved fixed6-epoch seed118 diagnostic. No new seed or
evaluation-driven epoch selection. All fitting calls the original fit_mlp117.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models/117_verdict_probe/unweighted_workflow_seed118'
PUBLIC = ROOT/'outputs/118_full_data_heads'
SOURCE = ROOT/'.local_models/117_verdict_probe'
import fit_mlp117 as original
import score_mlp117
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import section


def run():
    protocol = common.read(PRIVATE/'protocol.json')
    if (PUBLIC/'unweighted_workflow_seed118.json').exists():
        raise FileExistsError('Preserve this single same-seed original-algorithm replication')
    if original.CONFIG.get('class_weight') is not None or (original.CONFIG['max_epochs'], original.CONFIG['early_stopping_patience']) != (40, 8):
        raise ValueError('The original unweighted algorithm differs')
    original.CONFIG['seed'] = 118  # Process-local; the original source file is unchanged.
    summary = original.fit_mlp(SOURCE/'evidence/features_initial', SOURCE/'metadata.jsonl', PRIVATE/'fit', threads=4)
    selected = summary['selected_epoch']
    key_rows = common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    keys = {r['id']: r for r in key_rows}
    baseline = {r['id']: r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    first = common.rows(PRIVATE/'fit/screen_predictions.jsonl')
    first_ids = {r['id'] for r in first}
    if len(first_ids) != 160 or len(first) != 160:
        raise ValueError('Original fixed160 first predictions changed')
    expected = set(common.read(SOURCE/'data_selection.json')['screen_ids'])
    if first_ids != expected or len(keys) != 1817:
        raise ValueError('Wrong fixed160 or full development cohort')
    remaining = [dict(r, role='screen') for r in key_rows if r['id'] not in first_ids]
    common.putl(PRIVATE/'remaining1657_metadata.jsonl', remaining)
    # Reuse the established frozen-head scorer only for absent IDs.
    previous_argv = sys.argv
    sys.argv = ['score_mlp117.py', '--features', str(SOURCE/'evidence/features500_missing'),
                str(SOURCE/'evidence/features1817_missing'), '--metadata', str(PRIVATE/'remaining1657_metadata.jsonl'),
                '--model', str(PRIVATE/'fit/model.pt'), '--out', str(PRIVATE/'remaining1657')]
    try:
        score_mlp117.main()
    finally:
        sys.argv = previous_argv
    combined = first+common.rows(PRIVATE/'remaining1657/screen_predictions.jsonl')
    current = {r['id']: r for r in combined}
    if len(combined) != 1817 or set(current) != set(keys):
        raise ValueError('The first160 plus missing1657 do not form unique1817')
    if any(not r['valid'] or r['GT'] != keys[r['id']]['GT'] for r in combined):
        raise ValueError('Original GT or prediction validity changed')
    sources = dict(seed118_original_workflow=current,
        seed117_original_workflow={r['id']: r for r in common.rows(ROOT/'outputs/117_verdict_probe/reconsidered_extension_verdict_mlp_predictions.jsonl')},
        seed118_fixed6_diagnostic={r['id']: r for r in common.rows(PUBLIC/'seed_stability_original1024_unweighted_seed118_predictions.jsonl')})
    groups = dict(screen160_natural=[keys[i] for i in expected if keys[i].get('old_panel') == 'natural'],
        screen160_pressure=[keys[i] for i in expected if keys[i].get('old_panel') == 'pressure'],
        natural400=[r for r in key_rows if r.get('old_panel') == 'natural'],
        pressure100=[r for r in key_rows if r.get('old_panel') == 'pressure'],
        new1317=[r for r in key_rows if r.get('subset') == 'new'], selection1817=key_rows)
    result = dict(task=117, followup='original_unweighted_algorithm_second_seed', protocol=protocol,
        seed=118, selected_epoch=selected, completed_epochs=summary['completed_epochs'],
        validation_metrics=summary['validation_metrics'], epoch_selected_with_validation_only=True,
        original_seed117_selected_epoch=6, fixed6_seed118_preserved=True,
        old_results_or_algorithms_modified=False, new_GPU_CNY=0, new_API_CNY=0, models={})
    for name, predictions in sources.items():
        if set(predictions) != set(keys):
            raise ValueError('Reference predictions do not cover original1817: '+name)
        result['models'][name] = {p: section(rows, baseline, predictions) for p, rows in groups.items()}
    common.put(PUBLIC/'unweighted_workflow_seed118.json', result)
    common.putl(PUBLIC/'unweighted_workflow_seed118_predictions.jsonl',
        [dict(current[i], baseline107=baseline[i]['verdict']) for i in sorted(keys)])
    report(result)
    print(common.canonical(dict(selected_epoch=selected, completed_epochs=summary['completed_epochs'],
        panels={p: {k: v[k] for k in ('N', 'delta_MCC', 'delta_correct', 'delta_false_S')}
                for p, v in result['models']['seed118_original_workflow'].items()})))


def report(result):
    lines = ['# 同一seed118的原无权重MLP完整流程复验', '',
        f"原1024训练/730内部验证，完整复用max40、patience8和原MCC/PA/false-S选点规则，seed118选中epoch{result['selected_epoch']}，训练到epoch{result['completed_epochs']}停止。没有根据160/500/1817改epoch。先前seed118固定6轮只是单独诊断，原结果保留；本次才是原训练算法的第二seed复验。", '',
        '|完整1817方案|MCC|PA|正确数|false-S/真实非S|', '|---|---:|---:|---:|---:|']
    ref = result['models']['seed117_original_workflow']['selection1817']['scores']
    for name in ('label_only107', 'paper_r1'):
        v = ref[name]
        lines.append(f"|{name}|{v['mcc']:.4f}|{100*v['percent_agreement']:.2f}%|{v['correct']}|{v['false_S']}/{v['non_S']}|")
    for name, panels in result['models'].items():
        v = panels['selection1817']['scores']['candidate']
        lines.append(f"|{name}|{v['mcc']:.4f}|{100*v['percent_agreement']:.2f}%|{v['correct']}|{v['false_S']}/{v['non_S']}|")
    lines += ['', '按原验证选点算法，两seed均保留高于107的MCC和PA；此前固定6轮的失败不能用来否定原无权重算法的复验表现。风险代价也在两次中持续存在：false-S为92和99，均高于107的50。保留两次结果，不择优只报seed117。', '',
        '固定160的自然/压力、原400/100、新1317与完整1817的类别召回、救回/误伤和false-S变化见同名JSON。不能将固定6轮诊断直接等同于原早停算法的稳定性结论，也不能从两seed宣称普遍稳定。未追加第三seed、β或阈值。', '',
        '全部使用冻结107特征，GPU/API新增0；原模型、回执与报告未覆盖。完整部署仍需原9B prefill。', '']
    (PUBLIC/'unweighted_workflow_seed118.md').write_bytes('\n'.join(lines).encode('utf-8'))


if __name__ == '__main__':
    run()
