"""Complete fixed124 means from cached probabilities; reuse first160 means."""
from __future__ import annotations

from pathlib import Path
from collections import Counter
import argparse
import sys

from pilot124 import ROOT, LABELS, SOURCES, selected_rows, vector, mean_decision, compare, metrics, common

OUTPUT = ROOT/'outputs/124_seed_mean_readout'


def paired(rows, baseline, candidate):
    result = compare(rows, baseline, candidate)
    patients = []
    for sid in sorted({str(r['sid']) for r in rows}):
        group = [r for r in rows if str(r['sid']) == sid]
        patients.append(dict(sid=sid, N=len(group),
            correct_delta=sum(int(candidate[r['id']]['verdict'] == r['GT'])-
                              int(baseline[r['id']]['verdict'] == r['GT']) for r in group),
            false_S_delta=sum(int(r['GT'] != 'Supported' and candidate[r['id']]['verdict'] == 'Supported')-
                              int(r['GT'] != 'Supported' and baseline[r['id']]['verdict'] == 'Supported') for r in group)))
    result['patients'] = patients
    result['patient_direction'] = {name: dict(up=sum(r[name] > 0 for r in patients),
        down=sum(r[name] < 0 for r in patients), equal=sum(r[name] == 0 for r in patients))
        for name in ('correct_delta', 'false_S_delta')}
    return result


def run():
    if (OUTPUT/'full1817.json').exists():
        raise FileExistsError('Preserve the first fixed-family extension')
    pilot = common.read(OUTPUT/'pilot160.json')
    if (pilot['weights'], pilot['label_order'], set(pilot['families'])) != ([.5, .5], list(LABELS), set(SOURCES)):
        raise ValueError('The original124 fixed rule differs')
    ids160 = common.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids']
    old_ids = set(ids160)
    rows = common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    keys = {r['id']: r for r in rows}
    if len(keys) != len(rows) or len(keys) != 1817 or len(old_ids) != 160 or not old_ids <= set(keys):
        raise ValueError('Wrong original1817 and nested160 metadata')
    wanted = set(keys); new_ids = wanted-old_ids
    models = {
        'label_only107': selected_rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl', wanted),
        'step220': selected_rows(ROOT/'outputs/120_full_pool_sft/midpoint220_1817_predictions_sanitized.jsonl', wanted)}
    means = {}
    for family, paths in SOURCES.items():
        seeds = {name: selected_rows(ROOT/path, wanted) for name, path in paths.items()}
        for name, predictions in seeds.items():
            models[family+'_'+name] = predictions
        first = pilot['families'][family]['predictions_GT_free']
        current = {r['id']: dict(r) for r in first}
        if len(first) != 160 or set(current) != old_ids:
            raise ValueError('Original mean160 first predictions are incomplete')
        for i in sorted(new_ids):
            label, probability = mean_decision(vector(seeds['seed117'][i]), vector(seeds['seed118'][i]))
            current[i] = dict(id=i, verdict=label, probabilities=probability, valid=True,
                              probabilities_calibrated=False)
        if any(current[r['id']] != r for r in first):
            raise AssertionError('Original160 mean changed')
        models[family+'_mean'] = current
        means[family] = current
    models['paper_r1'] = {i: dict(id=i, verdict=keys[i]['paper_r1'], valid=True) for i in wanted}
    for name, predictions in models.items():
        if set(predictions) != wanted or any(r.get('valid') is not True or r['verdict'] not in LABELS for r in predictions.values()):
            raise ValueError('Incomplete or invalid model reference: '+name)
        if any('GT' in r and r['GT'] != keys[r['id']]['GT'] for r in predictions.values()):
            raise ValueError('GT association differs: '+name)
    cohorts = dict(natural400=[r for r in rows if r.get('old_panel') == 'natural'],
                   pressure100=[r for r in rows if r.get('old_panel') == 'pressure'],
                   new1317=[r for r in rows if r.get('subset') == 'new'], selection1817=rows)
    result = dict(task=124, name='seed_mean_readout', fixed_weights=[.5, .5],
        source_pilot='pilot160.json', original160_mean_predictions_reused=True,
        newly_combined_IDs_per_family=1657, no_new_model_predictions=True,
        no_weight_or_seed_selection=True, no_cross_family_fusion=True,
        labels=list(LABELS), exact_tie='Supported, Not Supported, Not Addressed order',
        new_GPU_CNY=0, new_API_CNY=0, confirmation40_used=False,
        deployment='One shared107 full input prefill per family, then two CPU heads; not two9B passes',
        panels={})
    for scope, group in cohorts.items():
        scores = {name: metrics(group, {r['id']: predictions[r['id']]['verdict'] for r in group})
                  for name, predictions in models.items()}
        comparisons = {family: {reference: paired(group, models[reference], means[family])
                       for reference in ('label_only107', 'step220', family+'_seed117', family+'_seed118')}
                       for family in SOURCES}
        result['panels'][scope] = dict(N=len(group), GT=dict(Counter(r['GT'] for r in group)),
                                      scores=scores, mean_vs=comparisons)
    common.put(OUTPUT/'full1817.json', result)
    sanitized = [dict(id=i, sid=str(keys[i]['sid']), GT=keys[i]['GT'], author=keys[i]['author'],
        old_panel=keys[i].get('old_panel'), subset=keys[i].get('subset'),
        prediction={name: predictions[i]['verdict'] for name, predictions in models.items()},
        mean_probabilities={family: means[family][i]['probabilities'] for family in SOURCES},
        mean_origin='pilot160' if i in old_ids else 'new1657_CPU') for i in sorted(keys)]
    common.putl(OUTPUT/'predictions_sanitized.jsonl', sanitized)
    report(result)
    print(common.canonical({scope: {family: dict(
        metrics={k: values['scores'][family+'_mean'][k] for k in ('mcc', 'percent_agreement', 'correct', 'false_S', 'non_S')},
        vs={name: {k: value[k] for k in ('delta_MCC', 'delta_correct', 'delta_false_S')}
            for name, value in values['mean_vs'][family].items()}) for family in SOURCES}
        for scope, values in result['panels'].items()}))


