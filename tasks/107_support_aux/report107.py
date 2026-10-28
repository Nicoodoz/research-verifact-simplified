"""Render107 CPU evaluation after confirmed GPU billing stop; no model calls."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import common107 as c

NAMES = {'label_only': 'label_only（三分类监督）',
         'support_aux': 'support_aux（训练期S/non-S辅助监督）',
         'paper_r1': 'paper_r1（作者历史预测）'}
SHORT = dict(zip(c.LABELS, ('S', 'NS', 'NA')))


def number(value, places=4, percent=False, signed=False):
    if value is None:
        return '未定义'
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Expected finite numerical result')
    return format(value * (100 if percent else 1), ('+' if signed else '') + f'.{places}f') + ('%' if percent else '')


def interval(value, percent=False):
    if value is None:
        return '未定义'
    return '[' + ', '.join(number(x, 2 if percent else 4, percent=percent) for x in value) + ']'


def choose(source, *paths):
    for path in paths:
        value = source
        for name in path.split('.'):
            if not isinstance(value, dict) or name not in value:
                value = None
                break
            value = value[name]
        if value is not None:
            return value
    return None


def text_value(value):
    if value is None:
        return '待核'
    if isinstance(value, bool):
        return '是' if value else '否'
    if not isinstance(value, (str, int, float)):
        return '见原始元数据'
    return str(value).replace('|', '\\|').replace('\n', ' ')


def main_table(panel):
    lines = ['|配置|MCC|PA|正确数|错误支持数|', '|---|---:|---:|---:|---:|']
    for arm in (*c.ARMS, 'paper_r1'):
        m = panel['metrics'].get(arm)
        if m is None:
            lines.append(f'|{NAMES[arm]}|未定义|未定义|未定义|未定义|')
        else:
            lines.append(f"|{NAMES[arm]}|{number(m['mcc'])}|{number(m['percent_agreement'], 2, True)}|{m['correct']}/{m['n']}|{m['false_S']}/{m['non_S']}|")
    return lines


def panel_details(name, panel):
    title = '自然' if name == 'natural' else '压力'
    paired = panel['paired']
    lines = [f'## {title}面板', '',
        f"冻结{panel['frozen_N']}条；本次两臂共同有效{panel['common_valid_N']}条。", ''] + main_table(panel)
    lines += ['', '差值方向均为support_aux减label_only；PA及召回差值以百分点显示。', '',
              '|指标|配对差值|患者cluster bootstrap 95% CI|', '|---|---:|---|']
    primary = (paired.get('primary') or {}).get('metrics', {})
    for field, label, pct in [('mcc', 'MCC', False), ('percent_agreement', 'PA', True), ('gwet_ac1', 'Gwet AC1', False)]:
        item = primary.get(field, {})
        delta=number(item.get('delta'), 2 if pct else 4, pct, True).replace('%','') if pct else number(item.get('delta'),signed=True)
        bounds=interval(item.get('ci95'),pct).replace('%','') if pct else interval(item.get('ci95'))
        lines.append(f"|{label+'（百分点）' if pct else label}|{delta}|{bounds}|")
    for field, label in [('false_S_rate', 'false-S/non-S'), ('S_recall', 'S召回'), ('NS_recall', 'NS召回'), ('NA_recall', 'NA召回')]:
        item = paired['risk'].get(field, {})
        lines.append(f"|{label}（百分点）|{number(item.get('delta'), 2, True, True).replace('%','')}|{interval(item.get('ci95'), True).replace('%','')}|")
    lines += ['', '|配置|Macro-F1|AC1|false-S/non-S|预测S假发现率|', '|---|---:|---:|---:|---:|']
    for arm in (*c.ARMS, 'paper_r1'):
        m = panel['metrics'].get(arm)
        if m:
            lines.append(f"|{arm}|{number(m['macro_F1'])}|{number(m['gwet_ac1'])}|{number(m['false_S_rate'], 2, True)}|{number(m['predicted_S_FDR'], 2, True)}|")
    lines += ['', '|配置|GT类别|GT数|预测数|Precision|Recall|F1|', '|---|---|---:|---:|---:|---:|---:|']
    for arm in (*c.ARMS, 'paper_r1'):
        m = panel['metrics'].get(arm)
        if not m:
            continue
        for label in c.LABELS:
            item = m['per_class'][label]
            lines.append(f"|{arm}|{SHORT[label]}|{item['support']}|{item['predicted']}|{number(item['precision'], 2, True)}|{number(item['recall'], 2, True)}|{number(item['f1'])}|")
    lines += ['', '混淆矩阵：行是原医生GT，列是预测，顺序S、NS、NA。', '']
    for arm in (*c.ARMS, 'paper_r1'):
        m = panel['metrics'].get(arm)
        if m:
            lines += [f'**{arm}**', '', '|GT\\预测|S|NS|NA|', '|---|---:|---:|---:|']
            lines += [f"|{SHORT[label]}|" + '|'.join(map(str, row)) + '|' for label, row in zip(c.LABELS, m['confusion_matrix'])]
            lines += ['']
    lines += ['### 救回、误伤与S预测变化', '', '|原GT|样本数|救回|误伤|净正确变化|', '|---|---:|---:|---:|---:|']
    for label in c.LABELS:
        item = paired['by_true_class'][label]
        lines.append(f"|{SHORT[label]}|{item['N']}|{item['rescued']}|{item['harmed']}|{item['rescued'] - item['harmed']:+d}|")
    s = paired['predicted_S']
    lines += ['', f"预测S：label_only {s['label_only']} → support_aux {s['support_aux']}（{s['support_aux'] - s['label_only']:+d}）。false-S新增{paired['false_S_new']}条，减少{paired['false_S_avoided']}条。",
        '救回指旧臂错误而新臂正确，误伤指旧臂正确而新臂错误。应结合正确S误伤、NS/NA召回与总正确变化判断；预测S减少本身不能证明核验改善。', '',
        '### 患者分组', '', '|患者|共同有效N|正确数差|false-S数差|预测S数差|', '|---|---:|---:|---:|---:|']
    for p in paired['patients']:
        lines.append(f"|{text_value(p['sid'])}|{p['N']}|{p['correct_delta']:+d}|{p['false_S_delta']:+d}|{p['supported_predictions_delta']:+d}|")
    lines += ['', '### 覆盖与无效输出', '', '|配置|冻结N|收到|有效|无效|缺失|全N PA上下界|全non-S false-S率上下界|', '|---|---:|---:|---:|---:|---:|---|---|']
    for arm in c.ARMS:
        v = panel['full_N_coverage'][arm]
        lines.append(f"|{arm}|{v['frozen_N']}|{v['received']}|{v['valid']}|{v['invalid']}|{v['missing']}|{interval(v['PA_full_bounds'], True)}|{interval(v['false_S_full_bounds'], True)}|")
    lines += ['', '上述上下界将缺失/无效按最好或最坏情形计入，不替换成旧答案。具体无效ID、原因和finish_reason保留在evaluation.json。', '']
    if panel.get('author'):
        lines += ['### 原命题来源分组（点估计）', '', '|来源|配置|N|MCC|PA|false-S|', '|---|---|---:|---:|---:|---:|']
        for author, arms in panel['author'].items():
            for arm, m in arms.items():
                if m:
                    lines.append(f"|{author}|{arm}|{m['n']}|{number(m['mcc'])}|{number(m['percent_agreement'], 2, True)}|{m['false_S']}/{m['non_S']}|")
        lines += ['']
    return lines


def generate(evaluation, output, *, resources=None, cost=None, backup=None, decision=None, gpu_billing_stopped=False):
    if not gpu_billing_stopped:
        raise ValueError('Run final CPU reporting only after actual GPU billing stopped; process exit is insufficient.')
    paths = dict(evaluation=Path(evaluation), resources=resources, cost=cost, backup=backup)
    inputs = {key: c.read(path) for key, path in paths.items() if path is not None}
    e = inputs['evaluation']
    if e.get('task') != 107 or e.get('primary_contrast') != 'fresh_label_only_vs_fresh_support_aux':
        raise ValueError('Expected the107 fresh two-arm evaluation')
    if not e.get('primary_common_ids_recomputed_for107') or not e.get('natural_and_pressure_never_pooled'):
        raise ValueError('Required107 cohort definition absent')
    for name in ('natural', 'pressure'):
        p = e['panels'][name]
        if p['common_valid_N'] != len(p['common_ids']) or len(set(p['common_ids'])) != p['common_valid_N']:
            raise ValueError('Common ID count or uniqueness mismatch')
    decision_text = Path(decision).read_text(encoding='utf-8-sig').strip() if decision else '待研究者评估：尚未填写基于真实指标的最终研究结论。'
    if not decision_text:
        raise ValueError('Empty final decision')
    detail = ['# 107完整指标', '', '只比较本次重新训练的label_only与support_aux；自然和压力分开，不沿用105三臂共同390/94条。', '']
    for name in ('natural', 'pressure'):
        detail += panel_details(name, e['panels'][name])
    detail += ['## 训练和推理成本', '', '|配置|训练步记录|训练秒（含保存）|其中保存秒|500条生成秒|生成tokens|收到预测|', '|---|---:|---:|---:|---:|---:|---:|']
    for arm in c.ARMS:
        t, v = e['training'][arm], e['inference_cost'][arm]
        detail.append(f"|{arm}|{t['observed_step_records']}|{number(t['logged_training_seconds'], 2)}|{number(t['logged_checkpoint_seconds'], 2)}|{number(v['generation_seconds'], 2)}|{v['output_tokens']}|{v['received']}|")
    detail += ['', '训练秒已包含保存秒，不重复相加。若步骤日志缺失或重复，该表只代表已记录的计算，完整开关机计费以费用记录为准。', '',
        '1000次患者cluster bootstrap为配对区间；区间跨0不能解释为等效。压力面板没有GT=S时，S召回未定义；不补0。区间不覆盖历史开发选择、重训种子或新医院泛化。', '']
    report = ['# 107最终报告', '', decision_text, '',
        '本实验验证成熟多任务学习在临床核验上的适配，不宣称原创算法。两臂从原Qwen3.5-9B重新训练，使用相同196条（S83、NS62、NA51）、原reference/医生GT、两轮50步。唯一研究差异是support_aux加入权重1的S/non-S BCE辅助监督；原三分类主loss、数据顺序和JSON推理接口保持不变。', '',
        '辅助头读取尚未看到真实答案的prompt末端隐藏态，与主任务共享一次backbone前向，推理不使用辅助头。CPU正确性、GPU技术检查及完整恢复证据与真实分类收益分别解释，loss下降不证明方法有效。', '']
    for name, title in [('natural', '自然'), ('pressure', '压力')]:
        p = e['panels'][name]
        report += [f'## {title}结果', '', f"本次两臂共同有效{p['common_valid_N']}/{p['frozen_N']}条。", ''] + main_table(p)
        pair = p['paired']; primary = (pair.get('primary') or {}).get('metrics', {})
        mcc, pa = primary.get('mcc', {}), primary.get('percent_agreement', {})
        report += ['', f"相对label_only：ΔMCC {number(mcc.get('delta'), signed=True)}，ΔPA {number(pa.get('delta'), 2, True, True).replace('%','')}个百分点；false-S新增{pair['false_S_new']}、减少{pair['false_S_avoided']}。", '']
        report += ['|原GT|救回|误伤|', '|---|---:|---:|'] + [f"|{SHORT[g]}|{pair['by_true_class'][g]['rescued']}|{pair['by_true_class'][g]['harmed']}|" for g in c.LABELS]
        report += ['', f"预测S {pair['predicted_S']['label_only']}→{pair['predicted_S']['support_aux']}；须同时看正确S误伤及NS/NA分类损失。", '']
    r, fee, b = inputs.get('resources', {}), inputs.get('cost', {}), inputs.get('backup', {})
    cost_values = {
        '实际GPU': choose(r, 'GPU', 'gpu', 'gpu_name', 'hardware.gpu', 'current_rented_GPU.model'),
        '小时报价（元）': choose(fee, 'hourly_cny', 'current_rate_cny_per_hour', 'active.hourly_cny'),
        '计费起点（北京时间）': choose(fee, 'billing_start_beijing'),
        '计费终点（北京时间）': choose(fee, 'billing_stop_beijing'),
        '累计计算估算（元）': choose(fee, 'gpu_cost_estimate_cny', 'compute_estimate_cny', 'estimated_GPU_cny', 'total_compute_cny', 'last_known_total_compute_cny', 'last_known_compute_cny'),
        '精确平台账单（元）': choose(fee, 'exact_invoice_cny'),
        '精确平台账单已核验': choose(fee, 'exact_platform_bill_verified'),
        '平台停止计费已确认': choose(fee, 'GPU_billing_stopped', 'billing_stopped', 'user_shutdown_confirmed', 'user_platform_confirmation_received'),
        '实例最终状态': choose(fee, 'instance_status', 'final_instance_status', 'platform_status'),
        '真实GPU方法实现已核验': choose(r, 'method_implementation_verified'),
        '辅助单独反向进入LoRA_B张量数': choose(r, 'auxiliary_only_gradient_LoRA_B_tensors'),
        '两臂同5090原底座新训练': choose(r, 'both_fresh_base_on_same_5090'),
        '主loss保持原105': choose(r, 'main_loss_unchanged'),
        '实际评价batch': choose(r, 'eval_batch_size'),
        '适配器及回执SHA已核验': choose(b, 'all_files_sha_verified', 'all_SHA_verified', 'all_sha_verified', 'SHA_verified', 'adapters_and_evidence_SHA_verified'),
        '两臂最终完整optimizer本地备份': choose(b, 'full_optimizer_final_each_arm_local', 'full_resume_checkpoints_local', 'complete_optimizer_backup_local'),
        '两臂最终适配器本地备份': choose(b, 'final_adapter_each_arm_local'),
        '辅助头本地备份': choose(b, 'aux_head_local'),
    }
    report += ['## 执行、保存与费用', '', '|事项|记录|', '|---|---|'] + [f'|{key}|{text_value(value)}|' for key, value in cost_values.items()]
    report += ['', '收费API新增0；GPU硬上限20元。未拿到精确平台账单时，计算估算不能写成精确实付；本地适配器备份不能冒充包含optimizer的完整恢复备份。源元数据未提供或缺少对应字段的事项标为待核。', '',
        '## 解释范围与研究决定', '',
        '本次仅在已有研究暴露的选型20名患者上比较；训练40人与选型患者隔离，未使用后续40名确认患者，不称全新未接触holdout。paper_r1只是同ID作者历史预测；未运行同期同模型verifact_ref，不能据此宣布超过原作者式强基线。', '',
        '自然与压力的三类指标、混淆矩阵、false-S新增/减少、患者分组及配对区间见[完整指标](final_metrics.md)和[evaluation.json](evaluation.json)。无效输出保留，不重发成功回执或用旧答案回填。', '',
        '本轮不追加辅助权重、采样、阈值、prompt、后处理或训练轮数，不扩训练池，不启108，不升级默认系统。后续是否值得确认，由真实MCC、false-S、PA和S/NS/NA得失共同决定；未填写结论时本报告不自动判定成功。', '']
    out = Path(output); c.write(out/'final_metrics.md', '\n'.join(detail)); c.write(out/'final_report.md', '\n'.join(report))
    training_complete = all((e['training'][arm].get('done') or {}).get('step') == 50 and (e['training'][arm].get('done') or {}).get('consumed') == 392 for arm in c.ARMS)
    source_files = {key: dict(name=Path(path).name, sha256=c.sha(path)) for key, path in paths.items() if path is not None}
    selfcheck = dict(task=107, status='FINAL_CPU_REPORT_RENDERED', executor_checks_only=True, independent_audit=False,
        all_frozen_first_requests_received=e.get('all_frozen_first_requests_received'), both50step392_consumption_recorded=training_complete,
        primary_common_ids_recomputed_for107=True, natural_and_pressure_never_pooled=True,
        no_fallback_recorded=e.get('missing_invalid_no_fallback'), auxiliary_head_unused_inference_recorded=e.get('auxiliary_head_never_used_at_inference'),
        evidence_insufficient=e.get('evidence_insufficient'), decision_text_supplied=bool(decision), method_effectiveness_automatic_judgment=None,
        method_implementation_verified=cost_values['真实GPU方法实现已核验'],
        GPU_billing_stop_attested_by_invoker=True, billing_stop_metadata_confirmation=cost_values['平台停止计费已确认'],
        exact_invoice_cny=cost_values['精确平台账单（元）'], backup_SHA_confirmation=cost_values['适配器及回执SHA已核验'],
        unchecked_metadata=[key for key, value in cost_values.items() if value is None],
        training_cost_log_complete={arm:e['training'][arm]['cost_log_complete'] for arm in c.ARMS},
        automatic_upgrade=False, confirmation40_new_use=False, API_new_cny=e.get('new_API_calls'), sources=source_files,
        report_files={name:c.sha(out/name) for name in ('final_report.md', 'final_metrics.md')})
    c.put(out/'final_selfcheck.json', selfcheck)
    return selfcheck


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    for name in ('resources', 'cost', 'backup', 'decision'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--gpu-billing-stopped', action='store_true', help='Actual billing has stopped, verified by the executor.')
    a = parser.parse_args()
    result = generate(a.evaluation, a.output_dir, resources=a.resources, cost=a.cost, backup=a.backup,
        decision=a.decision, gpu_billing_stopped=a.gpu_billing_stopped)
    print(c.canonical(dict(status=result['status'], decision_text_supplied=result['decision_text_supplied'], unchecked_metadata=result['unchecked_metadata'])))


if __name__ == '__main__':
    main()
