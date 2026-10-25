"""One Chinese report from replayable statistics and explicit executor interpretation."""
from pathlib import Path
import common015 as c

def run(output=None):
    root=c.OUT/'analysis_001';m=c.read(root/'metrics.json');p=c.read(root/'paired.json');s=c.read(root/'summary.json');g=c.read(root/'gate.json')
    d=c.read(c.TASK/'interpretation.json');rows=c.csvrows(root/'transitions.csv');economics=s['economics']
    names={'v4':'V4单模型','qwen':'Qwen单模型','adjudication':'分歧仲裁','evidence_only':'无候选重判'}
    lines=['# 015：分歧仲裁能否利用两模型互补', '**'+d['verdict']+'**',d['main_finding'],
        '执行与自查完成，准备独立审计；不是独立审计PASS。',
        '## 1. 为什么值得检验',
        '014的650条中78条分歧（12%）：LLM30/243、人写48/407。分歧中V4独对35、Qwen独对36、两边均错7。最强单模型总正确527；只在两个标签中完美选择可到562（+35，+5.38个百分点），允许第三标签的分歧oracle可到569（+42，+6.46个百分点）。这些是正确数/PA上界，不能实现的GT选择不算方法成绩。',
        '572条一致原样接受，其中81条共同错误不可能被本流程修复。研究问题是能否在不知道GT时利用候选分歧，而不是证明存在oracle空间。',
        '## 2. 固定方法与简单对照',
        '使用014同六名既用development患者、650条valid atomic claims；V4基础答案来自010、Qwen来自014，原claim及C48逐字保留。仅78条分歧新调用V4-Flash，输入匿名双方完整structured判断，按证据可返回任意S/NS/NA。未改检索、packing、claim或医学规则；没有GT、source/BHC、额外病历、作者类型或模型名称进入请求。',
        '唯一对照同一V4、同一独立复核system、原claim/reference及生成设置，仅省略候选判断字段。它检验提供候选信息是否优于额外一次证据重判；不能拆分标签、理由和额外输入长度各自贡献。双方各78次，ID哈希交错；候选A为V4共44、Qwen34，与GT无关。temperature=0、thinking=false、max_tokens=2048及原json_schema固定，成功回答不重生成。',
        '候选顺序有一处协议文字偏差：协议写哈希首位奇偶，调用前冻结代码和实际输入取整串整数奇偶（等同末位），35/78条与首位写法的顺序不同。实际顺序仍仅由ID确定、与GT无关；原输入保留，未反转或重跑选优，不能假设另一顺序结果相同。[偏差记录](execution_deviation_001.md)。',
        '这里的独立指新的调用上下文，仲裁器仍是V4而非第三个独立训练模型。候选匿名不保证消除风格识别和自偏好；未做顺序反转或重复试验。基础答案非同期，014也尚未独立审计；本轮先从原回执复算核对，仍不能将微小差异都归因于分歧机制。',
        '## 3. 完整650条成绩',
        '统一002评价：valid-only、完整分母、三分类micro PA/AC1/MCC、1000次患者cluster bootstrap，作者分开。',
        '|作者|方法|正确/n|PA|AC1|MCC|','|---|---|---:|---:|---:|---:|']
    for a in ('llm','human'):
        for name in names:
            x=m[a][name];n=sum(x['confusion_matrix'][i][i] for i in range(3))
            lines.append(f"|{a}|{names[name]}|{n}/{x['n']}|{x['percent_agreement']:.2%}|{x['gwet_ac1']:.4f}|{x['mcc']:.4f}|")
    lines+=['',d['effect_interpretation'],'|作者|仲裁相对|ΔPA百分点 [95%区间]|ΔAC1 [95%区间]|ΔMCC [95%区间]|','|---|---|---|---|---|']
    for a in ('llm','human'):
        for name in ('v4','qwen','evidence_only'):
            x=p[a]['adjudication_minus_'+name]['metrics'];cells=[]
            for key,scale in [('percent_agreement',100),('gwet_ac1',1),('mcc',1)]:
                y=x[key];digits=2 if scale==100 else 4
                cells.append(f"{y['delta']*scale:+.{digits}f} [{y['ci95'][0]*scale:+.{digits}f}, {y['ci95'][1]*scale:+.{digits}f}]")
            lines.append('|'+a+'|'+names[name]+'|'+'|'.join(cells)+'|')
    lines+=['','区间反映六名已用开发患者的不确定性；不得把区间跨0当作相等或把开发筛选称独立验证。所有完整精度和对照比较见[机器评价](analysis_001/metrics.json)与[配对结果](analysis_001/paired.json)。',
        '## 4. 到底选对了哪些分歧',
        '|作者|分歧类型|n|仲裁正确|无候选正确|仲裁选V4/Qwen/第三标签|','|---|---|---:|---:|---:|---|']
    for b in c.csvrows(root/'bucket_outcomes.csv'):
        if b['bucket']=='agreement':continue
        lines.append(f"|{b['author']}|{b['bucket']}|{b['n']}|{b['adjudication_correct']}|{b['evidence_only_correct']}|{b['selected_v4']}/{b['selected_qwen']}/{b['third_label']}|")
    lines+=['',d['disagreement_interpretation'],
        '两边均错且同标签的81条保持原错。分歧中均错的7条单独统计新修复/仍错；已经错误的case换成另一错误标签没有新增正确数损失，但可能改变NS/NA或错误接受S的性质。[完整逐条台账](analysis_001/transitions.csv)保留650条，[候选顺序诊断](analysis_001/order_diagnostics.csv)只作描述，不当作随机顺序因果试验。',
        '## 5. 类别代价和患者一致性',
        '|作者/GT|n|V4正确|Qwen正确|仲裁正确（召回）|无候选正确|','|---|---:|---:|---:|---:|---:|']
    for a in ('llm','human'):
        for label in c.LABELS:
            x=[m[a][name]['per_class'][label] for name in names]
            lines.append(f"|{a}/{label}|{x[0]['support']}|{x[0]['tp']}|{x[1]['tp']}|{x[2]['tp']} ({x[2]['recall']:.1%})|{x[3]['tp']}|")
    lines+=['',d['class_interpretation'],'混淆矩阵行=GT、列=预测，顺序S/NS/NA：','|作者/方法|GT S→S/NS/NA|GT NS→S/NS/NA|GT NA→S/NS/NA|','|---|---|---|---|']
    for a in ('llm','human'):
        for name in names:lines.append('|'+a+'/'+names[name]+'|'+'|'.join('/'.join(map(str,row)) for row in m[a][name]['confusion_matrix'])+'|')
    lines+=['','|患者|LLM仲裁净正确：相对V4/Qwen|human仲裁净正确：相对V4/Qwen|两作者合计相对患者较强单模型|','|---|---:|---:|---:|']
    for sid,delta in g['patient_deltas'].items():
        cells=[]
        for a in ('llm','human'):
            rr=[r for r in rows if r['subject_id']==sid and r['author_type']==a]
            cells.append('/'.join(f"{c.correct(rr,'adjudication')-c.correct(rr,k):+d}" for k in ('baseline','qwen')))
        lines.append('|'+sid+'|'+'|'.join(cells)+f'|{delta:+d}|')
    lines+=['',d['patient_interpretation'],'三类别precision/recall/F1与全部患者PA/AC1/MCC见[类别表](analysis_001/classes.csv)、[逐患者表](analysis_001/patients.csv)。',
        '## 6. 是否达到明显提升门槛',
        '调用前要求全部通过：总正确比较强单模型至少+20；LLM≥+5、人写≥+10；两作者MCC≥+0.04且AC1都提高；比无候选对照总≥+8、每作者≥+2且MCC不降；类别保护及错误S保护；至少4/6患者提高且无患者低于−2；完整有效。它是较高开发筛选标尺，不是临床安全标准。',
        f"实际总净正确相对较强单模型{g['total_gain_vs_best']:+d}，相对无候选对照{g['total_gain_vs_control']:+d}。整体winner={g['winner']}。",
        '未通过条件：'+ '；'.join(k for k,v in g['conditions'].items() if not v)+'。',d['stop_decision'],
        '[全部门槛与实际值](analysis_001/gate.json)；[调用前协议](protocol_001.md)。',
        '## 7. 原因观察与成本是否值得',d['semantic_interpretation'],
        f"按事前规则完整核对{s['semantic_cases']}例的原claim、C48及四份输出，字面引用见[案例索引](review_001/case_index.csv)。有目的选例不能估计总体机制占比，原GT不变，未新增医学裁决，理由文本不证明模型内部因果。",
        f"理想部署每650条需650次V4+650次Qwen+78次仲裁，共{economics['deployed_calls']}次Judge调用，为单模型的{economics['deployed_calls']/650:.2f}倍。使用共同无缓存/无时段优惠价格及实际usage：V4单模型¥{economics['v4_650_uniform_cny']:.4f}、Qwen¥{economics['qwen_650_uniform_cny']:.4f}、双模型+仲裁¥{economics['full_pipeline_uniform_cny']:.4f}；分别是{economics['pipeline_over_v4']:.2f}倍和{economics['pipeline_over_qwen']:.2f}倍。共有检索成本不重复计入，历史失败不计入理想部署，真实失败会增加成本。无候选对照属于实验成本，未计入部署方案。",
        d['cost_judgment'],'## 8. 执行与交审',
        f"本轮新增{s['valid_new_predictions']}条有效预测，HTTP尝试{s['http_attempts']}次，状态{s['http_status_counts']}，账号{s['accounts']}。任务实际usage估算及未知预留合计¥{s['task_cost_or_reserved_cny']:.6f}，总上限¥40，非账单；未重新收费运行旧650基础答案。",
        '逐次请求、原生回执、时间、usage、缓存、失败/未知预留及费用见[尝试台账](analysis_001/attempts.csv)与live目录。价格来源为[硅基流动官方价格页](https://siliconflow.cn/pricing)，实际估算含供应商usage提供的cache及适用时段优惠；部署比较另用统一无优惠价。',
        '断网重放、测试与历史文件保护、精确交审版本见[audit_handoff.md](audit_handoff.md)。001–014历史成果保留；原014待独立审计状态不改为PASS，015也仅为执行者自查完成。']
    text=''
    for i,line in enumerate(lines):text+=line+('\n' if i+1<len(lines) and line.startswith('|') and lines[i+1].startswith('|') else '\n\n')
    target=Path(output) if output else c.OUT/'report.md'
    with target.open('x',encoding='utf-8',newline='\n') as f:f.write(text)

if __name__=='__main__':run()