def report(result):
    lines = ['# 124固定两seed概率均值：完整1817', '',
        '两个家族各自等权平均，不混家族、不选seed或调权重。原160条均值预测直接复用，仅补其余1657条CPU组合；未运行模型或新增GPU/API。原20名选型患者均有历史暴露，本结果是开发证据。', '',
        '|完整1817方案|MCC|PA|正确数|false-S/真实非S|S/NS/NA召回|',
        '|---|---:|---:|---:|---:|---|']
    full = result['panels']['selection1817']
    for name, value in full['scores'].items():
        recalls = '/'.join('—' if value['per_class'][g]['recall'] is None else f"{100*value['per_class'][g]['recall']:.2f}%" for g in LABELS)
        lines.append(f"|{name}|{value['mcc']:.4f}|{100*value['percent_agreement']:.2f}%|{value['correct']}|{value['false_S']}/{value['non_S']}|{recalls}|")
    lines += ['', '|范围／均值家族|MCC|PA|正确数|false-S/真实非S|', '|---|---:|---:|---:|---:|']
    for scope in ('natural400', 'pressure100', 'new1317'):
        for family in SOURCES:
            v = result['panels'][scope]['scores'][family+'_mean']
            lines.append(f"|{scope}/{family}|{v['mcc']:.4f}|{100*v['percent_agreement']:.2f}%|{v['correct']}|{v['false_S']}/{v['non_S']}|")
    lines += ['', '均值相对每个单seed及107、120的完整配对类别救回/误伤与患者方向见[结果JSON](full1817.json)。以下均为完整1817上的实际变化，不用单项指标掩盖代价：', '']
    for family in SOURCES:
        for reference, p in full['mean_vs'][family].items():
            d = p['patient_direction']
            lines.append(f"- {family}相对{reference}：ΔMCC {p['delta_MCC']:+.4f}、Δ正确{p['delta_correct']:+d}、Δfalse-S{p['delta_false_S']:+d}；正确患者↑/↓ {d['correct_delta']['up']}/{d['correct_delta']['down']}，false-S患者↑/↓ {d['false_S_delta']['up']}/{d['false_S_delta']['down']}。")
    lines += ['', '**判断：平方根权重家族均值提供值得保留的新增质量—风险取舍。** 相对两个单seed都提高总体MCC和正确数；相对seed117增加5次false-S，相对seed118减少13次。它与120的总体MCC接近（仅高0.0009，不能包装成强胜），少39条正确但少52次false-S。原压力100上MCC略低于107，不能只展示总体和自然集。', '',
        '相对107，平方根均值的S/NS/NA净正确变化为+79/−9/+5；NS损失仍需保留。', '',
        '无权重家族均值比seed118改善，但相对seed117少2条正确、多1次false-S、MCC略低，当前没有明确的新质量收益。两家族结果均保留，不混合或再选权重。paper_r1仅为作者历史参照。', '',
        '所有平均概率来自真实三分类头的softmax，未作校准。部署每个家族只需一次冻结107完整prefill，再算两个CPU微头；不是两次9B调用。未自动升级系统、增加权重搜索或再次训练。', '']
    if 'retained_sqrt_evidence' in result:
        lines += ['## 固定平方根均值的患者配对区间', '',
            '|范围／参照|ΔMCC及95%CI|ΔPA百分点及95%CI|Δfalse-S率百分点及95%CI|', '|---|---|---|---|']
        for scope, comparisons in result['retained_sqrt_evidence'].items():
            for reference, value in comparisons.items():
                m = value['paired_bootstrap']['metrics']
                risk = value['risk_recall_bootstrap']['false_S_rate']
                fmt = lambda v, scale: f"{scale*v['delta']:+.4f} [{scale*v['ci95'][0]:+.4f}, {scale*v['ci95'][1]:+.4f}]"
                lines.append(f"|{scope}/{reference}|{fmt(m['mcc'],1)}|{fmt(m['percent_agreement'],100)}|{fmt(risk,100)}|")
        lines += ['', '1000次配对患者cluster bootstrap仅描述固定模型在当前患者内的抽样不确定性，不覆盖历史开发选择、训练随机性或外部泛化；CI不是全赢门槛。与120的差异应主要按少52次错误放行、少39条正确理解，不能把极小MCC差值包装为强优势。', '']
    (OUTPUT/'final_report.md').write_bytes('\n'.join(lines).encode('utf-8'))


