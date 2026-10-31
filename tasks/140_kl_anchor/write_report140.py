"""Render140 only from actual fixed48 training and analyzed first outputs."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import argparse

from analyze140 import R, P, O, SCOPES, c, completed
from write_report138 import table, LABELS


def fmt(value, percent=False):
    return '—' if value is None else (f'{value:.2%}' if percent else f'{value:.4f}')


def score_table(scores):
    return table(scores, 'kl_anchor')


def details(scores, title):
    lines = ['', '## ' + title, '', '|配置|GT|Precision|Recall|F1|', '|---|---|---:|---:|---:|']
    for name, metric in scores.items():
        name = 'kl_anchor' if name == 'candidate' else name
        for label in LABELS:
            row = metric['per_class'][label]
            lines.append(f"|{name}|{label}|{fmt(row['precision'])}|{fmt(row['recall'])}|{fmt(row['f1'])}|")
    for name, metric in scores.items():
        name = 'kl_anchor' if name == 'candidate' else name
        lines += ['', name + '混淆矩阵（行GT、列预测；S/NS/NA）', '',
                  '|GT\\预测|S|NS|NA|', '|---|---:|---:|---:|']
        lines += ['|' + label + '|' + '|'.join(map(str, row)) + '|'
                  for label, row in zip(('S', 'NS', 'NA'), metric['confusion_matrix'])]
    return lines


def changes(value):
    lines = ['', '|GT|救回|误伤|净正确|', '|---|---:|---:|---:|']
    for label in LABELS:
        row = value['changes']['by_class'][label]
        lines.append(f"|{label}|{row['rescued']}|{row['harmed']}|{row['rescued']-row['harmed']:+d}|")
    change = value['changes']
    lines += ['', f"false-S新增{change['false_S_new']}、避免{change['false_S_avoided']}。"]
    return lines


def intervals(value):
    lines = []
    if 'patient_bootstrap' in value:
        for key, label in (('mcc', 'ΔMCC'), ('percent_agreement', 'ΔPA')):
            metric = value['patient_bootstrap']['metrics'].get(key)
            if metric and metric.get('ci95') is not None:
                lo, hi = metric['ci95']
                lines.append(f'{label}患者配对95%区间[{lo:+.4f}, {hi:+.4f}]。')
        for name, metric in value.get('risk_and_recall_bootstrap', {}).items():
            if metric.get('ci95') is not None:
                lo, hi = metric['ci95']
                lines.append(f'{name}差值95%区间[{lo:+.4f}, {hi:+.4f}]。')
        lines.append('使用既有评价函数的1000次患者cluster bootstrap；区间跨0不等于等效，不涵盖重训、历史选型或新医院泛化。')
    else:
        lines.append('本次未请求患者bootstrap；这里为点估计，不提供未计算的置信区间。')
    return ['', *lines, '']


def render(value, decision, done):
    scope, primary = value['scope'], value['primary']
    lines = [f'# 140 kl_anchor：{scope}', '', decision, '',
             f"固定48步/384次呈现已完成；目标{value['expected_N']}条，140有效{value['valid_N']}条，"
             f"与136共同有效{value['joint_valid_N']}条。只读取实际首答，缺失和无效不填旧答案。", '',
             '## 主比较：相同136输入', ''] + score_table(primary['scores'])
    lines += ['', f"相对136：ΔMCC {primary['delta_MCC']:+.4f}，ΔPA {primary['delta_PA']:+.2%}，"
              f"正确{primary['delta_correct']:+d}，false-S {primary['delta_false_S']:+d}。", '',
              '140与136的逐ID完整prompt token SHA一致。140从120 final369出发，以新Adam完成标签回放；'
              '在原标签位置加入固定0.5×KL(p120||p_current)、T=1，其余沿用138 label_replay。'
              'teacher为120全词表条件分布，训练156个ID、每轮192个位置、两轮384次呈现，'
              '不加入理由数据。推理仍为单个原生Judge，不使用分类器、融合或标签修正。', '']
    history = value['historical_common']
    lines += [f"## 历史配置共同有效{history['N']}条", '']
    if history['N']:
        lines += score_table(history['scores'])
    else:
        lines += ['没有覆盖全部指定历史配置的共同有效ID；各配置可用子集见下表和JSON。']
    lines += ['', '|历史配置|与140/136共同有效N|', '|---|---:|']
    lines += [f"|{name}|{part['N']}|" for name, part in value['historical_comparisons'].items()]
    for name, part in value['historical_comparisons'].items():
        if part['N'] and part['N'] != history['N']:
            lines += ['', f"{name}实际共同子集N={part['N']}：", ''] + score_table(part['scores'])
    lines += ['', '监督差别：107来自原196条标签；120使用2945条训练标签、369步；132为107与120的固定权重中点；'
              '136改变120评价输入；137在120上追加149步。paper_r1为作者不同模型/系统发布的历史预测，'
              '不能替代同模型对照。各表只能在自己的明确共同ID范围比较。', '']
    author = value['author_baseline_common']
    lines += [f"## 作者提示两种9B共同有效{author['N']}条", '']
    lines += score_table(author['scores']) if author['N'] else ['当前没有共同有效子集。']
    lines += ['', '作者提示未调9B与微调9B使用原作者式prompt及768输出上限；140/136采用104体系、claim_repeat和384上限。'
              '这里明确保留提示词与生成预算差异，不称严格同prompt训练消融。', '']
    base = value['same_prompt_unfinetuned_overlap']
    lines += [f"## 104未微调9B实际重合{base['N']}条", '']
    lines += score_table(base['scores']) if base['N'] else ['当前没有实际有效重合，不填0或借用其他未调模型结果。']
    lines += ['', '此处核对104未调基线与107/120基础104 prompt SHA相同；140/136另含相同claim_repeat，'
              '因此不能把这张表误称为140与未调9B的完全相同输入对照。', '']
    for arm, title in (('label_replay', '匹配标签回放'), ('rationale_tasks', '理由任务历史描述性对照')):
        part = value['matched138'][arm]
        lines += [f"## 与138 {title}直接比较：共同有效{part['N']}条", '']
        if part['N']:
            lines += score_table(part['scores'])
            lines += ['', f"140减138：ΔMCC {part['delta_MCC']:+.4f}，正确{part['delta_correct']:+d}，"
                      f"false-S {part['delta_false_S']:+d}。"]
            lines += changes(part) + intervals(part)
        else:
            lines += ['尚无可配对的实际首答，不计算对照成绩。', '']
        if part['N'] < value['joint_valid_N']:
            lines += ['对照尚未覆盖本表全部140/136共同ID；这项直接比较只适用于上述共同子集，不能外推至其余ID。', '']
        if arm == 'label_replay' and part.get('matched_training_file_SHA256'):
            lines += ['匹配回放按训练文件SHA确认相同输入、顺序和位置，均48步/384次呈现；只改变固定KL项。'
                      '是否保留仍需相对136有实际质量或风险价值，不能仅以超过较弱回放为依据。', '']
        elif arm == 'rationale_tasks':
            lines += ['rationale_tasks改变了36个任务位置的目标，与140不是单一KL差异；仅作历史描述，不归因于KL。', '']
    lines += ['## 140相对136的类别和患者变化'] + changes(primary)
    lines += ['', '|面板|N|ΔMCC|Δ正确|Δfalse-S|', '|---|---:|---:|---:|---:|']
    for name, part in value['panels'].items():
        lines.append(f"|{name}|{part['N']}|{part['delta_MCC']:+.4f}|{part['delta_correct']:+d}|{part['delta_false_S']:+d}|")
    lines += ['', '|作者|N|ΔMCC|Δ正确|Δfalse-S|', '|---|---:|---:|---:|---:|']
    for name, part in value['by_author'].items():
        lines.append(f"|{name}|{part['N']}|{part['delta_MCC']:+.4f}|{part['delta_correct']:+d}|{part['delta_false_S']:+d}|")
    patients = primary['patient_directions']
    up = sum(p['correct_delta'] > 0 for p in patients)
    down = sum(p['correct_delta'] < 0 for p in patients)
    risk_up = sum(p['false_S_delta'] > 0 for p in patients)
    risk_down = sum(p['false_S_delta'] < 0 for p in patients)
    lines += ['', f'患者正确数{up}升/{down}降/{len(patients)-up-down}平；'
              f'false-S {risk_up}升/{risk_down}降/{len(patients)-risk_up-risk_down}平。', '',
              '|患者ID|N|Δ正确|Δfalse-S|', '|---|---:|---:|---:|']
    lines += [f"|{p['sid']}|{p['N']}|{p['correct_delta']:+d}|{p['false_S_delta']:+d}|" for p in patients]
    lines += details(primary['scores'], '主比较三类表现与混淆矩阵')
    lines += ['', '|配置|Gwet AC1|false-S/non-S|预测S假发现率|', '|---|---:|---:|---:|']
    for name, metric in primary['scores'].items():
        name = 'kl_anchor' if name == 'candidate' else name
        lines.append(f"|{name}|{fmt(metric['gwet_ac1'])}|{fmt(metric['false_S_rate'], True)}|{fmt(metric['predicted_S_FDR'], True)}|")
    lines += intervals(primary)
    lines += ['## 覆盖、冻结门槛与限制', '', '|配置|目标|收到|有效|缺失|无效|', '|---|---:|---:|---:|---:|---:|']
    coverage_rows = [('kl_anchor', value['coverage']['candidate']),
                     ('claim_repeat136', value['coverage']['claim_repeat136'])]
    coverage_rows += [('138_' + arm, part['coverage']) for arm, part in value['matched138'].items()]
    coverage_rows += list(value['author_baseline_coverage'].items())
    coverage_rows += [('base104_9b', value['same_prompt_unfinetuned_overlap']['raw_coverage'])]
    for name, cov in coverage_rows:
        lines.append(f"|{name}|{cov['expected_N']}|{cov['received_N']}|{cov['valid_N']}|{len(cov['missing_ids'])}|{len(cov['invalid_ids'])}|")
    rule = value['screening']
    lines += ['', '冻结继续信号：' + str(rule) + '。',
              '160阶段沿用ΔMCC≥.015，或正确≥+3且ΔMCC≥−.01，或false-S≤−2、正确≥−3且ΔMCC≥−.03；'
              '500及扩大范围沿用.01/+5/−5及对应−.02风险下界。完整首答、共同有效率≥95%、'
              'false-S增加不超过3/5及原TP≥6类别不损失一半的保护不变。达到信号后在本轮持续目标与预算内决定扩大，不自动升级默认。', '',
              '训练仅用原32名训练患者；固定134评价患者与训练隔离但已有历史暴露，不称未接触holdout。'
              '缺失、无效、不能核对prompt及历史覆盖差异均单列；不重发成功首答，不用旧标签填空。'
              '其余历史/作者/匹配对照的完整P/R/F1、混淆矩阵、患者变化和覆盖ID见同名JSON。', '',
              'KL可能保留120原有错误，也可能妨碍有效更新；loss/KL下降不证明分类提升，'
              '单次训练与患者bootstrap不覆盖训练随机性。标签成绩不证明原生reason与标签自洽。', '']
    pointer_path = P / 'evidence/train/resume.json'
    returned = False
    if pointer_path.exists():
        pointer = c.read(pointer_path)
        if (pointer.get('step'), pointer.get('consumed')) == (48, 384):
            returned = (pointer_path.parent / pointer['slot'] / 'training_state.pt').exists()
    lines += ['本地完整训练状态已找到。' if returned else '本地完整训练状态回传尚未在本报告中确认；不据此推断远端状态。']
    session_path = P / 'bundle/data/session.json'
    if session_path.exists():
        session = c.read(session_path)
        now = datetime.now(timezone.utc)
        cost = max(0., now.timestamp() - session['start_epoch']) * session['hourly_CNY'] / 3600
        stamp = now.astimezone(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
        lines += ['', f"截至{stamp}，自本轮统一窗口起按连续开机估算GPU¥{cost:.3f}；"
                  '这是窗口墙钟估算，包含准备、等待、加载、编译和回传，不是本算法单独租金。API不由此离线脚本调用；不自动关机或释放。']
    lines += ['', f'[完整统计](kl_anchor_{scope}.json) · [固定方案](../../tasks/140_kl_anchor/PROTOCOL.md)']
    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', choices=SCOPES, default='screen160')
    parser.add_argument('--decision', required=True)
    args = parser.parse_args()
    done = completed(P / 'evidence/training_done.json', 'kl_anchor')
    value = c.read(O / ('kl_anchor_' + args.scope + '.json'))
    if (value.get('arm') != 'kl_anchor' or value.get('scope') != args.scope
            or value.get('source_adapter_sha256') != done['adapter_sha256']
            or (value.get('training_steps'), value.get('training_consumed')) != (48, 384)):
        raise ValueError('Analyzed output does not match this actual140 checkpoint')
    text = render(value, args.decision, done)
    O.mkdir(parents=True, exist_ok=True)
    (O / ('kl_anchor_' + args.scope + '.md')).write_bytes(text.encode('utf-8'))
    (O / 'report.md').write_bytes(text.encode('utf-8'))
    print(c.canonical(dict(scope=args.scope, N=value['joint_valid_N'], report='kl_anchor_' + args.scope + '.md')))


if __name__ == '__main__':
    main()
