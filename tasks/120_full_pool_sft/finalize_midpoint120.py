"""Offline final analysis of the actual220-step120 model; no model calls."""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'outputs/120_full_pool_sft'
sys.path.insert(0, str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import section, metrics
sys.path.insert(0, str(ROOT/'tasks/107_support_aux'))
from evaluate107 import risk_deltas
sys.path.insert(0, str(ROOT/'src'))
from verifact_research.evaluation import paired_compare

LABELS = ('Supported', 'Not Supported', 'Not Addressed')


def direction(part):
    return {field: dict(up=sum(r[field] > 0 for r in part), down=sum(r[field] < 0 for r in part),
                        equal=sum(r[field] == 0 for r in part))
            for field in ('correct_delta', 'false_S_delta')}


def main():
    source = common.read(OUT/'midpoint220_1817.json')
    current_rows = common.rows(OUT/'midpoint220_1817_predictions_sanitized.jsonl')
    current = {r['id']: r for r in current_rows}
    key_rows = common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    keys = {r['id']: r for r in key_rows}
    base = {r['id']: r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    expected_sha = common.read(ROOT/'.local_models/120_full_pool_sft/midpoint220_job.json')['adapter_sha256']
    if len(current_rows) != len(current) or len(current) != 1817 or set(current) != set(keys):
        raise ValueError('Complete unique1817 predictions are required')
    for r in current_rows:
        key = keys[r['id']]
        if (r.get('valid') is not True or r['verdict'] not in LABELS or r['GT'] != key['GT']
                or str(r['sid']) != str(key['sid']) or r['source_adapter_sha256'] != expected_sha
                or r['source_prompt_sha256_104'] != base[r['id']]['prompt_token_sha256']):
            raise ValueError('Original120 prediction identity/GT/prompt differs')
    for n in (160, 500):
        old = common.rows(OUT/f'midpoint220_{n}_predictions_sanitized.jsonl')
        if len(old) != n or any(r['verdict'] != current[r['id']]['verdict'] for r in old):
            raise ValueError('Old first receipts changed during coverage extension')
    screen = set(common.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids'])
    groups = dict(selection1817=key_rows, new1317=[r for r in key_rows if r.get('subset') == 'new'],
                  natural400=[r for r in key_rows if r.get('old_panel') == 'natural'],
                  pressure100=[r for r in key_rows if r.get('old_panel') == 'pressure'])
    historical = {f'screen160_{p}': [r for r in key_rows if r['id'] in screen and r.get('old_panel') == p]
                  for p in ('natural', 'pressure')}
    analyzed = {}
    for name, rows in {**groups, **historical}.items():
        result = section(rows, base, current)
        result['author'] = {a: section([r for r in rows if r['author'] == a], base, current)
                            for a in sorted({r['author'] for r in rows})}
        result['patient_summary'] = direction(result['patient_directions'])
        result['NA_correct_to_S'] = sum(r['GT'] == 'Not Addressed' and base[r['id']]['verdict'] == r['GT']
                                        and current[r['id']]['verdict'] == 'Supported' for r in rows)
        result['NA_correct_to_NS'] = sum(r['GT'] == 'Not Addressed' and base[r['id']]['verdict'] == r['GT']
                                         and current[r['id']]['verdict'] == 'Not Supported' for r in rows)
        if name in groups:
            truth = [dict(proposition_id=r['id'], subject_id=str(r['sid']), human_gt=r['GT']) for r in rows]
            old = [dict(proposition_id=r['id'], verdict=base[r['id']]['verdict']) for r in rows]
            new = [dict(proposition_id=r['id'], verdict=current[r['id']]['verdict']) for r in rows]
            result['paired_patient_bootstrap'] = paired_compare(truth, old, new, iterations=1000)
            paired = [dict(r, pred={'baseline107': base[r['id']]['verdict'], 'step220': current[r['id']]['verdict']}) for r in rows]
            result['risk_recall_bootstrap'] = risk_deltas(paired, 'baseline107', 'step220')
        analyzed[name] = result
    # A numerical identity check, not a rewrite of the original analysis.
    for name, original_name in [('selection1817', 'selection1817'), ('new1317', 'new1317'),
                                ('natural400', 'natural'), ('pressure100', 'pressure')]:
        old = source['models']['full_pool_sft']['panels'][original_name]
        if any(abs(analyzed[name][metric]-old[metric]) > 1e-12
               for metric in ('delta_MCC', 'delta_PA', 'delta_correct', 'delta_false_S')):
            raise ValueError('Reused project metrics differ from original numerical record')
    files = {
        '120_step220': OUT/'midpoint220_1817_predictions_sanitized.jsonl',
        'MLP1024_unweighted_seed117': ROOT/'outputs/117_verdict_probe/reconsidered_extension_verdict_mlp_predictions.jsonl',
        'MLP1024_unweighted_seed118': ROOT/'outputs/118_full_data_heads/unweighted_workflow_seed118_predictions.jsonl',
        'MLP1024_sqrt': ROOT/'outputs/117_verdict_probe/sqrt_weight_mlp_predictions.jsonl',
        'MLP3675_sqrt_seed117': ROOT/'outputs/118_full_data_heads/reconsidered_refit_sqrt_weight_full_predictions.jsonl',
        'MLP3675_sqrt_seed118': ROOT/'outputs/118_full_data_heads/seed_stability_full3675_sqrt_seed118_predictions.jsonl'}
    comparison = {name: {} for name in groups}
    for label, path in files.items():
        records = common.rows(path); lookup = {r['id']: r for r in records}
        if (len(records) != 1817 or set(lookup) != set(keys)
                or any(r.get('valid') is not True or r['GT'] != keys[r['id']]['GT'] for r in records)):
            raise ValueError('MLP comparison lacks the same valid1817 IDs: '+label)
        for name, rows in groups.items():
            comparison[name][label] = metrics(rows, {r['id']: lookup[r['id']]['verdict'] for r in rows})
    final = dict(task=120, checkpoint_step=220, presentations=1760, planned_steps369_completed=False,
        source_adapter_sha256=expected_sha, coverage=source['models']['full_pool_sft']['coverage'],
        panels=analyzed, same_ID_MLP_comparison=comparison, new_GPU=False, new_API=False,
        CI_role='descriptive patient resampling; not an acceptance gate or an independent-test guarantee',
        confirmation40_used=False, bootstrap_iterations=1000)
    common.put(OUT/'midpoint220_followup_analysis.json', final)
    report(final)
    update_decision(final)
    print(common.canonical({name: dict(MCC=v['scores']['candidate']['mcc'], PA=v['scores']['candidate']['percent_agreement'],
          correct=v['scores']['candidate']['correct'], false_S=v['scores']['candidate']['false_S'],
          MCC_CI=v['paired_patient_bootstrap']['metrics']['mcc']['ci95']) for name, v in analyzed.items() if name in groups}))


def numbers(m):
    pa = (Decimal(str(m['percent_agreement']))*100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    return f"{m['mcc']:.4f}|{pa}%|{m['correct']}|{m['false_S']}/{m['non_S']}"


def recall(m):
    return '/'.join('—' if m['per_class'][g]['recall'] is None else f"{100*m['per_class'][g]['recall']:.2f}%" for g in LABELS)


def report(data):
    ps = data['panels']; full = ps['selection1817']; new = ps['new1317']
    lines = ['# 120：固定220步的1817条开发评价', '',
        '**结论：存在实质MCC与PA收益，应保留为质量—风险取舍候选；false-S和NA代价大，不自动升级默认系统。** 训练实际停在220步、1760次呈现，未完成原定369步。没有重启训练或搜索其他检查点。', '',
        '原160首回执、后补340及其余1317已合并为唯一完整1817条，全部有效、无缺失，旧结果未改。以下是原20名历史暴露的开发/选型患者，不是新增独立确认；未用确认40人。', '',
        '## 完整队列与新增覆盖', '',
        '|范围／方案|MCC|PA|正确数|false-S/真实非S|S/NS/NA召回|',
        '|---|---:|---:|---:|---:|---|']
    for panel in ('selection1817', 'new1317'):
        for model, label in [('label_only107', '107'), ('candidate', '120 step220'), ('paper_r1', 'paper_r1历史')]:
            m = ps[panel]['scores'][model]
            lines.append(f'|{panel}／{label}|{numbers(m)}|{recall(m)}|')
    lines += ['', f"完整1817：ΔMCC {full['delta_MCC']:+.4f}、正确{full['delta_correct']:+d}、false-S{full['delta_false_S']:+d}；新增1317自身也保留ΔMCC {new['delta_MCC']:+.4f}、正确{new['delta_correct']:+d}，收益不是仅由原160推动。", '',
        '|范围|S救回/误伤|NS救回/误伤|NA救回/误伤|false-S新增/避免|正确NA转S/转NS|',
        '|---|---:|---:|---:|---:|---:|']
    for name in ('selection1817', 'new1317'):
        p = ps[name]; change = p['changes']
        counts = '|'.join(f"{change['by_class'][g]['rescued']}/{change['by_class'][g]['harmed']}" for g in LABELS)
        lines.append(f"|{name}|{counts}|{change['false_S_new']}/{change['false_S_avoided']}|{p['NA_correct_to_S']}/{p['NA_correct_to_NS']}|")
    lines += ['', '主要增益来自救回正确S；同时存在NS改善与误伤，并显著损失NA。降低误报与新增错误放行是不同方向，不能用总正确数增加掩盖后者。', '',
        '## 来源、患者与不确定性', '',
        '|范围／来源|N|ΔMCC|Δ正确|Δfalse-S|', '|---|---:|---:|---:|---:|']
    for name in ('selection1817', 'new1317'):
        for author, a in ps[name]['author'].items():
            lines.append(f"|{name}/{author}|{a['N']}|{a['delta_MCC']:+.4f}|{a['delta_correct']:+d}|{a['delta_false_S']:+d}|")
    for name in ('selection1817', 'new1317'):
        d = ps[name]['patient_summary']
        lines += ['', f"{name}患者方向：正确数增加/减少/不变 {d['correct_delta']['up']}/{d['correct_delta']['down']}/{d['correct_delta']['equal']}；false-S增加/减少/不变 {d['false_S_delta']['up']}/{d['false_S_delta']['down']}/{d['false_S_delta']['equal']}。", '']
    lines += ['新增1317的LLM来源虽然正确数增加，MCC却下降0.0425；不能称各来源均一致改善。', '']
    lines += ['|范围|ΔMCC及95%CI|ΔPA百分点及95%CI|Δfalse-S率百分点及95%CI|', '|---|---|---|---|']
    for name in ('selection1817', 'new1317', 'natural400', 'pressure100'):
        p = ps[name]; b = p['paired_patient_bootstrap']['metrics']; r = p['risk_recall_bootstrap']['false_S_rate']
        fmt = lambda v, scale: f"{scale*v['delta']:+.4f} [{scale*v['ci95'][0]:+.4f}, {scale*v['ci95'][1]:+.4f}]"
        lines.append(f"|{name}|{fmt(b['mcc'], 1)}|{fmt(b['percent_agreement'], 100)}|{fmt(r, 100)}|")
    lines += ['', '区间使用1000次配对患者cluster bootstrap，仅描述这批患者内抽样不确定性；跨0不是拒绝进展的门槛，也不覆盖历史选型、训练随机性或新医院泛化。完整召回区间、患者明细和混淆矩阵见[CPU分析](midpoint220_followup_analysis.json)。', '',
        '## 与现成MLP候选的同ID比较', '',
        '|完整1817候选|MCC|PA|正确数|false-S/真实非S|', '|---|---:|---:|---:|---:|']
    for name, m in data['same_ID_MLP_comparison']['selection1817'].items():
        lines.append(f'|{name}|{numbers(m)}|')
    lines += ['', '均为相同1817个ID、医生GT及原完整reference下的候选比较。120继续训练LoRA；MLP读取冻结107表征，监督范围、输出方式和训练量不同，因此不是单组件消融。两seed完整保留，不以较好seed替代另一结果。作者paper_r1只作历史参照。', '',
        '## 原160与500分面保留', '',
        '|范围／方案|MCC|PA|正确数|false-S/真实非S|', '|---|---:|---:|---:|---:|']
    for panel in ('screen160_natural', 'screen160_pressure', 'natural400', 'pressure100'):
        for model, label in [('label_only107', '107'), ('candidate', '120 step220'), ('paper_r1', 'paper_r1历史')]:
            lines.append(f"|{panel}／{label}|{numbers(ps[panel]['scores'][model])}|")
    lines += ['', '原160和500数值与逐例记录仍见[160](midpoint220_160.json)、[500](midpoint220_500.json)；新1317及全1817的原始统计见[1817](midpoint220_1817.json)。本次仅补CPU分析，不改这些数值文件，也不重发输出。', '',
        '## 状态与边界', '',
        '继续停止追加149步训练，保留固定220候选及其明确风险。后续决策应比较现成候选的质量、错误放行和类别代价，不将本结果写成“全无效”，也不自动升级默认系统。', '',
        '220步完整状态已回传`.local_models/120_full_pool_sft/evidence/full_pool_sft/train/checkpoint_a/`，192步备份保留。日志TimeoutError来自用户要求的保存暂停，不是OOM或预算到期。费用属于共享窗口，精确平台账单未核；本次CPU分析GPU/API新增0。122由主执行者恢复独立运行，本报告不控制GPU或宣称实例已停止计费。', '']
    (OUT/'report.md').write_bytes('\n'.join(lines).encode('utf-8'))


def update_decision(data):
    path = OUT/'stop_decision.json'; old = common.read(path)
    if old.get('decision') != 'retain_fixed_step220_as_quality_risk_candidate_after1817':
        old.setdefault('decision_history', []).append(dict(decision=old.get('decision'),
            evaluation_scope=old.get('evaluation_scope'), superseded_by='complete1817_CPU_followup'))
    if 'initial160_coverage' not in old:
        old['initial160_coverage'] = old.get('coverage')
    old.update(decision='retain_fixed_step220_as_quality_risk_candidate_after1817',
        reason='Complete1817 and new1317 retain substantial MCC/PA gains; false-S and NA costs are large. Compare candidate tradeoffs, no automatic deployment or further training.',
        evaluation_scope='complete unique1817 historically exposed development claims; initial160 and old500 preserved',
        current_results_scope='complete1817 plus separate new1317, old400/100 and initial128/32',
        coverage=data['coverage'], analysis_file='midpoint220_followup_analysis.json')
    old['full1817_results'] = {name: dict(scores=p['scores'], changes=p['changes'], delta_MCC=p['delta_MCC'],
        delta_PA=p['delta_PA'], delta_correct=p['delta_correct'], delta_false_S=p['delta_false_S'])
        for name, p in data['panels'].items() if name in ('selection1817', 'new1317')}
    old.setdefault('claim_limits', {}).update(full1817_evaluation_completed=True,
        quality_risk_tradeoff_described=True, automatic_deployment_approved=False,
        step369_efficacy_tested=False, independent_confirmation_used=False)
    old.setdefault('next_expansion_plan', {}).update(results_available=True, completed=True)
    old['next_expansion_plan']['status'] = 'completed; no automatic further evaluation'
    old.setdefault('resources', {}).update(instance_currently_used_for_separate122=True,
        next_priority='No further120 GPU work; main executor handles running122',
        this_CPU_analysis_GPU_CNY=0, this_CPU_analysis_API_CNY=0)
    old.setdefault('next_task', {}).update(status='122_resumed_by_main_executor; no effect result inferred here')
    old['CI_role'] = data['CI_role']
    common.put(path, old)


if __name__ == '__main__':
    main()
