"""Render142 conclusions only from actual verified analysis JSON."""
from pathlib import Path
import argparse,sys
from analyze142 import R,P,O,SCOPES,SOURCE120_SHA,c
sys.path.insert(0,str(R/'tasks/140_kl_anchor'))
from write_report140 import changes,details,intervals,fmt
from write_report138 import table


def rescue_harm(part):
    rows=part['changes']['by_class'].values()
    return sum(x['rescued'] for x in rows),sum(x['harmed'] for x in rows)


def render(value,decision):
    scope=value['scope'];primary=value['primary'];cov=value['coverage']['candidate']
    lines=[f'# 142 relevance_order：{scope}','',decision,'',
        f"固定目标{value['expected_N']}条，收到{cov['received_N']}、有效{value['valid_N']}；与136共同有效{value['joint_valid_N']}条。缺失/无效不补旧答案。",'',
        '唯一输入改动：原作者reference全部完整编号片段按固定008 BM25降序，平分保留原序；完整header/Text及原编号保留。'
        '仍使用120 final369、104定义与claim_repeat、BF16、batch2（长输入单条）、16384容量、greedy384，无新训练或示例。','',
        '## 主比较：136','']+table(primary['scores'],'relevance_order')
    lines += ['',f"相对136：ΔMCC {primary['delta_MCC']:+.4f}、ΔPA {primary['delta_PA']:+.2%}、正确{primary['delta_correct']:+d}、false-S {primary['delta_false_S']:+d}。"]
    lines += changes(primary)+intervals(primary)
    lines += ['## 推理成本（同目标ID范围，全部实际收到首答）','',
        '|配置|收到/有效/无效|生成秒（计时N）|每条均摊秒|平均输入/输出tokens（各自N）|实际batch：条数|',
        '|---|---|---:|---:|---|---|']
    for name,cost in value['inference_cost'].items():
        t=cost['generation_seconds'];a=cost['input_tokens'];b=cost['output_tokens']
        total=fmt(cost['complete_generation_total']) if cost['complete_generation_total'] is not None else '部分 '+fmt(t['sum'])
        lines.append(f"|{name}|{cost['received_N']}/{cost['valid_N']}/{cost['invalid_N']}|{total} ({t['recorded_N']})|{fmt(t['mean'])}|{fmt(a['mean'])} ({a['recorded_N']}) / {fmt(b['mean'])} ({b['recorded_N']})|{cost['batch_size_items']}|")
    lines += ['','seconds已按batch均摊，不重复相加batch_seconds；缺失计时为未记录，不填0。各阶段实测墙钟见JSON，仅在真实起止记录存在时提供；生成时间不包含全部准备、等待和回传，不能代替共享20元窗口总账。','']
    for name,cost in value['inference_cost'].items():
        for phase in cost['phase_walls']:
            lines.append(f"- {name}：{phase['received_N']}条，{phase['kind']}={fmt(phase['seconds'])}秒。")
    extra=value['input_cost']
    lines += ['',f"已收到样本平均输入变化{extra['mean_extra_tokens']:+.2f} tokens，总变化{extra['total_extra_tokens']:+d}；无新增API或训练。",'',
        '## 历史结果与真实覆盖','']
    common=value['historical_common'];lines += [f"全部指定历史配置共同有效{common['N']}条。",'']
    lines += table(common['scores'],'relevance_order') if common['N'] else ['无完整共同子集；不可混用不同分母。']
    for name,part in value['historical_comparisons'].items():
        if part['N']!=common['N']:
            lines += ['',f"{name}实际共同子集{part['N']}条：",'']
            if part['N']:lines += table(part['scores'],'relevance_order')
    lines += ['','107原196标签；120扩为2945训练标签；132是权重中点；137追加训练，138采用独立理由任务，140增加KL锚定。'
        'paper_r1是不同模型/系统的作者历史预测。142只改输入顺序；这些历史差异不作单组件归因。','']
    for key,title in [('author_baseline_common','作者prompt未调/微调9B'),('same_prompt_unfinetuned_overlap','104 prompt未调9B实际子集')]:
        part=value[key];lines += [f"### {title}：共同有效{part['N']}条",'']
        lines += table(part['scores'],'relevance_order') if part['N'] else ['无实际共同有效样本，不填0。']
        lines += ['']
    lines += ['作者接口两种9B使用768输出上限；本候选为104体系加claim_repeat及重排、384上限。104未调子集仅验证基础prompt与107一致，不是与142完全同输入。','',
        '## 面板、作者和患者得失','',
        '|分组|N|ΔMCC|Δ正确|Δfalse-S|救回/误伤|','|---|---:|---:|---:|---:|---:|']
    for group,collection in [('面板',value['panels']),('作者',value['by_author'])]:
        for name,part in collection.items():
            rescued,harmed=rescue_harm(part)
            lines.append(f"|{group}/{name}|{part['N']}|{part['delta_MCC']:+.4f}|{part['delta_correct']:+d}|{part['delta_false_S']:+d}|{rescued}/{harmed}|")
    lines += ['','|患者|N|Δ正确|Δfalse-S|救回/误伤|','|---|---:|---:|---:|---:|']
    for sid,part in value['by_patient'].items():
        rescued,harmed=rescue_harm(part)
        lines.append(f"|{sid}|{part['N']}|{part['delta_correct']:+d}|{part['delta_false_S']:+d}|{rescued}/{harmed}|")
    named={('relevance_order' if name=='candidate' else name):m for name,m in primary['scores'].items()}
    lines += details(named,'三类P/R/F1与混淆矩阵')
    lines += ['','|配置|Gwet AC1|false-S率|预测S假发现率|','|---|---:|---:|---:|']
    for name,m in named.items():lines.append(f"|{name}|{fmt(m['gwet_ac1'])}|{fmt(m['false_S_rate'],True)}|{fmt(m['predicted_S_FDR'],True)}|")
    lines += ['','## 覆盖与解释边界','', '|配置|目标|收到|有效|缺失|无效|','|---|---:|---:|---:|---:|---:|']
    covs=[('relevance_order',cov),('claim_repeat136',value['coverage']['claim_repeat136']),*value['author_baseline_coverage'].items(),
        ('base104_9b',value['same_prompt_unfinetuned_overlap']['raw_coverage'])]
    for name,row in covs:lines.append(f"|{name}|{row['expected_N']}|{row['received_N']}|{row['valid_N']}|{len(row['missing_ids'])}|{len(row['invalid_ids'])}|")
    lines += ['',f"冻结筛选判定：{value['screening']}。达到门槛仍须结合类别、自然/压力与成本决定，不自动扩大。",'',
        '训练63的已有AI辅助引用位置仅提供可行性依据，不是医生gold evidence，也不证明分类增益。047已做过C48前2块词重叠前置，'
        '本项不声称首次排序或算法原创。患者有历史暴露，bootstrap不覆盖既往选型、重训或新医院泛化。', '',
        f'[完整统计及各子集P/R/F1、矩阵](relevance_order_{scope}.json) · [固定方案](../../tasks/142_relevance_order/PROTOCOL.md)']
    return '\n'.join(lines).rstrip()+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=SCOPES,default='screen160')
    p.add_argument('--decision',required=True);p.add_argument('--out',type=Path,default=O);a=p.parse_args()
    value=c.read(a.out/('relevance_order_'+a.scope+'.json'));job=P/a.scope/'bundle/data/job.json'
    if (value.get('task')!=142 or value.get('arm')!='relevance_order' or value.get('scope')!=a.scope
        or value.get('source_adapter_sha256')!=SOURCE120_SHA or not value.get('joint_valid_N')
        or c.sha(job)!=value['source_artifacts'][a.scope]['job_sha256']):
        raise ValueError('Report requires actual verified142 results for this frozen job')
    text=render(value,a.decision);a.out.mkdir(parents=True,exist_ok=True)
    (a.out/('relevance_order_'+a.scope+'.md')).write_text(text,encoding='utf-8')
    (a.out/'report.md').write_text(text,encoding='utf-8')
    print(c.canonical(dict(scope=a.scope,N=value['joint_valid_N'],report='relevance_order_'+a.scope+'.md')))


if __name__=='__main__':main()
