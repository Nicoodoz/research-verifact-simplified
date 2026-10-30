"""Summarize existing116-121 results on matched IDs; never calls a model."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys

R = Path(__file__).resolve().parents[2]
P = R/'.local_models'
O = R/'outputs/117_verdict_probe'
sys.path.insert(0, str(R/'tasks/109_boundary_replay'))
from analyze109 import metrics


def read(path):
    return json.loads((R/path).read_text(encoding='utf-8-sig'))


def rows(path):
    return [json.loads(line) for line in (R/path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def signature(score):
    return score['n'], score['correct'], score['false_S'], score['non_S'], score['confusion_matrix']


def compact(score):
    return {k: score[k] for k in ('n', 'mcc', 'percent_agreement', 'correct', 'false_S', 'non_S',
                                  'macro_F1', 'labels', 'confusion_matrix', 'per_class')}


def cell(score):
    return f"{score['mcc']:.4f} · {100*score['percent_agreement']:.2f}% · {score['correct']}/{score['n']} · {score['false_S']}/{score['non_S']}"


def same_ids(path, expected):
    values = rows(path)
    ids = [v['id'] for v in values]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError('Cached prediction coverage differs: '+str(path))


def anchor():
    key_rows = rows('.local_models/116_research_cycle/keys_selection1817.jsonl')
    keys = {r['id']: r for r in key_rows if r.get('old_panel') in ('natural', 'pressure')}
    all107 = rows('.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    p107 = {r['id']: r for r in all107 if r['id'] in keys}
    old = rows('outputs/105_brief_supervision/predictions_sanitized.jsonl')
    sources = {name: {r['id']: r for r in old if r['arm'] == name} for name in ('base_judge', 'label_only')}
    if len(keys) != 500 or any(set(v) != set(keys) for v in [p107, *sources.values()]):
        raise ValueError('Historical baseline IDs differ from fixed500')
    for i in keys:
        if any(v[i]['prompt_token_sha256'] != p107[i]['prompt_token_sha256'] for v in sources.values()):
            raise ValueError('Historical input differs')
        if not p107[i]['valid'] or any(p107[i][k] != keys[i][k] for k in ('GT', 'sid')):
            raise ValueError('107 baseline labels/coverage differ')
    result = dict(sources=['outputs/105_brief_supervision/predictions_sanitized.jsonl',
                          '.local_models/116_research_cycle/baseline107_selection1817.jsonl'],
                  original_input_identity_checked=True, new_inference=False, panels={})
    for panel in ('natural', 'pressure'):
        fixed = [r for r in keys.values() if r['old_panel'] == panel]
        valid = [r for r in fixed if all(v[r['id']]['parsed']['valid'] for v in sources.values())]
        pred = dict(base_judge105={r['id']: sources['base_judge'][r['id']]['parsed']['verdict'] for r in valid},
                    label_only105={r['id']: sources['label_only'][r['id']]['parsed']['verdict'] for r in valid},
                    label_only107={r['id']: p107[r['id']]['verdict'] for r in valid},
                    paper_r1={r['id']: r['paper_r1'] for r in valid})
        result['panels'][panel] = dict(expected_N=len(fixed), common_N=len(valid),
            invalid_by_arm={name: sum(not v[r['id']]['parsed']['valid'] for r in fixed) for name, v in sources.items()},
            scores={name: compact(metrics(valid, values)) for name, values in pred.items()})
    return result


def main():
    key_rows = rows('.local_models/116_research_cycle/keys_selection1817.jsonl')
    all_ids = {r['id'] for r in key_rows}
    old_ids = {r['id'] for r in key_rows if r.get('old_panel') in ('natural', 'pressure')}
    screen_ids = read('.local_models/117_verdict_probe/data_selection.json')['screen_ids']
    if (len(all_ids), len(old_ids), len(screen_ids), len(set(screen_ids))) != (1817, 500, 160, 160):
        raise ValueError('Fixed cohort sizes changed')
    scopes = {}

    def add(scope, label, source, parts, prediction=None, expected=None):
        parts = {k: v for k, v in parts.items() if k in ('natural', 'pressure', 'selection1817', 'new1317')}
        if prediction:
            same_ids(prediction, expected)
        if scope not in scopes:
            scopes[scope] = dict(baselines={name: {panel: compact(v['scores'][name]) for panel,v in parts.items()}
                                           for name in ('paper_r1', 'label_only107')}, candidates=[])
        for panel, value in parts.items():
            if value.get('missing_N', 0) or value.get('invalid_N', 0):
                raise ValueError('Use an explicitly separate common subset for incomplete coverage')
            for baseline in ('paper_r1', 'label_only107'):
                if signature(value['scores'][baseline]) != signature(scopes[scope]['baselines'][baseline][panel]):
                    raise ValueError('Baselines do not share the same cohort: '+label)
        scopes[scope]['candidates'].append(dict(name=label, source=source,
            panels={panel: dict(scores=compact(v['scores']['candidate']), changes=v['changes'],
                delta_MCC=v['delta_MCC'], delta_PA=v['delta_PA'], delta_correct=v['delta_correct'],
                delta_false_S=v['delta_false_S']) for panel,v in parts.items()}))

    for name in ('joint_path', 'single_token_107', 'gentle_refresh'):
        file = 'outputs/116_research_cycle/'+name+('_pilot' if name != 'gentle_refresh' else '')+'.json'
        add('original180', '116 '+name, file, read(file)['panels'])

    cached116 = read('.local_models/117_verdict_probe/recent116_comparison.json')
    for name, v in cached116['models'].items():
        add('old500', '116 '+name, v['source_analysis'].replace('\\','/'), v['panels'])
    for stem, title in [('probe_initial_500', '117 linear_initial'),
                        ('regularized_probe_500', '117 linear_regularized'),
                        ('balanced_probe_500', '117 linear_balanced'),
                        ('mlp_500', '117 mlp'), ('balanced_mlp_500', '117 mlp_balanced')]:
        file = 'outputs/117_verdict_probe/'+stem+'.json'
        for model, value in read(file)['models'].items():
            pred = 'outputs/117_verdict_probe/'+stem+'_'+model+'_predictions.jsonl'
            add('old500', title+'/'+model, file, value['panels'], pred, old_ids)

    file = 'outputs/117_verdict_probe/kernel_probe_160.json'
    for model, v in read(file)['models'].items():
        add('fixed160', '117 '+model, file, v['panels'])
    for stem, name in [('balanced_mlp_initial','117 mlp_balanced'),
                        ('../118_full_data_heads/full_linear_160','118 full_linear'),
                        ('../118_full_data_heads/full_mlp_160','118 full_mlp')]:
        file = str(Path('outputs/117_verdict_probe')/(stem+'.json'))
        data = read(file)
        for model, v in data['models'].items():
            pred = str(Path(file).with_name(Path(file).stem+'_'+model+'_predictions.jsonl'))
            add('fixed160', name, file, v['panels'], pred, screen_ids)
    file = 'outputs/119_warm_head_ft/trained_best160.json'
    v = read(file)['models']['warm_head_ft']
    add('fixed160', '119 warm_head_ft/369步', file, v['panels'],
        'outputs/119_warm_head_ft/trained_best160_predictions_sanitized.jsonl', screen_ids)
    file = 'outputs/121_nearest_memory/results.json'
    add('fixed160', '121 nearest_memory', file, read(file)['stages']['160']['panels'],
        '.local_models/121_nearest_memory/predictions_160.jsonl', screen_ids)

    midpoint120 = R/'outputs/120_full_pool_sft/midpoint220_160.json'
    if midpoint120.exists():
        v = read(midpoint120)['models']['full_pool_sft']
        add('fixed160', '120 full_pool_sft/220步中途检查', str(midpoint120.relative_to(R)), v['panels'],
            'outputs/120_full_pool_sft/midpoint220_160_predictions_sanitized.jsonl', screen_ids)
    midpoint500 = R/'outputs/120_full_pool_sft/midpoint220_500.json'
    if midpoint500.exists():
        add('old500', '120 full_pool_sft/220步', str(midpoint500.relative_to(R)),
            read(midpoint500)['models']['full_pool_sft']['panels'],
            'outputs/120_full_pool_sft/midpoint220_500_predictions_sanitized.jsonl', old_ids)
    midpoint1817 = R/'outputs/120_full_pool_sft/midpoint220_1817.json'
    if midpoint1817.exists():
        add('selection1817', '120 full_pool_sft/220步', str(midpoint1817.relative_to(R)),
            read(midpoint1817)['models']['full_pool_sft']['panels'],
            'outputs/120_full_pool_sft/midpoint220_1817_predictions_sanitized.jsonl', all_ids)

    file = 'outputs/116_research_cycle/claim_repeat_1817_missing.json'
    add('selection1817', '116 claim_repeat', file, read(file)['panels'],
        'outputs/116_research_cycle/claim_repeat_1817_missing_predictions.jsonl', all_ids)
    file = 'outputs/117_verdict_probe/balanced_mlp_1817.json'
    add('selection1817', '117 mlp_balanced', file, read(file)['models']['verdict_mlp']['panels'],
        'outputs/117_verdict_probe/balanced_mlp_1817_verdict_mlp_predictions.jsonl', all_ids)
    reconsidered117 = R/'outputs/117_verdict_probe/reconsidered_extension.json'
    if reconsidered117.exists():
        for model, value in read(reconsidered117)['models'].items():
            parts={dict(natural400='natural',pressure100='pressure').get(k,k):v
                   for k,v in value['panels'].items()}
            add('selection1817', '117 '+model+'（补充扩展）', str(reconsidered117.relative_to(R)), parts,
                'outputs/117_verdict_probe/reconsidered_extension_'+model+'_predictions.jsonl', all_ids)
    reconsidered121 = R/'outputs/121_nearest_memory/reconsidered_extension.json'
    if reconsidered121.exists():
        values=read(reconsidered121)['stages']
        add('old500', '121 nearest_memory（补充扩展）', str(reconsidered121.relative_to(R)), values['500']['panels'])
        add('selection1817', '121 nearest_memory（补充扩展）', str(reconsidered121.relative_to(R)), values['1817']['panels'],
            'outputs/121_nearest_memory/reconsidered_extension_predictions_sanitized.jsonl', all_ids)
    sqrt_file = R/'outputs/117_verdict_probe/sqrt_weight_mlp.json'
    if sqrt_file.exists():
        values=read(sqrt_file)['stages']
        add('old500', '117 sqrt_weight_mlp', str(sqrt_file.relative_to(R)), values['500']['panels'])
        full_parts=dict(values['1817']['panels'])
        full_parts['selection1817']=full_parts.pop('pooled')
        add('selection1817', '117 sqrt_weight_mlp', str(sqrt_file.relative_to(R)), full_parts,
            'outputs/117_verdict_probe/sqrt_weight_mlp_predictions.jsonl', all_ids)
    refit_file = R/'outputs/118_full_data_heads/reconsidered_refit.json'
    if refit_file.exists():
        for model in ('unweighted_full','sqrt_weight_full','full_linear'):
            values=read(refit_file)['models'][model]['panels']
            parts={dict(natural400='natural',pressure100='pressure').get(k,k):v for k,v in values.items()}
            add('selection1817', '118 '+model, str(refit_file.relative_to(R)), parts,
                'outputs/118_full_data_heads/reconsidered_refit_'+model+'_predictions.jsonl', all_ids)
    repeat_file = R/'outputs/118_full_data_heads/seed_stability.json'
    if repeat_file.exists():
        values=read(repeat_file)['models']['full3675_sqrt']['panels']
        parts={dict(natural400='natural',pressure100='pressure').get(k,k):v['seed118'] for k,v in values.items()}
        add('selection1817', '118 sqrt_weight_full / seed118', str(repeat_file.relative_to(R)), parts,
            'outputs/118_full_data_heads/seed_stability_full3675_sqrt_seed118_predictions.jsonl', all_ids)
    repeat_file = R/'outputs/118_full_data_heads/unweighted_workflow_seed118.json'
    if repeat_file.exists():
        values=read(repeat_file)['models']['seed118_original_workflow']
        parts={dict(natural400='natural',pressure100='pressure').get(k,k):v for k,v in values.items()
               if k in ('natural400','pressure100','new1317','selection1817')}
        add('selection1817', '117 MLP / seed118原选轮流程', str(repeat_file.relative_to(R)), parts,
            'outputs/118_full_data_heads/unweighted_workflow_seed118_predictions.jsonl', all_ids)
    complete120 = R/'outputs/120_full_pool_sft/full_pool_sft160.json'
    if complete120.exists():
        v = read(complete120)['models']['full_pool_sft']
        add('fixed160', '120 full_pool_sft/369步', str(complete120.relative_to(R)), v['panels'],
            'outputs/120_full_pool_sft/full_pool_sft160_predictions_sanitized.jsonl', screen_ids)

    data = dict(updated_beijing=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        scope='Recent116-121; same IDs within each table, not across tables', anchor=anchor(), scopes=scopes,
        paper_r1_historical_only=True, current_same_judge_verifact_ref_not_run=True,
        new_GPU=False, new_API=False, training_running=not complete120.exists() and not midpoint120.exists(),
        midpoint120_checked=midpoint120.exists(),
        caveat='All20 selection patients have historical exposure; no confirmation40 used. Baseline107 ancestors saw some internal-validation patients.')
    O.mkdir(exist_ok=True)
    (O/'recent_fair_comparison.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')

    lines = ['# 最近研究的同ID对比：116—122', '',
        '截至 '+data['updated_beijing']+'。107仍为低错误放行微调基线；117原MLP在完整1817已显示明显MCC/PA收益，同时有风险代价。120'+('仍在训练。' if data['training_running'] else '已有首轮结果，见表及120报告。')+'122保存暂停24步，优先120扩大后接续，尚无分类成绩。', '',
        '在完整1817个同ID上，107相对原作者历史系统：MCC **0.5445 vs 0.4842**，false-S **50 vs 105**；代价是少判对25条，PA **80.74% vs 82.11%**。这说明微调基线有实际的质量—风险收益，后续增量失败不能概括成“微调全部失败”。', '',
        '这里的“公平”首先指同一组ID、原医生GT和同一指标口径。paper_r1是原作者发布的历史系统预测，模型和推理设置未在本轮做同条件控制，因此只能作系统级历史参照，不能冒充同Judge同期强对照。107是当前普通微调主基线。新方案与107比较时也交代监督量、输出方式和成本差别，不把完整方案对比写成单组件消融。', '',
        '每格顺序均为 **MCC · PA · 正确数/评价数 · false-S/真实非S数**。自然与人为压力面板分开；160、180、500、1817不能跨表直接比数字。所有20名选型患者均有历史研究暴露，未使用后续确认40人。', '',
        '## 标签微调的历史收益仍然成立', '',
        '下面只用105未微调基线的有效共同ID；不沿用包含理由组时的390条自然子集，也不将107全400条数字搬到这里。只分析既有回执，没有补跑105。四者原输入token标识一致；105在A800/batch8，107在5090/batch2，仍属历史复用而非新同期重跑。', '',
        '|方案|自然共同ID|压力共同ID|', '|---|---|---|']
    for name, label in [('paper_r1','paper_r1 作者历史系统'),('base_judge105','未微调9B / 105接口'),
                        ('label_only105','105 label_only / 历史微调'),('label_only107','107 label_only / 当前微调基线')]:
        lines.append('|'+label+'|'+cell(data['anchor']['panels']['natural']['scores'][name])+'|'+cell(data['anchor']['panels']['pressure']['scores'][name])+'|')
    lines += ['', '105未微调基线15/500条输出无效，未重发、未用其他模型补齐。此表仅共同有效子集，覆盖损失仍保留。相对该未微调原接口，107自然多判对35条、false-S多1；压力多判对3条、false-S多5。标签微调有收益，但也不是所有指标全赢。', '']

    titles = [('fixed160','固定嵌套粗筛：自然128 / 压力32'),
              ('old500','完整旧面板：自然400 / 压力100'),
              ('selection1817','完整开发队列1817及新增1317'),
              ('original180','116中只做了原180的候选：自然120 / 压力60')]
    for scope, title in titles:
        group = scopes[scope]
        lines += ['## '+title, '']
        if scope == 'selection1817':
            panels = ('selection1817','new1317')
            lines += ['完整1817按其实际组成报告；新增1317也单列。两者不是将人工压力面板冒充自然分布。', '',
                      '|方案|完整1817|新增1317|', '|---|---|---|']
        else:
            panels = ('natural','pressure')
            lines += ['|方案|自然|压力|', '|---|---|---|']
        for model, label in [('paper_r1','paper_r1 历史系统'),('label_only107','107 label_only')]:
            lines.append('|'+label+'|'+'|'.join(cell(group['baselines'][model][p]) for p in panels)+'|')
        for row in group['candidates']:
            lines.append('|'+row['name']+'|'+'|'.join(cell(row['panels'][p]['scores']) for p in panels)+'|')
        if scope == 'fixed160' and data['training_running']:
            lines.append('|120 full_pool_sft / 正在训练|尚无分类结果|尚无分类结果|')
        if scope == 'fixed160':
            lines.append('|122 balanced_pool_sft / 保存暂停24步|尚无分类结果|尚无分类结果|')
        lines.append('')

    lines += ['## 实际得失与当前决定', '',
        '- 116 claim_repeat在1817条净多7条正确、false-S多1，MCC仅增加约0.0073；属于很弱的开发信号，未达到稳定保留的证据。',
        '- 117平衡MLP在500条净多3条正确、false-S少2；扩到1817后变成少12条正确、false-S仅少3，NA净损失11。小面板的信号没有维持。',
        '- 用户要求放宽过严取舍后，117原未加权MLP固定模型补评1317，完整1817 MCC升至0.6109、正确增加111、false-S增加42；线性头为0.5984、正确增加113、false-S增加61。MLP相对线性头少2条正确，换来更高MCC与少19次错误放行，值得保留为取舍候选。原先仅平衡MLP扩展的结论不能代表全部固定头。',
        '- 118原平衡头和线性头未给出综合增量。后续固定平方根权重重拟合全3675条，得到MCC0.5704、正确1504、false-S56/362；另一seed为0.5727、1524、74/362。两次质量收益均在，风险代价存在波动；不能只展示false-S较低的一次。',
        '- 无权重MLP按原内部验证选轮流程复验seed118，MCC0.5884、正确1562、false-S99/362，仍有质量收益。固定6轮的seed118诊断曾退化，不能将它冒充原选轮算法的完整复验或据此否定原流程。',
        '- 119完整训练自然MCC提高明显，但压力正确少6、合计false-S多7，NS正确9/24降到2/24。',
        '- 121最初160近邻检查后曾停止；固定配置补评完整1817后MCC为0.5911、正确增加117、false-S增加77，S/NS/NA净+172/−20/−35。它有真实MCC/PA收益，但风险与少数类代价大于117原MLP。原160停止记录和新扩展结果并列保留。',
        ('- 120按用户要求在220步/1760次呈现保存并提前检查：自然正确+14、压力−2，false-S合计10→20，NA正确23→16。有明显MCC收益，保留为需要扩大验证的风险取舍候选；暂停追加训练，不把风险增加等同于所有收益无效。原369步尚未完成。' if midpoint120.exists() else '- 120正在检验同32人2945条的原JSON/原loss续训，尚无分类结论。'),
        '- 122从原107重新开始，三类各243条、共729条、固定92步，检验均衡资料的实用配方。它同时改变资料组成与总呈现次数，不会单独证明类别不均衡是唯一原因。', '',
        '## 比较中的训练与接口差别', '',
        '|方案|实际监督范围与主要变化|', '|---|---|',
        '|107 label_only|原40患者中的196条，原9B新训练50步；主JSON基线|',
        '|116 claim_repeat / support_check|固定107权重，输入强调/核查提示变化；其余116候选另见原报告|',
        '|117探针/MLP/RBF|固定107表示；32患者中1024训练，8患者730内部验证选配置；输出来自分类头|',
        '|118 full_data_heads|固定107表示；原40患者3675条训练固定分类头|',
        '|119 warm_head_ft|107起点；32患者2945条训练369步，8患者730验证选369步；新分类头和LoRA联合训练|',
        '|120 full_pool_sft|107起点；与119同32人2945条、原JSON/原主loss、固定369步最终点；未加入分类头|',
        '|121 nearest_memory|固定107表示；32患者2945条记忆库，8患者730验证选择6个近邻配置中的一个|', '',
        '各方法内部验证存在107祖先已见少量原40人样本的历史暴露，不称完全无祖先暴露的验证。原180与旧500只重合70条；116 short/support源文件有610条，500表已按ID剔除额外110条。', '',
        '完整指标、三类precision/recall/F1和混淆矩阵见 [汇总JSON](recent_fair_comparison.json)。此摘要不新增bootstrap或独立医生审查，不将既有小面板选型反复使用包装成独立验证。', '',
        '来源：[105](../105_brief_supervision/final_report.md) · [107](../107_support_aux/final_report.md) · [116](../116_research_cycle/report.md) · [117](report.md) · [118](../118_full_data_heads/report.md) · [119](../119_warm_head_ft/report.md) · [120进度](../120_full_pool_sft/实时进度.md) · [121](../121_nearest_memory/report.md)。', '']
    (O/'recent_fair_comparison.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(dict(scopes={k:len(v['candidates']) for k,v in scopes.items()},
        anchor_common={k:v['common_N'] for k,v in data['anchor']['panels'].items()},
        new_inference=False, report=str(O/'recent_fair_comparison.md')),ensure_ascii=False))


if __name__ == '__main__':
    main()
