"""Conditional-on-fixed-model patient-bootstrap evidence for five saved heads."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT/'outputs/118_full_data_heads'
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import section
sys.path.insert(0, str(ROOT/'tasks/107_support_aux'))
from evaluate107 import risk_deltas
sys.path.insert(0, str(ROOT/'src'))
from verifact_research.evaluation import paired_compare

FILES = {
    'unweighted1024_seed117': ROOT/'outputs/117_verdict_probe/reconsidered_extension_verdict_mlp_predictions.jsonl',
    'unweighted1024_seed118': OUTPUT/'unweighted_workflow_seed118_predictions.jsonl',
    'sqrt3675_seed117': OUTPUT/'reconsidered_refit_sqrt_weight_full_predictions.jsonl',
    'sqrt3675_seed118': OUTPUT/'seed_stability_full3675_sqrt_seed118_predictions.jsonl',
    'sqrt1024_seed117': ROOT/'outputs/117_verdict_probe/sqrt_weight_mlp_predictions.jsonl',
}


def compact_score(score):
    return {k: score[k] for k in ('mcc', 'percent_agreement', 'correct', 'false_S', 'non_S', 'macro_F1')} | {
        'recall': {label: values['recall'] for label, values in score['per_class'].items()}}


def point(rows, base, predicted):
    value = section(rows, base, predicted)
    patients = value['patient_directions']
    return dict(N=len(rows), score=compact_score(value['scores']['candidate']),
        delta={k: value['delta_'+k] for k in ('MCC', 'PA', 'correct', 'false_S')},
        class_changes=value['changes'], patient_directions=patients,
        patient_summary={key: dict(up=sum(r[key] > 0 for r in patients), down=sum(r[key] < 0 for r in patients),
                                  equal=sum(r[key] == 0 for r in patients))
                         for key in ('correct_delta', 'false_S_delta')})


def main():
    keys_list = common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    keys = {r['id']: r for r in keys_list}
    base_rows = common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    base = {r['id']: r for r in base_rows}
    if len(keys_list) != len(keys) or len(keys) != 1817 or set(base) != set(keys):
        raise ValueError('Original complete1817 cohort differs')
    groups = dict(selection1817=keys_list, new1317=[r for r in keys_list if r.get('subset') == 'new'])
    if len(groups['new1317']) != 1317:
        raise ValueError('Original new1317 membership differs')
    result = dict(iterations=1000, resampling='paired patients; seeds0..999; fixed fitted model',
        comparison='candidate minus saved107', new_GPU_CNY=0, new_API_CNY=0,
        no_new_training=True, no_prediction_regeneration=True, confirmation40_used=False,
        limits='CI does not cover training randomness, historical model/development selection, ancestor exposure, or external generalization; not an all-win gate.',
        models={})
    for name, path in FILES.items():
        raw = common.rows(path); pred = {r['id']: r for r in raw}
        if len(raw) != len(pred) or set(pred) != set(keys):
            raise ValueError('Incomplete/nonunique prediction IDs: '+name)
        for r in raw:
            if r.get('valid') is not True or r['GT'] != keys[r['id']]['GT'] or str(r['sid']) != str(keys[r['id']]['sid']):
                raise ValueError('Prediction GT/patient association differs: '+name)
        model = dict(source_prediction=str(path.relative_to(ROOT)).replace('\\', '/'), panels={})
        for group, rows in groups.items():
            item = point(rows, base, pred)
            item['author'] = {author: point([r for r in rows if r['author'] == author], base, pred)
                              for author in sorted({r['author'] for r in rows})}
            truth = [dict(proposition_id=r['id'], subject_id=str(r['sid']), human_gt=r['GT']) for r in rows]
            old = [dict(proposition_id=r['id'], verdict=base[r['id']]['verdict']) for r in rows]
            new = [dict(proposition_id=r['id'], verdict=pred[r['id']]['verdict']) for r in rows]
            item['paired_bootstrap'] = paired_compare(truth, old, new, iterations=1000)
            paired = [dict(r, pred={'baseline107': base[r['id']]['verdict'], 'head': pred[r['id']]['verdict']}) for r in rows]
            item['risk_recall_bootstrap'] = risk_deltas(paired, 'baseline107', 'head')
            model['panels'][group] = item
        result['models'][name] = model
        print(common.canonical(dict(completed=name)), flush=True)
    common.put(OUTPUT/'readout_evidence_summary.json', result)
    report(result)
    print(common.canonical({name: {p: dict(MCC=v['score']['mcc'], delta_MCC=v['delta']['MCC'],
        MCC_CI=v['paired_bootstrap']['metrics']['mcc']['ci95'], false_S=v['score']['false_S'])
        for p, v in model['panels'].items()} for name, model in result['models'].items()}))


def report(result):
    lines = ['# 固定读出头的患者配对证据汇总', '',
        '只读取5份固定模型的已完成预测，不训练、不重推。对完整1817及新增1317分别做1000次患者配对bootstrap，候选减107。无权重seed118采用原完整验证选轮流程，不是固定6轮诊断。', '',
        '|范围／候选|ΔMCC及95%CI|ΔPA百分点及95%CI|Δ正确|false-S/非S|Δfalse-S率百分点及95%CI|',
        '|---|---|---|---:|---:|---|']
    for group in ('selection1817', 'new1317'):
        for name, model in result['models'].items():
            p = model['panels'][group]; b = p['paired_bootstrap']['metrics']; risk = p['risk_recall_bootstrap']['false_S_rate']
            fmt = lambda v, scale: f"{scale*v['delta']:+.4f} [{scale*v['ci95'][0]:+.4f}, {scale*v['ci95'][1]:+.4f}]"
            lines.append(f"|{group}/{name}|{fmt(b['mcc'],1)}|{fmt(b['percent_agreement'],100)}|{p['delta']['correct']:+d}|{p['score']['false_S']}/{p['score']['non_S']}|{fmt(risk,100)}|")
    lines += ['', '|范围／候选|human ΔMCC/Δ正确/Δfalse-S|LLM ΔMCC/Δ正确/Δfalse-S|', '|---|---|---|']
    for group in ('selection1817', 'new1317'):
        for name, model in result['models'].items():
            authors = model['panels'][group]['author']
            cells = []
            for author in ('human', 'llm'):
                d = authors[author]['delta']
                cells.append(f"{d['MCC']:+.4f}/{d['correct']:+d}/{d['false_S']:+d}")
            lines.append(f'|{group}/{name}|'+ '|'.join(cells)+'|')
    lines += ['', '|完整1817候选|正确患者↑/↓/同|false-S患者↑/↓/同|', '|---|---:|---:|']
    for name, model in result['models'].items():
        p = model['panels']['selection1817']['patient_summary']
        show = lambda v: f"{v['up']}/{v['down']}/{v['equal']}"
        lines.append(f"|{name}|{show(p['correct_delta'])}|{show(p['false_S_delta'])}|")
    lines += ['', '患者逐项方向、三类召回及其差值区间、类别救回/误伤均保留在[汇总JSON](readout_evidence_summary.json)。区间仅描述这组患者内、给定已拟合模型的抽样不确定性，不覆盖训练随机性、历史开发选择、107祖先暴露或外部泛化；跨0不等于无效，区间也不代替实际收益和风险取舍。', '',
        '全部样本仍属于已暴露的20名开发/选型患者。未使用确认40人，GPU/API新增0；缓存头部统计不代表完整系统部署速度。', '']
    (OUTPUT/'readout_evidence_summary.md').write_bytes('\n'.join(lines).encode('utf-8'))


if __name__ == '__main__':
    main()
