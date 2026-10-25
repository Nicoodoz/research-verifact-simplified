"""Write 037 report and figures from frozen numerical results; no refitting."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import core037 as c
R=c.OUT/'run_001';F=c.OUT/'figures_001';F.mkdir(exist_ok=True)
metrics=pd.read_csv(R/'main40/metrics.csv');allm=metrics.query("scope=='all'").set_index('method')
pairs=c.readj(R/'main40/paired.json');trans=pd.read_csv(R/'main40/transitions.csv').query("scope=='all'").set_index('method')
old=pd.read_csv(R/'old_R1/metrics.csv').query("scope=='all'").set_index('method')
conf=c.readj(R/'main40/score_conflicts.json')
labels={'U0':'U0','U2':'U2','Std_M':'Std_M：多类偏置','Std_V':'Std_V：Vector scaling','VM_switch':'V/M固定切换','Ratio_restore':'NS/NA单阈值','Logistic_restore':'四维Logistic修复'}
def table(frame):
    lines=['| 方法 | 正确/N | PA | MCC | false-S | NS召回 | NA召回 | NS精确率 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for method in c.METHODS:
        x=frame.loc[method]
        lines.append(f"| {labels[method]} | {int(x.correct)}/{int(x.n)} | {x.PA:.2%} | {x.MCC:.4f} | {int(x.false_S)} | {x.NS_recall:.2%} | {x.NA_recall:.2%} | {x.NS_precision:.2%} |")
    return lines
p=pairs['all/VM_switch-vs-Std_V']
lines=['# 037：固定Supported集合的NS/NA决策研究','',
'## 核心结论','',
'**可以缓解Vector scaling的低NS召回，但没有得到全面占优的新模型。最简单的V/M切换已经完成主要恢复；单阈值和小型Logistic没有稳定额外增量。**','',
'本任务仅使用40名development、3675条的四折患者外预测。037在036结果之后提出，是探索性扩展；未读取或重新评价036的reserved逐例数据，没有新增API。以下数值不是新的reserved测试成绩。','',
'## 1. 方法和评价对象','']
lines += [
'先逐折在另外30名患者上拟合原022的Std_V和Std_M，保持其正则、边界和优化器。新增方法只允许Std_V原NA变NS，保持原S与原NS。',
'V/M固定切换：V=NA且M=NS时改NS，否则保持V。NS/NA单阈值：在V原NA中按q_NS/(q_NS+q_NA)排序。Logistic：四个已有score特征拟合NS/NA，不读文本、不调用第二Judge。',
'阈值在严格内层患者预测上确定：NS检出数达到同批V/M切换的水平后，最大化完整训练侧正确数。Logistic元特征还有一层患者交叉拟合，排除通过校准器间接看到验证标签。',
'原V误拒的真实S没有重标为NA，仍保留在全部系统评价中。没有筛选患者、添加特征或根据外层结果改配置。设置详见tasks/037_ns_na_decision/protocol.md。','',
'## 2. Development患者外主结果','']
lines += table(allm)
lines += ['',
f"最简单的V/M切换较Std_V多判对{int(allm.loc['VM_switch','correct']-allm.loc['Std_V','correct'])}条；PA增加{100*p['metrics']['percent_agreement']['delta']:.3f}个百分点，95%患者区间[{100*p['metrics']['percent_agreement']['ci95'][0]:+.3f},{100*p['metrics']['percent_agreement']['ci95'][1]:+.3f}]；MCC差{p['metrics']['mcc']['delta']:+.4f}，区间[{p['metrics']['mcc']['ci95'][0]:+.4f},{p['metrics']['mcc']['ci95'][1]:+.4f}]。两区间跨0，不宣称已确认总体性能提升。",
f"NS召回由{allm.loc['Std_V','NS_recall']:.2%}升至{allm.loc['VM_switch','NS_recall']:.2%}，差值95%区间[{100*p['extra']['NS_recall']['ci95'][0]:+.2f},{100*p['extra']['NS_recall']['ci95'][1]:+.2f}]个百分点；NA召回从{allm.loc['Std_V','NA_recall']:.2%}降至{allm.loc['VM_switch','NA_recall']:.2%}。这是明确的类别交换，不是无损修复。",
'三种修复的Supported预测集合逐条不变，false-S都为237。它们不会处理原V已经错放为S的样本。','',
'## 3. 到底救回和误伤了什么','',
'| 修复 | NA→NS总数 | 救回真实NS | 误伤真实NA | 真实S仍错 | 净正确变化 |','|---|---:|---:|---:|---:|---:|']
for method in c.REPAIRS:
    x=trans.loc[method]
    lines.append(f"| {labels[method]} | {int(x.changed)} | {int(x.NS_rescued)} | {int(x.NA_harmed)} | {int(x.S_wrong_still_wrong)} | {int(x.delta_correct):+d} |")
lines += ['',
'净正确变化=救回NS−误伤NA；真实S原来被V报NA，改NS后仍错。不能把所有修改都计作NS有效恢复。',
'固定切换与Logistic在main40的3675条以及old_R1的879条上逐条标签完全一致，不只是汇总指标一样。单阈值较切换多识别2条NS，但多损失3条NA，净少1正确。没有证据支持额外保留这个Logistic模型。','',
'## 4. 与标准M的关系及概率输出','',
'固定切换的标签表现几乎就是Std_M：main40比M少1正确、NS检出相同、false-S多1。它不是明显超过M的新分类器。其差别是基础三类概率仍保留Std_V，而不是改为M的概率。',
f"Std_V及三种修复均保留基础概率NLL={allm.loc['Std_V','NLL']:.4f}、Brier={allm.loc['Std_V','Brier']:.4f}。这由概率未修改直接保证，不是三次校准成功。",
'修复标签可能不再等于概率argmax；V的最大类概率不能冒充新标签的可信度。不额外声称人工复核或临床安全收益。','',
'## 5. Human/LLM分层','']
for scope in ('human','llm'):
    lines += ['### '+scope,'']+table(metrics.query('scope==@scope').set_index('method'))+['']
lines += ['## 6. 旧R1评分敏感性','',
'把同一套main40各外层训练模型应用于旧R1对应留出患者，879条；不重新拟合，也不是新患者或新API重复。它诊断不同历史评分条件下的规则变化。','']+table(old)+['',
'旧R1固定切换较V多2正确；单阈值反而比V少3。Logistic仍与固定切换完全同标签。此辅助结果不支持继续追求阈值或分类器复杂化。','',
'## 7. 排序信息与能力上限','',
f"main40保留S集合后，全部可触及真实NS只占{conf['V_nonS_NS_recall_ceiling']:.2%}。即使第二步完美，也不能救回V已判S的NS；237条false-S全部遗留。",
f"按外层折和原始score分组，V的NA区域有{conf['V_NA_score_cells']}种score单元，其中{conf['mixed_NS_NA_cells']}种同时出现真实NS与NA。相同score经本方案任何确定性变换仍相同，说明仅靠这些评分不能把每个个体区分开。",
'仅在V原NA且真实NS/NA的504条上，原NS/NA概率比的AUC为0.7062，小Logistic为0.6544。这个条件化排序诊断不支持认为Logistic增加了更好的区分信息，不能把它推广为全队列AUC。',
'同NS检出数下的GT知情阈值混合包络仅作描述，不用于选正式阈值，也不是可部署分数。所有曲线、同分冲突和原ID保存在run_001/main40/。','',
'## 8. 结论与停止','',
'建议保留V/M固定切换作为一个极简探索性扩展：保留V的概率表达和S判定，以M提供的NS/NA分歧恢复NS。它完成了原问题中的“不要让NS几乎消失”，但付出NA召回代价，未消除错误支持，也未优于M形成新的总体分类优势。',
'不推荐继续训练更大的NS/NA分类器，不追加第二Judge、NLI或作者专属分支。037只能补充论文的类别决策与概率表达分离分析；不能把它回填成036事前冻结的最终方法。',
'10项合成测试和执行者科学核验通过；核验包括各级患者隔离、阈值重选、参数逐条重放、原基线复现和患者配对区间。独立审计待进行。','',
'0 API、0费用；未重跑或改写001—036；未使用reserved做新预测；未提交/推送，不自动038。','',
'## 图表和复现','',
'![开发队列NS/NA折中](figures_001/ns_na_tradeoff.png)','',
'![修复后的NS召回](figures_001/ns_recall.png)','',
'运行和核验见tasks/037_ns_na_decision/README.md；原始机读表、患者结果、候选阈值和嵌套模型在run_001。']
(c.OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
fig,ax=plt.subplots(figsize=(8,5))
for method,short,offset in [('Std_V','Vector scaling',(8,5)),('VM_switch','V/M switch = Logistic',(8,12)),('Ratio_restore','Ratio threshold',(8,-22))]:
    x=allm.loc[method];ax.scatter(100*x.NS_recall,100*x.NA_recall,s=65)
    ax.annotate(short,(100*x.NS_recall,100*x.NA_recall),xytext=offset,textcoords='offset points')
ax.set(xlabel='NS recall (%)',ylabel='NA recall (%)',title='Development: NS recovery exchanges NA recall',xlim=(4,58),ylim=(52,77))
ax.grid(alpha=.25);fig.tight_layout();fig.savefig(F/'ns_na_tradeoff.png',dpi=220);fig.savefig(F/'ns_na_tradeoff.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(8,5))
ms=['Std_V','VM_switch','Ratio_restore','Std_M'];vals=[100*allm.loc[m,'NS_recall'] for m in ms]
bars=ax.bar(['Vector scaling','V/M switch','Ratio threshold','Multiclass bias'],vals)
ax.bar_label(bars,labels=[f'{v:.2f}%' for v in vals],padding=4)
ax.set(ylabel='NS recall (%)',title='Development: recovering the suppressed NS class',ylim=(0,50))
fig.tight_layout();fig.savefig(F/'ns_recall.png',dpi=220);fig.savefig(F/'ns_recall.svg');plt.close(fig)
params=[]
for f in range(4):
    meta=c.readj(R/f'fits/fold{f}.json')
    params.append(dict(fold=f,ratio_threshold=meta['ratio_selection']['selected']['threshold'],
        logistic_threshold=meta['lr_selection']['selected']['threshold'],inner_target_NS_tp=meta['ratio_selection']['target_NS_tp'],
        ratio_inner_correct=meta['ratio_selection']['selected']['correct'],logistic_inner_correct=meta['lr_selection']['selected']['correct']))
pd.DataFrame(params).to_csv(c.OUT/'parameter_summary.csv',index=False)
c.put(c.OUT/'report_manifest.json',dict(created_utc=c.now(),source_run='run_001',files={
    p.relative_to(c.OUT).as_posix():c.sha(p) for p in [c.OUT/'report.md',c.OUT/'parameter_summary.csv',*F.iterdir()]}))
print('037 report and figures complete',flush=True)
