"""Generate the numerical Chinese synthesis; conclusions remain auditable from tables."""
import common036 as c
def fmt(x,n=4):return 'NA' if x is None or x=='' else f'{float(x):.{n}f}'
def pct(x):return 'NA' if x is None or x=='' else f'{float(x)*100:.2f}'
def main():
    root=c.OUT;f=root/'analysis_001/R0';m=c.read(f/'metrics.json');pairs=c.read(f/'paired.json');dirs={r['comparison']:r for r in c.read(f/'directions.json')};cost=c.read(root/'accounting_002/summary.json');den=c.read(f/'denominators.json');cfg=c.read(root/'final_freeze_001/config.json')
    risk={r['method']:r for r in c.csvread(f/'risk_rescue.csv') if r['scope']=='all'};get=lambda x:m['all/'+x];u0=get('U0');u2=get('U2');g=get('Gate_A');t=get('U2_T');rr=risk['U2'];gr=risk['Gate_A'];N=den['paired_n']
    methods=['O','B','Score_verdict','U0','U2','U2_T','Gate_A','Std_T','Std_G','Std_M','Std_V','Joint_NLL','Task_T','Robust_T','MCC_T','U4']
    composition='|子组|N|GT S|GT NS|GT NA|Always-S的PA%|Always-S的false-S|\n|---|---:|---:|---:|---:|---:|---:|\n'
    for scope in ('all','human','llm'):
        v=m[scope+'/U0'];counts=[v['per_class'][label]['support'] for label in c.LABELS]
        composition+=f"|{scope}|{v['n']}|{counts[0]}|{counts[1]}|{counts[2]}|{100*counts[0]/v['n']:.2f}|{counts[1]+counts[2]}|\n"
    predictions=c.csvread(f/'predictions.csv');class_transfers=[]
    for scope in ('all','human','llm'):
        for gt in c.LABELS:
            for before in c.LABELS[1:]:
                selected=[r for r in predictions if (scope=='all' or r['author']==scope) and r['GT']==gt and r['U0']==before and r['U2']=='Supported']
                kept=sum(r['Gate_A']=='Supported' for r in selected);kind='R' if gt=='Supported' else 'H' if gt==before else 'W'
                class_transfers.append(dict(scope=scope,GT=gt,U0=before,kind=kind,U2_n=len(selected),Gate_kept_S=kept,Gate_blocked=len(selected)-kept))
    c.csvwrite(root/'error_transfer_by_class.csv',class_transfers)
    transfer_table='|GT|原U0|类型|U2改为S|Gate保留S|Gate挡回|\n|---|---|---|---:|---:|---:|\n'
    for v in class_transfers:
        if v['scope']=='all':transfer_table+=f"|{v['GT']}|{v['U0']}|{v['kind']}|{v['U2_n']}|{v['Gate_kept_S']}|{v['Gate_blocked']}|\n"
    def table(scope,names):
        text='|方法|correct/N|PA%|MCC|AC1|false-S|S recall%|NS recall%|NA recall%|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
        for name in names:
            v=m[scope+'/'+name];text+=f"|{name}|{v['correct']}/{v['n']}|{pct(v['PA'])}|{fmt(v['MCC'])}|{fmt(v['AC1'])}|{v['false_S']}|{pct(v['S_recall'])}|{pct(v['NS_recall'])}|{pct(v['NA_recall'])}|\n"
        return text
    def pairtext(new,base):
        p=pairs['all/'+new+'-vs-'+base]['metrics'];v=p['percent_agreement'];w=p['mcc']
        return f"{new}−{base}：ΔPA {v['delta']*100:+.2f}百分点，95%患者区间[{v['ci95'][0]*100:+.2f},{v['ci95'][1]*100:+.2f}]；ΔMCC {w['delta']:+.4f}，区间[{w['ci95'][0]:+.4f},{w['ci95'][1]:+.4f}]。"
    pa=pairs['all/U2-vs-U0']['metrics']['percent_agreement'];mc=pairs['all/U2-vs-U0']['metrics']['mcc']
    support='PA和MCC的总体提升均有患者配对区间支持' if pa['ci95'][0]>0 and mc['ci95'][0]>0 else '总体点估计与区间需分别看待，不能宣布PA/MCC均得到明确提升'
    gatedesc=('它以部分正确数换取更少错误支持，只能作为风险折中点，不能称无损增益' if g['false_S']<u2['false_S'] else '本次没有降低总错误支持，不支持将其作为默认增益模块') if g['correct']<u2['correct'] else '应按本次固定工作点的风险/性能和配对区间判断价值，不据此重选阈值'
    probability_direction='、'.join(k+('下降' if t[k]<u2[k] else '上升' if t[k]>u2[k] else '不变') for k in ('NLL','Brier','ECE10'))
    prob='|方法|NLL↓|Brier↓|ECE10↓|\n|---|---:|---:|---:|\n'
    for name in methods:
        v=get(name)
        if 'NLL' in v:prob+=f"|{name}|{fmt(v['NLL'])}|{fmt(v['Brier'])}|{fmt(v['ECE10'])}|\n"
    direction='|比较|正/负/持平患者|净正确|去掉任一患者后的净正确范围|\n|---|---:|---:|---:|\n'
    for new,base in cfg['primary_pairs']:
        v=dirs[new+'-vs-'+base];direction+=f"|{new}−{base}|{v['positive']}/{v['negative']}/{v['tied']}|{v['net']:+d}|[{v['leave_one_out_min_net']:+d},{v['leave_one_out_max_net']:+d}]|\n"
    development=[r for r in c.csvread(root/'development_001/all_metrics.csv') if r['dataset']=='main40' and r['scope']=='all'];devtable='|方法|正确/3675|PA%|MCC|false-S|NLL|Brier|\n|---|---:|---:|---:|---:|---:|---:|\n'
    for v in development:devtable+=f"|{v['method']}|{v['correct']}|{pct(v['PA'])}|{fmt(v['MCC'])}|{v['false_S']}|{fmt(v['NLL'])}|{fmt(v['Brier'])}|\n"
    repeats=c.csvread(root/'analysis_001/repeat_stability.csv');repeattext='|方法|同ID N|R0正确|R1正确|标签变化|\n|---|---:|---:|---:|---:|\n'
    for v in repeats:
        if v['method'] in ['B','U0','U2','U2_T','Gate_A','Std_M','Std_V','Joint_NLL']:repeattext+=f"|{v['method']}|{v['n']}|{v['correct_R0']}|{v['correct_R1']}|{v['label_flips']}|\n"
    r1=c.read(root/'analysis_001/R1/metrics.json');q0=c.read(root/'analysis_001/R0_repeat_subset/metrics.json')
    repeated_delta=lambda metrics,new,base:metrics['all/'+new]['correct']-metrics['all/'+base]['correct']
    lossR=int(rr['R'])-int(gr['R']);restoredH=int(rr['H'])-int(gr['H']);preventedW=int(rr['W'])-int(gr['W'])
    text=f'''# 036：标准对照、reserved40最终验证与论文实验收尾

## 一、先回答研究结论

本轮冻结后评价全部40名reserved患者、3573条valid atomic claims；共同有效主分析为{N}条，覆盖{den['paired_patients']}名患者。没有用reserved重新拟合、选择患者、改prompt或调λ。所有方法在GT连接前封存预测。

1. **U2相对同次评分U0净增{u2['correct']-u0['correct']:+d}条正确**（PA {pct(u0['PA'])}%→{pct(u2['PA'])}%，MCC {fmt(u0['MCC'])}→{fmt(u2['MCC'])}）；{support}。它救回真S {rr['R']}条、误伤原正确non-S {rr['H']}条，并把原本已错的non-S {rr['W']}条转为错误S。总false-S {u0['false_S']}→{u2['false_S']}。收益与风险必须同时报告。
2. **A Gate相对U2净正确{g['correct']-u2['correct']:+d}、总false-S {g['false_S']-u2['false_S']:+d}**。保留{gr['R']}/{rr['R']}真S救回（{pct(gr['rescue_retention'])}%），阻止H {restoredH}、W {preventedW}条，同时挡掉R {lossR}条。{gatedesc}。80%只是训练内目标，不是最终测试保证或临床安全线。
3. **温度不改变任何U2标签**。NLL {fmt(u2['NLL'])}→{fmt(t['NLL'])}，Brier {fmt(u2['Brier'])}→{fmt(t['Brier'])}，ECE10 {fmt(u2['ECE10'])}→{fmt(t['ECE10'])}，即{probability_direction}。这些量各有定义，不能用NLL改善代替“全面校准成功”。
4. **U2有效，但不是总体成绩最好的后处理。** 多类常数偏置Std_M为2999/3571、PA 83.98%、MCC 0.5850，较U2多91正确、也多47条false-S。Vector scaling为3004/3571、PA 84.12%、MCC 0.5850，但NS召回仅10.55%，不能把最高总分称为全面更优。论文主结果应呈现“固定边界的组件增量＋标准监督对照＋类别/风险代价”，不能以“新λ2方法优于经典校准或已全面超过原VeriFact”为主张。
5. **可以结束本轮实验开发并进入写作**。必要标准对照、最终队列和预设重复已执行；复杂Gate/特征路线不再追加。当前剩余事项是独立审计与论文陈述核对，不是以reserved结果为依据追加优化。执行者自检与独立审计分开，036尚未独立审计。

## 二、主结果：一次评分共享所有后处理

PA为正确比例；MCC考虑类别混淆与不平衡；AC1为一致性指标。false-S是真实NS/NA被报Supported的数量。类别召回是该真实类别被识别正确的比例。

{table('all',methods)}

原VeriFact O使用作者发布系统结果。B是同期普通structured判断；Score_verdict是同次评分回答自带的原verdict；U0是同次label_scores的argmax，三者不能混同。U2_T、Task_T和Robust_T若标签相同，是固定参数/定义的结果，不能作为三次独立复现。U4是预先登记的Joint标签核对参照。

### 主要配对比较

{chr(10).join('- '+pairtext(new,base) for new,base in cfg['primary_pairs'])}

1000次患者cluster bootstrap，固定预测重抽患者，seed0..999；不能把claim当独立患者。以上是预设主比较，标准方法比较及两作者区间全部保存，存在多重比较，不从未校正的漂亮区间挑结论。区间跨0不等于等效。

**最强的确认结论是U0→U2的组件增量。** 相对同期B，PA提升得到支持，但MCC区间跨0，且false-S多114条；相对原VeriFact，PA/MCC虽点值更高，两个区间都跨0，因此尚不能宣布显著超越原系统。原系统还包含不同检索、模型与运行时间条件。

标准对照相对U2：Std_M的ΔPA +2.55百分点[+1.76,+3.30]、ΔMCC +0.0330[+0.0157,+0.0487]；Std_V的ΔPA +2.69百分点[+1.52,+3.70]、ΔMCC +0.0330[+0.0088,+0.0552]。这些预设辅助比较显示它们确有竞争力；相应false-S增加47/50条，不能省略。全部配对数值集中在`paired_statistics.csv`。

### 作者与类别

共同有效队列的类别背景如下。Always-S是“所有陈述都报Supported”的退化诊断，其PA就是S占比，MCC按002约定为0；不是新拟合方法或可取的临床策略。

{composition}

Human：

{table('human',['O','B','U0','U2','Gate_A','Std_M','Std_V'])}

LLM：

{table('llm',['O','B','U0','U2','Gate_A','Std_M','Std_V'])}

LLM类别偏Supported时PA很容易受多数类驱动，因此同时保留MCC、NS/NA召回和完整混淆矩阵。所有类别support、precision、recall及矩阵见`analysis_001/R0/metrics.json`，不能只摘取Supported召回。

U2较U0在human/LLM分别净增115/62正确，两作者PA区间均正；human MCC差+0.0179的区间为[+0.0032,+0.0309]，LLM MCC差+0.0132的区间为[−0.0664,+0.0822]，后者没有明确确认。Gate的63条false-S减少中，61条来自human；LLM只减少2条false-S，却损失10条正确，LLM PA差的区间也为负。因此不支持把同一个Gate当成两作者通用的默认性能提升模块，也不据此再拟合作者专属Gate。

Vector scaling将NS召回从U2的50.55%降至10.55%，换来NA召回53.53%→73.40%；多类偏置的对应值为NS 37.45%、NA 61.25%。这说明连PA/MCC同时较高也可能掩盖少数类别严重损失。U2可以作为保留较多NS识别的固定折中点，但没有预设临床效用权重，不能把它称为已经证明的“最优平衡”。

    Std_V相对Std_M仅多5条正确、MCC几乎相同，背后却是NS正确数103→29、NA正确数373→447（各差74，互相抵消），S正确数2523→2528。这是不同类别之间的取舍，不是所有类别一起进步；每类precision/F1与完整混淆矩阵见`class_performance.csv`、`confusion_matrices.csv`。

## 三、错误转移与患者异质性

R/H/W仅定义在原U2候选：R是真S救回；H是U0本来正确的non-S被λ改错；W是U0已错的non-S又变S。**净正确=R−H；新增false-S=H+W。**二者不能混用。

U2候选{rr['candidate_n']}条，其中R={rr['R']}、H={rr['H']}、W={rr['W']}。Gate通过后R={gr['R']}、H={gr['H']}、W={gr['W']}。Gate少报的错误S不全转化成正确：阻止W只是退回原本错误的NS/NA；阻止H才恢复正确，误挡R会损失正确。

{transfer_table}

这里“挡回”在R行是误伤，在H行是修错，在W行只表示减少错误支持；原U0已报S的错误不属于候选，Gate不会处理。两作者同样的细分表见`error_transfer_by_class.csv`。

{direction}

“去掉任一患者”只是集中性诊断，没有重新训练、改阈值或删患者报告。逐条fix/harm、错误S增减及ID已完整写入`transitions.csv`；本轮不把模型reason当因果机制，不新标医学gold。

## 四、概率输出：温度、边界与自由度分开

NLL是真实类负对数概率；Brier是三类平方误差之和；ECE10是10个等宽桶的最大类置信度差。均越低越好，但衡量不同方面。模型声明score经floor/log/softmax得到这些概率，不是原生token概率。

{prob}

U2_T的ΔNLL为−0.5762，95%患者区间[−0.6971,−0.4711]，改善明确；ΔBrier为+0.0010，区间[−0.0078,+0.0098]，不能认定改善，也不能认定已经确证恶化或等效。ECE10是点值下降，不据分箱曲线宣称全面校准。Std_V的概率指标更低，但它同时改变分类标签和类别取舍，不能视为“保持U2标签的更好温度”。

Std_T只有置信度尺度，分类标签与U0一致。U2_T只改变已移边界后的置信度。Std_G、Std_M可改变边界；Std_V同时有尺度和偏置自由度。Joint_NLL在development命中λ=4上界，开发七个数据视图、最终R0及R1均与U4逐条标签完全一致（不是仅正确数相同，见`final_label_equivalence.csv`），温度部分继续改变概率；不继续扩大λ范围，不把命中上界解释为找到了理论最优。各标准方法还保留原正则和约束，不能将全部差异简单归因于参数数量。

可靠性图和分箱人数见Figure4及机器表；`probability_breakdown.csv`按U2正确/错误、真实类score为0分解。没有人工复核效用或临床安全实验，不能据NLL变化推导这些应用收益。原评分reason未随U2/Gate标签重写，是应用解释一致性的限制。没有新增passage-level evidence gold，标签改对也不等于已逐条验证C48支持充分或引用正确；判定性能结论不能直接扩展为证据忠实性已验证。

## 五、预设重复

重复患者为{', '.join(cfg['repeat_patients'])}，共444条，按ID哈希在任何正式结果前确定。6人方案保守估算超过150元，按已登记的预算规则选4人。以下是同一444条的独立调用，不是新增444条独立测试样本。

{repeattext}

同一重复子集U2−U0净正确：R0 {repeated_delta(q0,'U2','U0'):+d}，R1 {repeated_delta(r1,'U2','U0'):+d}；Gate−U2：R0 {repeated_delta(q0,'Gate_A','U2'):+d}，R1 {repeated_delta(r1,'Gate_A','U2'):+d}。两轮分别保存所有指标、区间和患者方向。4名患者的重复仅诊断运行波动，不能保证所有40名的多轮稳定性。

## 六、development对照与历史证据如何串联

新增标准方法复用035相同评分、同四折、同患者隔离；不使用reserved做标准方法拟合。Main40 development OOF结果如下，其他原R0/R1及跨Judge视图都保存：

{devtable}

多类常数偏置与Vector scaling有竞争力，故在reserved完整保留，未为突出U2而删对照。它们使用医生标签拟合；固定U2来自先前开发阶段决定，不能写成完全未接触标签的先验常数。

研究链条可写为：早期检索/证据重组与复杂解释并未稳定改善→发现评分判定存在Supported边界取舍→固定简单修正跨开发患者、重复和服务条件检查→对额外信息Gate做开发与迁移，保留风险控制但拒绝复杂路线的过度结论→补足标准后处理→冻结后reserved最终评价。019最初保护门槛失败、λ2为事后开发信号；020以冻结方式继续确认；023说明局部平台但不证明全局最优。025的Gate OOF信号、026的迁移减弱与031追加信息未确认，均保留为方法边界，而非删掉的失败。

**写作定位需要随证据收束。** 036不支持把论文写成“固定λ2是一种优于标准校准的新最强算法”。更可辩护的是临床核验中决策边界、置信度和风险控制的实证研究：简单偏置确有可重复组件收益，学习的标准偏置/尺度有更高总分，同时暴露false-S和少数类别代价。这个定位不要求继续开发新方法，也不将标准方法本身的通用思想宣称首创。

**035勘误：**“跨Judge所有方法标签不变”不适用于探索性MCC_T。既有勘误记录DS→Q 45/879标签变化、净+7；Q→DS 36/879变化、净+1。U2_T/Task_T/Robust_T/Joint_NLL对应迁移没有标签变化。原报告和独立审计保留，036采用修正后的表述。

## 七、覆盖、费用、复现与审计

冻结N=3573，主分析共同有效N={N}；逐方法missing ID与全冻结分母missing-as-error PA见`coverage.csv`。所有40人完整进入计划，不静默删除失败；Qwen缺失候选按事前规则退回U0；主评分缺失则显式标为不可构造U0。HTTP200不为答案或非核心格式重跑。

具体为R0的1条B响应出现冲突的重复verdict（`e9978999-0aa6-9da2-2a88-be59c23726e9`），1条评分缺少label_scores（`acec553e-a8a2-a3a2-1c75-377db23fc4d6`）。两条均在人写组，保留原始200回执并标invalid；R1的444条和Qwen候选评分均完整。158条非核心格式异常回答保留有效核心字段。全N missing-as-error下U2 PA为81.39%、U0为76.43%，净正确增量仍177条；没有重跑无效200来补分母。

API累计估算及未知预留 **¥{cost['total_used_or_reserved_cny']:.6f}/150**，其中未知预留¥{cost['unknown_reserved_cny']:.6f}；全部尝试{cost['all_attempts']}，收到HTTP200 {cost['terminal_HTTP200']}。按公开峰值无缓存usage估算，未逐笔核销供应商账单。BGE硅基流动、Judge阿里云；原始回执、请求、usage、异常都保留，没有重试。单独运行R0的BGE+评分约46.75元，加入342次Qwen后约52.76元（多6.01元，约12.9%）；Gate费用增加不大，但22条净正确损失和作者差异使其不适合作默认准确率模块。需要更低false-S时可把该固定结果作为风险折中参考，本轮不证明临床成本收益。

正式费用入口为`accounting_002`：初版001的费用一直正确，但rerank token列未读取供应商meta而显示0，002已逐条回执修正为36,731,639个输入tokens；原001、回执和所有预测/指标保留不变。推理费用按本队列摊销，不包括既往研发/监督材料采集、自由文本切分或本地硬件成本。不同后处理共享一次评分，不能把方法数当调用次数。

环境为`research-verifact-029`，统一`scripts/run_research.ps1`；无主环境或历史文件修改。执行者自检覆盖冻结参数、原始回执、全部预测、002指标、配对bootstrap和R/H/W恒等关系，独立审计仍待进行。完整入口见任务README、`methods_and_settings.md`与`audit_handoff.md`。

## 图表与写作入口

- [Figure1](figures_002/figure1_performance_risk.svg)：总体PA/MCC/false-S，包含有竞争力的标准方法。
- [Figure2](figures_002/figure2_class_recall.svg)：总体/human/LLM三类别召回，包含Vector scaling的NS代价。
- [Figure3](figures_002/figure3_patient_deltas.svg)：U2和Gate逐患者正确数变化。
- [Figure4](figures_002/figure4_reliability.svg)：U2、U2_T与Vector scaling的三类可靠性。
- [Figure5](figures_002/figure5_risk_rescue.svg)：固定U2候选上的R与新增false-S工作点。
- `paper_tables.md`：总体、作者、概率、配对统计和重复的论文表格源。
- `paper_handoff.md`：研究主张、证据对应和建议章节结构。

![总体性能与错误支持](figures_002/figure1_performance_risk.png)

![三类别召回与标准方法代价](figures_002/figure2_class_recall.png)

完成后停止；reserved已消费，不能重新作为开发选择集。后续只做独立审计和写作，不自动037或任何优化。
'''
    c.write_text(root/'report.md',text)
    c.write_text(root/'paper_tables.md','# 论文核心表格源\n\n## 最终测试\n\n'+table('all',methods)+'\n## Human\n\n'+table('human',methods)+'\n## LLM\n\n'+table('llm',methods)+'\n## 概率\n\n'+prob+'\n## 患者方向\n\n'+direction+'\n## 重复\n\n'+repeattext+'\n## Development OOF\n\n'+devtable)
    handoff=f'''# 论文写作交接稿

## 研究问题与最终方法

给定患者EHR，如何在临床一致性核验中修正Supported判定边界，并明确由此产生的false-S风险？以固定C48与scoring Judge为基础，比较U0、固定λ2的U2、保持标签的U2+T及候选触发A Gate。重点是边界、置信度和风险控制三种作用的分离；不声称后处理/温度/Logistic本身首创。

最终参数已在reserved评分前冻结，见`final_freeze_001`。标准温度、单偏置、多类偏置和Vector scaling完整保留，不以突出U2为目的省略有竞争力的对照。

最重要的定稿边界：U2不是本次最高总分方法。Std_M较U2多91正确、也多47条false-S；Std_V多96正确、多50条false-S，且NS召回只有10.55%。应写成边界/置信度/风险权衡的临床核验实证研究，不能写成“新λ2算法全面优于经典校准”。本轮没有在看到reserved后重新选择部署参数。

## 支撑主结论的证据

1. 同次评分U0→U2：{u0['correct']}→{u2['correct']}/{N}，MCC {fmt(u0['MCC'])}→{fmt(u2['MCC'])}，false-S {u0['false_S']}→{u2['false_S']}；主表、Figure1/2、paired.json。
2. 风险代价：R={rr['R']}、H={rr['H']}、W={rr['W']}；逐条转移、Figure3/5和患者方向说明收益是否集中。不能只报净正确。
3. Gate：相对U2正确数{g['correct']-u2['correct']:+d}、false-S {g['false_S']-u2['false_S']:+d}，保留率{pct(gr['rescue_retention'])}%；61/63的false-S减少来自human，LLM丢10正确只换回2条false-S。保留作风险控制辅助结果，不推荐为两作者通用的默认准确率模块，不再按作者救Gate。
4. 温度：标签不变，NLL {fmt(u2['NLL'])}→{fmt(t['NLL'])}、Brier {fmt(u2['Brier'])}→{fmt(t['Brier'])}；概率表、Figure4。分别叙述，不写成全面校准或临床安全。
5. 标准后处理：以完整development OOF和reserved表说明边界、尺度和参数自由度，U4逐条核对解释Joint上界。Std_M/Std_V的总体提升有配对区间支持，必须与NS损失/false-S一起呈现。监督标准方法与固定U2训练依赖不同，固定2也受过开发选择，不能称完全未使用标签。
6. 重复/迁移：本轮4人444条双轮作为运行波动；历史020/024跨轮跨Judge作为开发辅助。重复claim不增加独立患者数，035 MCC_T迁移按勘误表述。

## 历史负结果的定位

早期检索/packing/解释改造不稳定，引出边界研究；026冻结Gate迁移减弱、028硬语义核查误伤、029/030联合信息OOF信号与031确认失败说明复杂信息并非稳定收益。033未发现优于全development覆盖的稳定subset，故A Gate复用全40训练。不要按任务编号写成实验流水账，不把审计PASS当方法成功。

## 结论边界

这是一个临床核验benchmark上的最终患者隔离评价，不是外部医院验证；所有原始标签由数据集提供，没有新增医生gold。U2相对原VeriFact的PA/MCC区间均跨0，尚不能宣称显著超越原系统；相对同期B只有PA提升明确、MCC不确定。原系统比较同时涉及不同检索、Judge和运行时间。声明score不是模型原生概率，原reason不随离线标签更新，没有passage-level evidence gold来逐条证明改判的证据充分性。API模型实验不支持本地部署/显存/速度结论。16/16返回λ2不证明理论最优。reserved结果不再用于开发。

## 建议论文结构

1. Introduction：临床陈述核验和“支持不足/错误支持”的实际权衡，提出实证问题。
2. Related Work：EHR事实核验、Judge评分/后处理校准、双Judge风险筛选；新意限于本任务证据链，不抢通用方法首创。
3. Methods：固定C48、B与scoring、U0/U2公式、温度、候选Gate及训练规则、标准对照。
4. Experimental Setup：冻结患者分组、development选择与reserved隔离、模型快照、缺失和费用、002统一评价及患者bootstrap。
5. Results：主表先给全部标准对照；再边界R/H/W、患者/作者/类别、Gate成本权衡、概率可靠性和重复。
6. Discussion/Limits：复杂方案负结果、服务/类别依赖、错误支持成本、解释未同步、单数据来源与临床应用限制。
7. Conclusion：按最终数据强度总结固定边界的实际收益和代价，不宣称所有模块成功。

## 是否还有实质缺口

必要数值实验和公平标准对照已齐，可以写Methods、Experiments和Results。尚须独立审计确认代码/统计，正式写作时完成原论文与通用校准方法文献核对；这些不需要重新开发模型。若主比较区间或子组不支持提升，照实保留，不能为论文再调reserved。执行者自检不是独立审计，本次按用户授权先推送。

若论文必须以“优于通用标准的新算法”为中心，现有036结果不足以支撑该主张；这属于贡献定位/新颖性边界，不应靠继续调整已消费的reserved来解决。推荐当前实证研究定位，停止实验开发后与导师讨论写作主张。
'''
    c.write_text(root/'paper_handoff.md',handoff)
    print('036 Chinese synthesis, paper tables and writing handoff generated; inspect before release.')
if __name__=='__main__':main()
