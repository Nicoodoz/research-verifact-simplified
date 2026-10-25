"""Single concise report from frozen statistics plus explicitly authored interpretation."""
from collections import Counter
import common014 as c

def run(output=None):
    root=c.OUT/'analysis_001';m=c.read(root/'metrics.json');s=c.read(root/'summary.json');o=c.read(root/'overlap.json')
    decision=c.read(c.TASK/'interpretation.json')
    f=lambda x:f'{x:.4f}'
    ci=lambda v:'['+', '.join(f(x) for x in v)+']'
    lines=['# 014：Qwen3.8-27B与V4-Flash固定证据比较',
        '**'+decision['verdict']+'**',decision['reason'],
        '执行与自查完成，准备独立审计；本报告不代表独立审计PASS。',
        '## 1. 比较范围与公平性',
        '固定009–010的6名既用development患者、650条valid atomic claims（LLM243、人写407）。Qwen原生请求只替换model字段；原claim、冻结C48 reference、structured prompt、标签定义、temperature=0、thinking=false、max_tokens=2048及json_schema均保持。没有重检索、重排、prompt优化、新患者或V4调用。',
        'C48已知的条件/身份等信息损失继续保留。本轮比较模型对这套实际证据包的处理，不能外推为完整EHR下的能力排序，也不把发布reference当医生gold evidence。',
        '主对照提前选定010完整C48 canonical结果；009旧C48只作非同期敏感性。010 V4于2026-09-15 02:51–03:38 UTC运行，Qwen于'+s['qwen_start']+'至'+s['qwen_end']+'运行。相同字符串不等于相同tokenizer/模板或计算量，服务未提供不可变权重指纹；小幅差异不能孤立归为模型能力。已有009→010同C48 body发生80/650次标签变化。',
        '## 2. 差距多大',
        '统一调用002 evaluate/paired_compare：valid-only、完整分母、三分类micro PA/AC1/MCC、1000次患者cluster bootstrap；以下方向均为Qwen−010 V4。',
        '|作者/模型|n|PA|AC1|MCC|','|---|---:|---:|---:|---:|']
    for author in ('llm','human'):
        for name in ('v4_010','qwen'):
            v=m[author][name];lines.append(f"|{author}/{name}|{v['n']}|{v['percent_agreement']:.2%}|{f(v['gwet_ac1'])}|{f(v['mcc'])}|")
    lines+=['','|作者|ΔPA（百分点）[95%区间]|ΔAC1 [95%区间]|ΔMCC [95%区间]|','|---|---|---|---|']
    for author in ('llm','human'):
        d=m[author]['qwen_minus_v4_010']['metrics'];p=d['percent_agreement'];a=d['gwet_ac1'];v=d['mcc']
        lines.append(f"|{author}|{p['delta']*100:+.2f} [{p['ci95'][0]*100:+.2f}, {p['ci95'][1]*100:+.2f}]|{a['delta']:+.4f} {ci(a['ci95'])}|{v['delta']:+.4f} {ci(v['ci95'])}|")
    lines+=['',decision['overall'],
        '六患者区间只能表达该开发队列下的不确定性，不是正式非劣证明。事前“接近”描述标尺为两作者ΔMCC≥−0.05、ΔPA≥−3个百分点、错判S增加≤各作者分母2%；完整判定见[nearness.json](analysis_001/nearness.json)。这不是临床安全阈值或自动续跑授权。',
        '## 3. 类别代价与混淆',
        '|作者/GT|分母|V4正确→Qwen正确|V4召回→Qwen召回|Qwen precision / F1|','|---|---:|---:|---|---|']
    for author in ('llm','human'):
        for label in c.LABELS:
            a=m[author]['v4_010']['per_class'][label];b=m[author]['qwen']['per_class'][label]
            ratio=lambda v:'未定义' if v is None else f'{v:.1%}'
            lines.append(f"|{author}/{label}|{a['support']}|{a['tp']}→{b['tp']}|{ratio(a['recall'])}→{ratio(b['recall'])}|{ratio(b['precision'])} / {ratio(b['f1'])}|")
    lines+=['',decision['classes'],'混淆矩阵行=原GT、列=预测；顺序均为S/NS/NA（Supported/Not Supported/Not Addressed）。']
    for author in ('llm','human'):
        lines+=['',f'**{author}**','|GT|V4：S / NS / NA|Qwen：S / NS / NA|','|---|---|---|']
        for i,label in enumerate(('S','NS','NA')):
            a=m[author]['v4_010']['confusion_matrix'][i];b=m[author]['qwen']['confusion_matrix'][i]
            lines.append('|'+label+'|'+' / '.join(map(str,a))+'|'+' / '.join(map(str,b))+'|')
    lines+=['','全部precision/recall/F1、TP/FP/FN/TN与完整精度见[类别表](analysis_001/classes.csv)。NS同时包含支持不足，不应全部解释为直接医学矛盾。',
        '## 4. 错误是否重合',
        '|作者|V4错 / Qwen错|共同错|Qwen改对 / 改错|共同对|错误Jaccard|共同错占V4错 / Qwen错|','|---|---:|---:|---:|---:|---:|---:|']
    for author in ('llm','human'):
        v=o[author];x=v['movements']
        lines.append(f"|{author}|{v['v4_errors']} / {v['qwen_errors']}|{v['intersection']}|{x.get('qwen_corrected',0)} / {x.get('qwen_broke',0)}|{x.get('both_correct',0)}|{v['jaccard']:.1%}|{v['intersection_over_v4_errors']:.1%} / {v['intersection_over_qwen_errors']:.1%}|")
    lines+=['',decision['overlap'],'错误Jaccard=两模型错误交集/错误并集；不是标签一致率，也不是可实现的模型组合收益。[逐条台账](analysis_001/transitions.csv)保存全部650条；[重合统计](analysis_001/overlap.json)另分同错同标签与同错不同标签。',
        '## 5. 逐患者与非同期敏感性',
        '|患者|LLM净正确数 / ΔMCC|human净正确数 / ΔMCC|','|---|---:|---:|']
    p=c.csvrows(root/'patients.csv')
    for sid in sorted({x['subject_id'] for x in p}):
        cells=[]
        for author in ('llm','human'):
            a=next(x for x in p if x['subject_id']==sid and x['author']==author and x['model']=='v4_010')
            b=next(x for x in p if x['subject_id']==sid and x['author']==author and x['model']=='qwen')
            cells.append(f"{int(b['correct'])-int(a['correct']):+d} / {float(b['mcc'])-float(a['mcc']):+.4f}")
        lines.append('|'+sid+'|'+'|'.join(cells)+'|')
    lines+=['',decision['patients']]
    for author in ('llm','human'):
        d=m[author]['qwen_minus_v4_009']['metrics'];lines.append(f"相对009旧C48，{author} ΔPA={d['percent_agreement']['delta']*100:+.2f}个百分点，ΔMCC={d['mcc']['delta']:+.4f}；该敏感性不替换010主对照。")
    lines+=['','## 6. 集中缺陷与案例边界',decision['semantic'],
        f"按事前作者×改对/改错/共同错/共同对规则选{s['selected_semantic_cases']}例（目标24例，格不足则全取），核对相同完整reference和两模型完整输出；这些是有目的的解释样本，不估计总体机制比例。未新增医学GT，模型解释不是内部因果证明，未做补证或优化实验。[完整案例与引用](review_001/case_index.csv)。",
        '## 7. 是否值得成为私有化研究模型',decision['research'],
        '官方模型卡给出Qwen语言模型27B稠密参数与Apache-2.0开放权重；V4-Flash为284B总参数、13B激活的MoE。Qwen总权重规模明显较小，有私有化研究动机，但这不意味着激活计算量更低或本地更快。这里没有下载权重、测显存/速度或评估量化损失，也不能确认API与某个公开checkpoint完全等价。[Qwen模型卡](https://huggingface.co/Qwen/Qwen3.8-27B) · [V4模型卡](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash)',
        'Qwen官方非thinking推荐采样包含temperature=0.7等设置；014按用户要求沿用V4 temperature=0，未作Qwen专用调参。本结果限定为固定配置下的可比baseline，不是Qwen的能力上限。任何后续本地部署/训练或新实验另行立项，不消耗剩余development或reserved test。',
        '## 8. 执行、费用与复核',
        f"650条Qwen有效预测：{s['valid_qwen']}/650；HTTP尝试{s['http_attempts']}次，状态{s['http_status_counts']}。账户别名{s['accounts']}。累计费用估算/未知预留¥{s['task_cost_or_reserved_cny']:.6f}，任务上限¥40，非已核对账单。无新增V4、检索、embedding或rerank费用；首批4条包含在650内。",
        f"Qwen input/output tokens={s['usage']['qwen']['input_tokens']}/{s['usage']['qwen']['output_tokens']}；V4历史相同650条件为{s['usage']['v4_010']['input_tokens']}/{s['usage']['v4_010']['output_tokens']}。Qwen解释结构/词数等诊断{s['usage']['qwen']['adherence_flagged']}条，V4 {s['usage']['v4_010']['adherence_flagged']}条；合法标签均按原规则保留。",
        '按调用前核对的官方价格，Qwen每百万input/output为3/12元；prompt全部按输入价计算，未自行假定缓存折扣。每次开始、完整body、回执、usage、失败/未知预留及费用均可回查。[价格页](https://siliconflow.cn/pricing) · [尝试账本](analysis_001/attempts.csv) · [冻结协议](protocol_001.md)。',
        '原始数据与001–013历史成果不改写；离线验证及精确版本见[audit_handoff.md](audit_handoff.md)。当前是执行者自查完成、等待独立审计，不自行宣告PASS。']
    rendered=''
    for i,line in enumerate(lines):
        separator='\n' if i and line.startswith('|') and lines[i-1].startswith('|') else '\n\n'
        rendered+=(separator if i else '')+line
    with (output or c.OUT/'report.md').open('x',encoding='utf-8',newline='\n') as f:f.write(rendered+'\n')

if __name__=='__main__':run()
