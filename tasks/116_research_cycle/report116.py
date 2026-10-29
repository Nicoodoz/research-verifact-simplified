"""Build a compact decision report; preserve every analysis in comparison.jsonl."""
from pathlib import Path
import json
import time

R = Path(__file__).resolve().parents[2]
O = R / 'outputs/116_research_cycle'
LABELS = ('Supported', 'Not Supported', 'Not Addressed')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def expected(part):
    return part.get('expected_N') or part['N']


def has_old500(result):
    panels = result['panels']
    return all(name in panels and expected(panels[name]) == size
               for name, size in (('natural', 400), ('pressure', 100)))


def scope_rank(result):
    """Choose coverage, never the most favourable metric or checkpoint."""
    panels = result['panels']
    if 'selection1817' in panels:
        return 3, panels['selection1817']['N']
    if has_old500(result):
        return 2, sum(panels[name]['N'] for name in ('natural', 'pressure'))
    return 1, sum(part['N'] for part in panels.values())


def score_row(label, part, arm, changes=None):
    score = part['scores'][arm]
    net = added_avoided = '—'
    if changes:
        net = '/'.join(f"{changes['by_class'][name]['rescued'] - changes['by_class'][name]['harmed']:+d}"
                       for name in LABELS)
        added_avoided = f"{changes['false_S_new']}/{changes['false_S_avoided']}"
    return (f"|{label}|{score['mcc']:.4f}|{score['percent_agreement']:.2%}|"
            f"{score['correct']}/{part['N']}|{score['false_S']}/{score['non_S']}|"
            f"{part['N']}/{expected(part)}|{net}|{added_avoided}|")


