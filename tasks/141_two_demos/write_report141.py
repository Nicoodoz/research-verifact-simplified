"""Short141 report from verified analysis only; no model or training operations."""
from pathlib import Path
import argparse
import sys

from analyze141 import R, P, O, SCOPES, SOURCE120_SHA, EXAMPLE_IDS, c
sys.path.insert(0, str(R / 'tasks/140_kl_anchor'))
from write_report140 import changes, details, intervals, fmt
from write_report138 import table


def render(value, decision):
    scope, primary = value['scope'], value['primary']
    lines = [f'# 141 two_demos：{scope}', '', decision, '',
             f"目标{value['expected_N']}条，收到{value['coverage']['candidate']['received_N']}条，"
             f"有效{value['valid_N']}条，与136共同有效{value['joint_valid_N']}条；缺失和无效不补旧答案。", '',
             'two_demos（两条完整训练示例）：保持120 final369权重与136目标输入，前置固定S→NS两例完整对话；'
             '示例assistant仅含原标签JSON，没有reason。两例已用于120训练，不新增训练监督；无NA示例。'
             '所有reference完整保留，输出格式不变，无训练、无后接标签规则。', '',
             '## 主比较：136', ''] + table(primary['scores'], 'two_demos')
    lines += ['', f"相对136：ΔMCC {primary['delta_MCC']:+.4f}，ΔPA {primary['delta_PA']:+.2%}，"
              f"正确{primary['delta_correct']:+d}，false-S {primary['delta_false_S']:+d}。"]
    lines += changes(primary)
    control = value['matched_runtime_control']
    lines += ['', f"## 139运行设置匹配对照：仅固定160条，当前共同有效{control['N']}条", '']
    if control['N']:
        lines += table(control['scores'], 'two_demos') + changes(control) + intervals(control)
    else:
        lines += ['尚无可配对首答，不计算匹配运行对照成绩。']
    lines += ['', f"139 claim_control160与136核对有效{control['valid_vs136_N']}/160条，"
              f"差异标签{len(control['control_vs136_changed_ids'])}条；"
              f"完整160逐条相同确认={control['all160_labels_equal136']}。"
              '该对照与141同为batch1／32768／greedy384，但不提供500或1817条运行对照。', '',
              '## 历史与监督差别', '']
    history = value['historical_common']
    lines += [f"全部指定历史配置共同有效{history['N']}条。", '']
    lines += table(history['scores'], 'two_demos') if history['N'] else ['无覆盖全部历史配置的共同子集。']
    lines += ['', '|历史配置|与141/136共同有效N|', '|---|---:|']
    for name, part in value['historical_comparisons'].items():
        lines.append(f"|{name}|{part['N']}|")
        if part['N'] and part['N'] != history['N']:
            lines += ['', f"{name}实际子集：", ''] + table(part['scores'], 'two_demos')
    for name, part in value['optional_historical'].items():
        lines += ['', f"可选历史{name}：真实共同有效{part['N']}条。", '']
        if part['N']:
            lines += table(part['scores'], 'two_demos')
    lines += ['', '107用原196条标签，120扩为2945条标签训练；132为固定权重中点，137/138/140另有训练更新。'
              'paper_r1属于作者不同模型/系统的历史预测。141是已有权重上的in-context示例适配；'
              '这些历史比较不隔离单一组件效应。', '']
    author = value['author_baseline_common']
    lines += [f"作者prompt未调/微调9B及paper_r1共同有效{author['N']}条。", '']
    lines += table(author['scores'], 'two_demos') if author['N'] else ['无共同有效子集。']
    lines += ['', '作者prompt两种9B使用768输出上限，141使用104体系及384上限；提示词和生成预算差异保留。', '']
    base = value['same_prompt_unfinetuned_overlap']
    lines += [f"104原prompt未微调9B实际共同有效{base['N']}条。", '']
    lines += table(base['scores'], 'two_demos') if base['N'] else ['无真实重合，不填0或借其他条件替代。']
    lines += ['', '104未调基线的基础prompt指纹与107核对一致；136另含claim_repeat，141再增加两例，'
              '不称与141完全相同输入的未调对照。', '',
              '## 面板、作者与患者', '', '|面板|N|ΔMCC|Δ正确|Δfalse-S|', '|---|---:|---:|---:|---:|']
    for name, part in value['panels'].items():
        lines.append(f"|{name}|{part['N']}|{part['delta_MCC']:+.4f}|{part['delta_correct']:+d}|{part['delta_false_S']:+d}|")
    lines += ['', '|作者|N|ΔMCC|Δ正确|Δfalse-S|', '|---|---:|---:|---:|---:|']
    for name, part in value['by_author'].items():
        lines.append(f"|{name}|{part['N']}|{part['delta_MCC']:+.4f}|{part['delta_correct']:+d}|{part['delta_false_S']:+d}|")
    lines += ['', '|患者ID|N|Δ正确|Δfalse-S|', '|---|---:|---:|---:|']
    for row in primary['patient_directions']:
        lines.append(f"|{row['sid']}|{row['N']}|{row['correct_delta']:+d}|{row['false_S_delta']:+d}|")
    # Existing renderer only renames its own candidate label; provide141 name explicitly.
    named = {('two_demos' if name == 'candidate' else name): m for name, m in primary['scores'].items()}
    lines += details(named, '主比较三类P/R/F1及混淆矩阵')
    lines += ['', '|配置|Gwet AC1|false-S/non-S|预测S假发现率|', '|---|---:|---:|---:|']
    for name, m in named.items():
        fdr = '—' if m['predicted_S_FDR'] is None else f"{m['predicted_S_FDR']:.2%}"
        lines.append(f"|{name}|{fmt(m['gwet_ac1'])}|{m['false_S']}/{m['non_S']} ({fmt(m['false_S_rate'], True)})|{fdr}|")
    lines += intervals(primary)
    lines += ['## 覆盖、成本与边界', '', '|配置|目标|收到|有效|缺失|无效|', '|---|---:|---:|---:|---:|---:|']
    covs = [('two_demos', value['coverage']['candidate']), ('claim_repeat136', value['coverage']['claim_repeat136']),
            ('claim_control139_160', control['coverage']), *value['author_baseline_coverage'].items(),
            ('base104_9b', base['raw_coverage'])]
    for name, cov in covs:
        lines.append(f"|{name}|{cov['expected_N']}|{cov['received_N']}|{cov['valid_N']}|{len(cov['missing_ids'])}|{len(cov['invalid_ids'])}|")
    cost = value['input_cost']
    extra = '—' if cost['mean_extra_tokens'] is None else f"{cost['mean_extra_tokens']:.1f}"
    lines += ['', f"已回传首答平均增加输入{extra} tokens，总增加{cost['total_extra_tokens']}；"
              '模型仍只调用一次，但完整示例增加上下文开销。', '',
              '冻结继续信号：' + str(value['screening']) + '。沿用138/140的160及500质量/风险门槛，'
              '完整首答、≥95%有效覆盖、false-S及类别保护保持；不得因少数成功病例搜索顺序或更换示例。', '',
              '目标患者虽与两例训练患者分离，但有历史研究暴露，不称未接触holdout。'
              '所有分母、历史覆盖、救回误伤和其他配置完整P/R/F1及矩阵见JSON。'
              '标签成绩不证明reason自洽；无NA示例的影响不能从格式完整推定。', '',
              f"[完整统计](two_demos_{scope}.json) · [固定方案](../../tasks/141_two_demos/PROTOCOL.md)"]
    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', choices=SCOPES, default='screen160')
    parser.add_argument('--decision', required=True)
    args = parser.parse_args()
    value = c.read(O / ('two_demos_' + args.scope + '.json'))
    job = c.read(P / args.scope / 'bundle/data/job.json')
    if (value.get('task') != 141 or value.get('arm') != 'two_demos' or value.get('scope') != args.scope
            or value.get('adapter_sha256') != SOURCE120_SHA or job.get('adapter_sha256') != SOURCE120_SHA
            or value.get('demos_sha256') != job.get('demos_sha256')
            or c.sha(P / args.scope / 'bundle/data/job.json') != value['source_artifacts'][args.scope]['job_sha256']
            or tuple(value.get('example_ids', [])) != EXAMPLE_IDS or not value.get('joint_valid_N')):
        raise ValueError('Report requires actual verified141 analysis for this frozen job')
    text = render(value, args.decision)
    O.mkdir(parents=True, exist_ok=True)
    (O / ('two_demos_' + args.scope + '.md')).write_bytes(text.encode('utf-8'))
    (O / 'report.md').write_bytes(text.encode('utf-8'))
    print(c.canonical(dict(scope=args.scope, N=value['joint_valid_N'], report='two_demos_' + args.scope + '.md')))


if __name__ == '__main__':
    main()
