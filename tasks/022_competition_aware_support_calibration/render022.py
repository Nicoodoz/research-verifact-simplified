"""Single Chinese main report and optional mechanical statistics appendix."""
from collections import Counter
import common022 as c

NAMES={'B':'同期原structured B','V_raw':'评分原verdict','U0':'U0','U2':'固定U2','G':'学习全局λ','C':'竞争感知双偏置','M':'多类常数偏置','V':'vector scaling','T':'temperature scaling','Always_S':'Always-S诊断'}
def table(head,rows):return '| '+' | '.join(head)+' |\n|'+ '|'.join(['---']*len(head))+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)+'\n'
def render():
    out=c.OUT;data=out/'stageA_002';rows=c.csvrows(data/'core_results.csv');probs=c.csvrows(data/'probability.csv');fits=c.read(data/'fitted_parameters.json');metrics=c.read(data/'metrics.json')
    def core(scope,author='all',methods=c.METHODS):
        own={r['method']:r for r in rows if r['scope']==scope and r['author']==author}
        return table(['方法','正确/N','PA%','MCC','AC1','false-S','NS→S / NA→S'],[[NAMES[a],own[a]['correct']+'/'+own[a]['n'],f"{float(own[a]['PA'])*100:.2f}",f"{float(own[a]['MCC']):.4f}",f"{float(own[a]['AC1']):.4f}",own[a]['false_S'],own[a]['NS_to_S']+' / '+own[a]['NA_to_S']] for a in methods])
    text='''# 022：竞争感知支持边界校准

2026-09-19。**阶段A完成、未过事前门槛，022按停止分支结束；待独立审计。新增API调用0、费用0元。**

## 结论

**保留固定λ=2，不将竞争感知双偏置升级为方法候选。** 新方案减少了false-S，但PA下降超过事前容忍的1个百分点，MCC也没有提高；更关键的是，它在全部2408份折外评分上的最终标签与“学习一个全局λ”逐条完全相同，未证明条件结构有额外分类价值。

因此未启动阿里云阶段B、Qwen扩展或reserved40，不追加正则化搜索、v2/v3或新prompt救结果。不是预算耗尽，也不是未完成收费任务。

## 1. 做了什么，评价边界是什么

沿用户[022任务计划](../../docs/022_竞争感知支持边界校准_任务计划.md)与[结果前登记](protocol_001.md)，读取019的650条R0和020的879条R0，共16名患者、1529个不同valid atomic claims（LLM512、human1017）。020另有879条R1，只用于重复稳定性，不进入拟合。全部1529份冻结API-BGE证据的来源另有哈希清单，没有改检索或切本地BGE。

按不使用GT的固定患者哈希分4折，每折4名患者；每个校准器只用另外12人的R0评分及GT拟合，然后预测留出患者R0和R1。训练每claim权重1，无作者/患者特征、无类别重采样、无内层参数搜索。采用固定正则化的三类NLL和原epsilon/平分规则；不是微调LLM，也不是training-free。

主候选：NS/NA内部竞争权重r决定S偏置`r*bNS+(1-r)*bNA`。仅两个全局参数，不改变NS/NA相对顺序。G/M/V/T分别是全局λ、多类偏置、vector scaling和正温度缩放；所有后处理共享同一条历史评分回答。

这是**已暴露development材料的患者折外筛查**。020患者已参与022动机形成，交叉验证与新调用都不能把他们变回独立确认患者。R0=1529条与R1=879条不是相同队列；下面同时给出同879条的R0。历史评分全部来自硅基流动；本任务没有阿里云性能结论。

## 2. 完整主比较：R0折外1529条

'''+core('R0')+'''
竞争感知相对U2：正确数**−28**，PA **−1.83个百分点**，MCC **−0.0164**；false-S由90降至69（真实非S分母358，25.14%→19.27%）。减少错误支持属实，但分类收益未达标。

002的1000次固定折外预测患者bootstrap：ΔPA 95%区间[−2.78,−1.01]个百分点；ΔMCC [−0.0310,−0.0017]。这是本批开发结果的描述性区间，不包含所有拟合/选择不确定性，不当作最终确认性检验。

## 3. 同879条的两轮结果与患者方向

'''+table(['范围','U2正确 / 竞争感知正确','U2 MCC / 竞争感知MCC','U2 false-S / 竞争感知false-S'],[['020子集R0','718 / 699','0.5960 / 0.5746','47 / 37'],['020子集R1','708 / 695','0.5711 / 0.5679','52 / 33']])+'''
R1相对U2净−13，PA −1.48个百分点，MCC −0.0032；ΔMCC区间[−0.0296,+0.0256]跨0，不据此声称等价。R0同879条净−19，方向同样不支持升级。

患者方面，R0全部16人中**14负、1平、1正**；R1十人中7负、1平、2正。逐一排除任一患者后未能改变原门槛失败，不是由一个坏病例或单个患者决定。相同879条两轮翻转：U2为81条，竞争感知/全局λ均88条；相对U2两轮均救回仅1条、两轮均伤害10条。重复没有提供更稳定的正向信号。

作者分层必须保留：

'''+table(['范围/作者','U2 PA / 竞争感知PA','U2 MCC / 竞争感知MCC','U2 false-S / 竞争感知false-S'],[['R0 / LLM','94.14% / 91.99%','0.1886 / 0.1842','15 / 13'],['R0 / human','78.96% / 77.29%','0.5710 / 0.5601','75 / 56'],['R1 / LLM','95.54% / 94.42%','0.3825 / 0.4197','2 / 1'],['R1 / human','73.93% / 72.30%','0.5331 / 0.5273','50 / 32']])+'''
R1 LLM的MCC点值虽提高，但PA下降、非S仅6条且MCC区间跨0，不能用它替代主比较。完整作者/类别PRF、混淆矩阵、逐患者与区间见[统计附录](statistics.md)。

## 4. 减少false-S，实际交换了什么

R0竞争感知相对U2：**救回10、伤害38**，净−28；移除21个false-S，没有新增false-S或W型错误。移除的21个错误支持中，只有10个变成正确的NS/NA，另外11个仍在NS/NA之间判错，不能把21全部计作救回。

类别正确数为S **1089→1051（−38）**、NS **49→55（+6）**、NA **147→151（+4）**。R1救回6、伤害19；移除19个false-S，但仅6个成为正确非S，仍有13个非S类别错误。三类代价与逐条新/移除false-S标记保存在[转移台账](stageA_002/transitions.csv)。

它得到的是“更少错误支持、更多漏掉真实支持”的权衡，**没有达到本轮要求的权衡改善**，更不能称总体分类性能提高。

## 5. 条件竞争信号是否存在，是否超越普通校准

原U0→U2确有不同竞争结构：R0中U0为NS的改S包含R=121、H=19、W=24；U0为NA的改S为R=8、H=4、W=0。R/H/W分别指救回真S、破坏原正确非S、原已错但进一步变成false-S。这些是描述性分布，不控制S margin、类别比例或患者构成就不能解释成条件因果机制。

本轮保留全部不变样本，并按固定S margin×r联合分箱、作者和患者展示[联合分布](stageA_002/competition_bins.csv)。最关键的外推检验结果是：**双偏置与全局λ在R0、R1均逐条同标签（2408/2408）**；概率数值略有不同，分类结构没有实际增量。

拟合参数如下，没有强制bNS<bNA，所有优化器成功终止且没有边界命中：

'''
    fmap={(f['fold'],f['method']):f for f in fits}
    text+=table(['外层折','全局λ','bNS','bNA'],[[fold,f"{fmap[(fold,'G')]['theta'][0]:.4f}",f"{fmap[(fold,'C')]['theta'][0]:.4f}",f"{fmap[(fold,'C')]['theta'][1]:.4f}"] for fold in range(4)])
    text+='''四折均为bNS>bNA，与“NS竞争强应更谨慎”的动机方向相反；这是NLL与本批生成评分分布下的拟合结果，不能当作医生层面的放宽建议。两参数均低于2，实际表现主要是整体收紧；评分离散性也使参数变化未必改变标签。本轮固定ridge只检验这一个登记实现，不证明所有条件形式永远无效。

普通多类偏置R0比U2多对3条，但false-S多3条、NS正确数下降；R1反而少对1条。vector scaling的概率质量改善明显，但false-S R0/R1为158/86，远高于U2的90/52。**没有依据将普通基线事后换成winner，也没有证据需要保留更复杂的主候选。**

## 6. 概率质量与分类结果分开

模型给的是整数相对信心，不是token logits或已校准概率。NLL、Brier越低越好，Brier为三类平方误差之和；ECE固定10等宽箱，仅辅助。

'''
    own={r['method']:r for r in probs if r['scope']=='R0' and r['author']=='all'}
    text+=table(['R0方法','NLL','Brier','ECE'],[[NAMES[a],f"{float(own[a]['NLL']):.4f}",f"{float(own[a]['Brier']):.4f}",f"{float(own[a]['ECE']):.4f}"] for a in ('U0','U2','G','C','M','V','T')])
    text+='''竞争感知相对U2没有概率质量优势，相对全局λ的NLL略差、Brier略好，不能包装成已验证校准。vector scaling R1的NLL也较低（0.4907，对U2 1.2236），但并未满足本轮分类—错误支持目标。temperature scaling改变概率、不改变U0标签；这是预期性质，不是实现失败。

B/V_raw没有完整概率，不编造NLL。所有方法逐类分箱、空箱及样本数保留于[可靠性表](stageA_002/reliability.csv)；少量NS/NA和高度饱和/零分评分会限制概率解释。

## 7. 停止决定、研究定位与交审

[事前门槛检查](stageA_002/decision.json)为false：C相对U2的PA/MCC不达标、相对学习全局λ没有额外分类价值、患者分布亦不支持。即使忽略本轮补充的实际差异门槛，用户计划原建议的MCC提高和PA损失≤1pp也已失败。**阶段B与可选Qwen均不执行；保留λ=2，不替换core。**

022没有改医生标签、读reserved40病例或修改原prompt、C48、BGE环境；原reason保留，离线新标签不能把旧reason当自洽证据。文献中的后处理校准和标签偏置已有充分背景，见[定向相关工作](related_work.md)：本轮是有监督的轻量应用检验，未证公式首创或跨模型/跨医院泛化。

12项022测试覆盖U2退化、零分/平分、解析梯度、患者隔离、重复权重、共享评分、概率公式与模拟预算恢复；002评价15项测试通过。原始评分与冻结C48哈希、独立乘法解码及断网重放见[复核结果](verification_001/summary.json)。自查不等于独立审计PASS。

收费累计**0/80元**，无阿里云调用、探针、重试或未知预留。因阶段A停止，没有做022账户0731实时可用性或价格实测，不能把任务计划参考价格称已核实当前账单。路由说明已按本任务更新：BGE硅基流动缓存优先，Judge直接阿里云0731，任何后续发送仍须单独满足当前阶段授权和费用登记。

一次OOF写出发生numpy布尔值序列化错误，原stageA_001及代码保留，修复输出类型后写stageA_002；未调整方法或选择规则。详见[执行记录](execution_notes.md)及[审计交接](audit_handoff.md)。
'''
    with (out/'report.md').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    appendix='# 022机器统计附录\n\n唯一必读[中文主报告](report.md)。所有分类指标调用002；混淆矩阵行GT、列预测，S/NS/NA顺序。R1仅020的879条，与R0_020同ID。\n\n'
    for scope in ('R0','R0_020','R1'):
        for author in ('all','llm','human'):
            appendix+=f'## {scope} / {author}\n\n'+core(scope,author)
            for a in c.METHODS:
                m=metrics[f'{scope}/{author}/{a}'];appendix+=f'**{NAMES[a]}**\n\n'+table(['GT / Pred','S','NS','NA'],[[lab,*m['confusion_matrix'][i]] for i,lab in enumerate(('S','NS','NA'))])
    appendix+='完整类别precision/recall/F1与单系统区间：[metrics.json](stageA_002/metrics.json)；配对差值区间：[paired.json](stageA_002/paired.json)；每患者结果：[patients.csv](stageA_002/patients.csv)；固定折外参数：[fitted_parameters.json](stageA_002/fitted_parameters.json)；NLL/Brier/ECE：[probability.csv](stageA_002/probability.csv)。\n'
    with (out/'statistics.md').open('x',encoding='utf-8',newline='\n') as f:f.write(appendix)

if __name__=='__main__':render()