def add_table(lines, title, results, panel, historical=False):
    available = [result for result in results if panel in result['panels']]
    if not available:
        return
    lines += ['', f'### {title}', '',
              '|方案|MCC|PA|正确/有效|false-S/非S|有效/计划|S/NS/NA净正确|false-S新增/避免|',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    # Complete fixed cohorts share one baseline. Incomplete common-ID subsets
    # retain their own reference rows, rather than silently mixing denominators.
    reference_rows = []
    seen = {}
    for result in available:
        part = result['panels'][panel]
        subset = result['candidate'] if part['N'] != expected(part) else None
        for arm, label in (('label_only107', '107 label_only'), ('paper_r1', 'paper_r1（历史）')):
            if arm not in part['scores']:
                continue
            key = (subset, part['N'], expected(part), arm)
            metric = part['scores'][arm]
            essential = (metric['confusion_matrix'], metric['correct'], metric['false_S'], metric['non_S'])
            if key in seen:
                assert seen[key] == essential, 'Same fixed cohort has inconsistent reference counts'
                continue
            seen[key] = essential
            suffix = f"〔与{result['candidate']}共同有效〕" if subset else ''
            reference_rows.append(score_row(label + suffix, part, arm))
    lines.extend(reference_rows)
    history_path = O / 'historical180.json'
    if historical and history_path.exists():
        history = read(history_path)['panels'][panel]
        for key, label in (('103_base9b', '未微调9B（103原接口）'),
                           ('103_lora9b', '103微调（历史整套方案）')):
            entry = history[key]
            part = dict(N=entry['valid_N'], expected_N=entry['expected_N'],
                        scores={'history': entry['metrics']})
            lines.append(score_row(label, part, 'history'))
    for result in available:
        part = result['panels'][panel]
        lines.append(score_row(f"\x60{result['candidate']}\x60", part, 'candidate', part.get('changes')))


def main():
    state = read(O / 'cycle_state.json')
    analyses = []
    rows = []
    for name in state['completed_jobs']:
        path = O / (name + '.json')
        if not path.exists():
            continue
        result = read(path)
        if 'panels' not in result:
            continue
        analyses.append(result)
        for panel, part in result['panels'].items():
            for arm, score in part['scores'].items():
                rows.append(dict(job=name, panel=panel, arm=arm, N=part['N'],
                                 expected_N=expected(part), MCC=score['mcc'],
                                 PA=score['percent_agreement'], correct=score['correct'],
                                 false_S=score['false_S'], non_S=score['non_S'],
                                 recall={label: value['recall'] for label, value in score['per_class'].items()}))
    # Keep all attempted stages, including negative pilots and later expansions.
    (O / 'comparison.jsonl').write_bytes(
        ('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\n').encode())
    largest = {}
    for result in analyses:
        candidate = result['candidate']
        if candidate not in largest or scope_rank(result) >= scope_rank(largest[candidate]):
            largest[candidate] = result
    selected = list(largest.values())
    full = [result for result in selected if 'selection1817' in result['panels']]
    old500 = [result for result in selected if has_old500(result)]
    pilot_only = [result for result in selected if result not in full and result not in old500]

    snapshot = state.get('closed_epoch', time.time())
    elapsed = snapshot - state['start_epoch']
    cost = elapsed * state['hourly_CNY'] / 3600
    write(O / 'cost_status.json',
          dict(start_beijing=state['start_beijing'], snapshot_epoch=snapshot,
               elapsed_seconds=elapsed, GPU_estimate_CNY=cost, GPU_cap_CNY=state['GPU_cap_CNY'],
               API_CNY=state['paid_API_CNY'], API_cap_CNY=state['API_cap_CNY'],
               estimate_not_platform_invoice=True, no_shutdown=True, cycle_status=state['status']))
    lines = ['# 自主研究周期1：决策结果', '',
             state.get('current_takeaway', '仍在筛查，尚未达到周期主要目标。'), '',
             '107 label_only仍是主基线。全部为原20名患者的开发评价，所有患者均有历史暴露；'
             '不称独立盲测，原医生GT及首次回执保留。确认40人使用状态以本周期状态记录为准。', '',
             '各候选按最大已完成范围展示，不按最好成绩挑阶段。已有1817结果者另列其旧500同ID分面；'
             '180表只列尚未扩大者。类别净正确=救回−误伤，顺序S/NS/NA；'
             'false-S分母为共同有效ID中的真实非S数，缺失/无效不补旧答案。']
    if full:
        lines += ['', '## 1817条完整队列', '',
                  '按队列实际构成评价；覆盖不足1817时只能称该共同有效子集。']
        add_table(lines, '完整队列', full, 'selection1817')
    if old500:
        lines += ['', '## 旧500条分面', '', '自然400与人为压力100分别解释，不合并冒充自然分布。']
        add_table(lines, '自然400', old500, 'natural')
        add_table(lines, '压力100', old500, 'pressure')
    if pilot_only:
        lines += ['', '## 仅完成180条粗筛', '', '这些候选未补齐500；小面板成绩不能代替扩大验证。']
        add_table(lines, '自然120', pilot_only, 'natural', historical=True)
        add_table(lines, '压力60', pilot_only, 'pressure', historical=True)
        lines += ['', '103及其未微调9B只在原180条上有此处可复用的同ID结果；'
                  '103与107的监督规模、提示与损失不同，是整套历史方案比较，不能当单组件消融或1817条成绩。']

    lines += ['', '## 去留与限制', '']
    for result in selected:
        decision = state.get('decisions', {}).get(result['job'], '按该范围结果判断，未自动扩大。')
        lines.append(f"- \x60{result['candidate']}\x60：{decision.rstrip('。')}。"
                     f" [最大范围结果]({result['job']}.json)")
    if state.get('prepared_next_candidate') and state['prepared_next_candidate'] not in largest:
        lines.append(f"- \x60{state['prepared_next_candidate']}\x60：尚无已完成分类结果；"
                     f"当前执行状态为 \x60{state.get('active_job')}\x60，不预写成败。")
    strata = O / 'claim_repeat_1817_missing_strata.json'
    if strata.exists():
        section = read(strata)['sections']['selection1817']
        ci = section['patient_paired']['metrics']['mcc']['ci95']
        better = sum(p['scores']['candidate']['correct'] > p['scores']['base']['correct']
                     for p in section['patients'])
        worse = sum(p['scores']['candidate']['correct'] < p['scores']['base']['correct']
                    for p in section['patients'])
        lines += ['', f"claim_repeat的1817条ΔMCC患者95%区间为[{ci[0]:+.4f}, {ci[1]:+.4f}]"
                  f"（1000次bootstrap）；患者正确数改善/下降{better}/{worse}。"
                  '点估计增益很小，区间跨0不等于等效，也未证明稳定优势；不据此消耗确认40人。']
    overlap = O / 'single_token_short_500_missing_overlap.json'
    if overlap.exists():
        groups = read(overlap)['groups']
        lines += ['', f"single_token_short在180与500重合的70条净正确"
                  f"{groups['shared70']['correct_delta']:+d}；500其余430条净正确"
                  f"{groups['old500_only430']['correct_delta']:+d}、false-S"
                  f"{groups['old500_only430']['false_S_delta']:+d}。"
                  '扩大时权重未再训练，小面板阳性不能替代整体收益。']
    lines += ['', '## 配方、覆盖与成本', '',
              '- joint_path：115适配器＋完整JSON/EOS路径评分，每例三次完整前向。'
              '其他已评配方每例一次模型预测；输出概率不是校准风险概率。',
              '- claim_repeat只在reference外重述命题；support_check只补通用要素核对，'
              '均保留107权重和原JSON接口，没有增添临床事实。',
              '- single_token_short实际24步/192条、31名梯度患者，另8人128条选checkpoint；'
              '原768条/96步方案未跑完。single_token_107仅换同一三代码读出，不训练。'
              '两者均不能外推为所有判别学习方案无效。',
              '- gentle_refresh设计固定：107最终权重及Adam状态，114第二轮196条，'
              '学习率2e-5、25步，原JSON、完整reference与原分段loss不变。'
              '只取固定最后一步；是否已完成及效果以上表和当前状态为准。',
              '- 原180与旧500仅重合70条，面板定义也有差别；不能把两表之差当新增320条。'
              '逐例、三类召回、混淆矩阵、患者/来源分层及所有失败阶段保留在'
              ' [comparison.jsonl](comparison.jsonl) 和各原始分析JSON，不因主表压缩删除。',
              '',
              f"授权窗口：{state['start_beijing']}至{state['deadline_beijing']}（北京时间）；"
              f"本次记录的墙钟GPU估算¥{cost:.3f}/{state['GPU_cap_CNY']}，"
              f"API ¥{state['paid_API_CNY']}/{state['API_cap_CNY']}。含等待、加载和回传，非平台精确账单。",
              '',
              f"状态：\x60{state['status']}\x60；当前任务 \x60{state.get('active_job')}\x60；"
              f"当前保留方案 \x60{state['best_candidate']}\x60。未自动关机，实例留机仍计费。",
              '',
              '依据：[周期备忘](../../tasks/116_research_cycle/memo.md) · '
              '[粗筛规则](../../tasks/116_research_cycle/screen_rules.json) · '
              '[状态](cycle_state.json)。']
    if state.get('closed_epoch'):
        lines += ['', f"实际收束：{state['closed_beijing']}；GPU计算结束与关键回传时间见状态JSON。"
                  '收束后的留机和发布等待仍会产生租金，本记录不是关机账单。']
    (O / 'report.md').write_bytes(('\n'.join(lines) + '\n').encode())
    print(json.dumps(dict(rows=len(rows), displayed_candidates=len(selected),
                          completed=state['completed_jobs'], GPU_estimate_CNY=cost),
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
