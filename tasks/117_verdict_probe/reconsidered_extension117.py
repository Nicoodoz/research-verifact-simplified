"""Analyze new cached-feature117 follow-up without altering original decisions.

New1317 predictions are made by the existing score_frozen117/score_mlp117
commands and merged with untouched old500 first predictions. No fitting here.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT/'.local_models/117_verdict_probe'
PUBLIC = ROOT/'outputs/117_verdict_probe'
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import section


def main():
    output = PUBLIC/'reconsidered_extension.json'
    if output.exists():
        raise FileExistsError('Preserve this follow-up result; do not silently overwrite it')
    key_rows = common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    keys = {r['id']: r for r in key_rows}
    baseline = {r['id']: r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    old = {i for i in keys if keys[i].get('old_panel') in ('natural', 'pressure')}
    new = set(keys)-old
    if len(keys) != len(key_rows) or (len(keys), len(old), len(new)) != (1817, 500, 1317):
        raise ValueError('Original complete1817 or old500 membership differs')
    if set(baseline) != set(keys) or any(r.get('valid') is not True for r in baseline.values()):
        raise ValueError('Require complete valid cached107 reference')
    sources = {
        'verdict_mlp': dict(old=PUBLIC/'mlp_500_verdict_mlp_predictions.jsonl',
            new=PRIVATE/'reconsidered_extension/mlp_new1317/screen_predictions.jsonl',
            model=PRIVATE/'mlp_initial/model.pt', choice=dict(selected_epoch=6, class_weight=None,
            representation='verdict_prefix', training_N=1024, training_patients=32)),
        'regularized_probe': dict(old=PUBLIC/'regularized_probe_500_verdict_prefix_predictions.jsonl',
            new=PRIVATE/'reconsidered_extension/linear_new1317/verdict_prefix_screen_predictions.jsonl',
            model=PRIVATE/'fit_regularization_selected/verdict_prefix_head.npz',
            choice=dict(C=.0001, class_weight=None, representation='verdict_prefix',
                        training_N=1024, training_patients=32))}
    cohorts = dict(natural400=sorted(i for i in old if keys[i]['old_panel'] == 'natural'),
                   pressure100=sorted(i for i in old if keys[i]['old_panel'] == 'pressure'),
                   new1317=sorted(new), selection1817=sorted(keys))
    result = dict(task=117, reason='User authorized reconsideration of previously strict false-S stop decisions',
        old117_results_and_stop_decisions_unchanged=True, old500_reinference=False,
        new_predictions_per_model=1317, models={}, new_GPU_CNY=0, new_API_CNY=0,
        confirmation40_used=False, cohort_role='Historically exposed development-selection20 patients',
        refit=False, new_model_selection=False, probabilities_calibrated=False,
        deployment_note='Both heads require frozen107 full prefill; cached CPU head throughput is not end-to-end throughput')
    for name, source in sources.items():
        old_rows, new_rows = common.rows(source['old']), common.rows(source['new'])
        if len(old_rows) != 500 or {r['id'] for r in old_rows} != old:
            raise ValueError('Old500 first-prediction coverage differs: '+name)
        if len(new_rows) != 1317 or {r['id'] for r in new_rows} != new:
            raise ValueError('New1317 coverage differs: '+name)
        combined = old_rows+new_rows
        predicted = {r['id']: r for r in combined}
        if len(predicted) != 1817 or any(r.get('valid') is not True or r['GT'] != keys[r['id']]['GT']
                or str(r['sid']) != str(keys[r['id']]['sid']) for r in combined):
            raise ValueError('Prediction label/ID/patient association differs: '+name)
        panels = {panel: section([keys[i] for i in ids], baseline, predicted) for panel, ids in cohorts.items()}
        author = {panel: {source_name: section([keys[i] for i in ids if keys[i]['author'] == source_name], baseline, predicted)
                          for source_name in sorted({keys[i]['author'] for i in ids})}
                  for panel, ids in cohorts.items()}
        result['models'][name] = dict(choice=source['choice'], model_sha256=common.sha(source['model']),
            N=1817, missing_N=0, invalid_N=0, panels=panels, by_author=author,
            old500_source_sha256=common.sha(source['old']))
        sanitized = [dict(id=i, sid=str(keys[i]['sid']), GT=keys[i]['GT'], author=keys[i]['author'],
                         old_panel=keys[i].get('old_panel'), subset=keys[i].get('subset'),
                         verdict=predicted[i]['verdict'], valid=True, baseline107=baseline[i]['verdict'],
                         probabilities=predicted[i].get('probabilities'), probabilities_calibrated=False,
                         receipt_origin='original500' if i in old else 'new1317_CPU') for i in sorted(keys)]
        common.putl(PUBLIC/('reconsidered_extension_'+name+'_predictions.jsonl'), sanitized)
    common.put(output, result)
    report(result)
    print(common.canonical({name: {panel: {k: v[k] for k in ('N', 'delta_MCC', 'delta_correct', 'delta_false_S')}
                                   for panel, v in model['panels'].items()} for name, model in result['models'].items()}))


def report(result):
    lines = ['# 117固定头的开发队列补充评价', '',
        '按用户本次放宽风险取舍的授权，补评原MLP与regularized_probe；不是新训练或重新选参。MLP固定第6个epoch，线性头固定C=0.0001，均不加类别权重。旧500条首回执原样复用，每个模型只新增1317条CPU缓存特征预测。原117停止记录保持原样。', '',
        '|范围|方案|MCC|PA|正确数|false-S/真实非S|S/NS/NA净救回|',
        '|---|---|---:|---:|---:|---:|---:|']
    for panel in ('natural400', 'pressure100', 'new1317', 'selection1817'):
        reference = result['models']['verdict_mlp']['panels'][panel]
        for name in ('label_only107', 'paper_r1', 'verdict_mlp', 'regularized_probe'):
            if name in ('label_only107', 'paper_r1'):
                value = reference['scores'][name]
                net = '—'
            else:
                current = result['models'][name]['panels'][panel]
                value = current['scores']['candidate']
                net = '/'.join(str(current['changes']['by_class'][g]['rescued']-
                                   current['changes']['by_class'][g]['harmed'])
                               for g in ('Supported', 'Not Supported', 'Not Addressed'))
            lines.append(f"|{panel}|{name}|{value['mcc']:.4f}|{100*value['percent_agreement']:.2f}%|{value['correct']}|{value['false_S']}/{value['non_S']}|{net}|")
    lines += ['', '完整1817下相对107的实际取舍：', '']
    for name, model in result['models'].items():
        value = model['panels']['selection1817']
        change = value['changes']
        lines.append(f"- {name}：ΔMCC {value['delta_MCC']:+.4f}，Δ正确{value['delta_correct']:+d}，"
                     f"false-S净{value['delta_false_S']:+d}（新增{change['false_S_new']}、避免{change['false_S_avoided']}）。")
    lines += ['', '扩大后总体MCC和PA收益仍在，主要来自救回正确S；NS与NA的识别损失也真实存在。MLP比线性头少判对2条，但MCC更高、少19次false-S，提供相对更好的总体质量—风险取舍；两者都不能称为风险降低。应保留这份实际增益供取舍，不因false-S增加直接把总体收益写成无效，也不据此自动升级默认系统。', '',
        '这些是原20名开发/选型患者的扩展证据，所有患者已有历史暴露；不称独立测试。完整混淆矩阵、各类救回/误伤、来源及患者方向见同名JSON。作者paper_r1仅历史参照。', '',
        '没有改变模型、训练数据或输出阈值；本次GPU/API新增均为0。完整部署仍需107做全输入prefill，缓存头CPU预测时间不能充当端到端速度。', '']
    (PUBLIC/'reconsidered_extension.md').write_bytes('\n'.join(lines).encode('utf-8'))


if __name__ == '__main__':
    main()