def finalize_evidence():
    sys.path.insert(0, str(ROOT/'tasks/118_full_data_heads'))
    from readout_evidence118 import paired_compare, risk_deltas
    data = common.read(OUTPUT/'full1817.json')
    if 'retained_sqrt_evidence' in data:
        raise FileExistsError('Preserve completed fixed-model bootstrap evidence')
    rows = common.rows(OUTPUT/'predictions_sanitized.jsonl')
    if len(rows) != len({r['id'] for r in rows}) or len(rows) != 1817:
        raise ValueError('Complete unique1817 predictions are required')
    evidence = {}
    for scope in ('selection1817', 'new1317'):
        part = rows if scope == 'selection1817' else [r for r in rows if r.get('subset') == 'new']
        evidence[scope] = {}
        for reference in ('label_only107', 'step220'):
            cohort = [dict(proposition_id=r['id'], subject_id=str(r['sid']), human_gt=r['GT']) for r in part]
            old = [dict(proposition_id=r['id'], verdict=r['prediction'][reference]) for r in part]
            new = [dict(proposition_id=r['id'], verdict=r['prediction']['sqrt_weight_full_mean']) for r in part]
            paired = [dict(r, pred={'source': r['prediction'][reference],
                                   'mean': r['prediction']['sqrt_weight_full_mean']}) for r in part]
            evidence[scope][reference] = dict(
                paired_bootstrap=paired_compare(cohort, old, new, iterations=1000),
                risk_recall_bootstrap=risk_deltas(paired, 'source', 'mean'))
    source = common.read(ROOT/'.local_models/117_verdict_probe/features_initial.json')
    heads = [ROOT/'.local_models/118_full_data_heads/reconsidered_refit/sqrt_weight_full/model.pt',
             ROOT/'.local_models/118_full_data_heads/seed_stability/full3675_sqrt/model.pt']
    deployment = dict(candidate='sqrt_weight_full_mean', status='saved_candidate_not_default_upgrade',
        backbone_model_dir=source['model_dir'], frozen107_remote_adapter=source['adapter_path'],
        frozen107_adapter_sha256=source['adapter_sha256'],
        frozen107_local_adapter=str(ROOT/'.local_models/109_boundary_replay/source107/checkpoint_a'),
        prompt_code='tasks/104_supervision_evidence/training104.py:prompt_ids',
        public_prefix='{"verdict":"', public_prefix_token_ids=[4754, 415, 8217, 3147],
        feature='last hidden state after the shared public prefix; full original claim/reference; no answer label',
        backbone_prefills_per_input=1,
        heads=[dict(seed=seed, model_path=str(path), sha256=common.sha(path),
                    scaler='exact buffers stored inside this model.pt') for seed, path in zip((117, 118), heads)],
        rule='softmax each frozen head logits separately; arithmetic mean(.5,.5); argmax in fixed class order',
        labels=list(LABELS), probability_weights=[.5, .5], exact_tie='first label in fixed order',
        output='original label in verdict JSON', calibrated=False, weights_averaged=False,
        no_refit=True, no_threshold=True)
    common.put(ROOT/'.local_models/124_seed_mean_readout/deployment_sqrt_mean.json', deployment)
    data['retained_sqrt_evidence'] = evidence
    data['deployment_manifest'] = '.local_models/124_seed_mean_readout/deployment_sqrt_mean.json'
    common.put(OUTPUT/'full1817.json', data)
    report(data)
    print(common.canonical({scope: {reference: evidence[scope][reference]['paired_bootstrap']['metrics']['mcc']
                                   for reference in evidence[scope]} for scope in evidence}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--finalize-evidence', action='store_true')
    args = parser.parse_args()
    finalize_evidence() if args.finalize_evidence else run()
