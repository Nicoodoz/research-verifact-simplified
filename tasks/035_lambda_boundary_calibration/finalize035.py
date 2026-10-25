"""Finalize task 035 report, parameter table and figures from frozen outputs."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/035_lambda_boundary_calibration'
R1=OUT/'run_001';R2=OUT/'run_002'
FIG=OUT/'figures_001';FIG.mkdir(exist_ok=True)

def loadj(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def writecsv(p,rows):
    keys=list(rows[0])
    with Path(p).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

# Parameter summary.
params=[]
for source in ('old_R0','main40','bridge_deepseek','bridge_qwen'):
    for fold in range(4):
        m=loadj(R2/f'fits/{source}/fold{fold}.json')['models']
        params.append(dict(source=source,fold=fold,
            U2_T_T=m['U2_T']['T'],
            Joint_NLL_lambda=m['Joint_NLL']['lam'],Joint_NLL_T=m['Joint_NLL']['T'],
            Task_lambda=m['Task_T']['lam'],Task_T=m['Task_T']['T'],
            Robust_lambda=m['Robust_T']['lam'],Robust_T=m['Robust_T']['T'],
            MCC_lambda=m['MCC_T']['lam'],MCC_T=m['MCC_T']['T']))
writecsv(OUT/'parameter_summary.csv',params)

# Frozen result frames used by report generation. Figures are emitted separately as pure SVG.
main=pd.read_csv(R2/'main40/metrics.csv')
allm=main[main.scope.eq('all')].set_index('method')
pdf=pd.DataFrame(params)

pairs=loadj(R2/'main40/paired.json')
p_ut=pairs['all/U2_T-vs-U2']
p_joint=pairs['all/Joint_NLL-vs-U2']
p_mcc=pairs['all/MCC_T-vs-U2']
breakdown=pd.read_csv(R2/'main40/nll_breakdown.csv').set_index(['method','group'])
repeat=pd.read_csv(R2/'repeat_stability.csv').set_index('method')
full=loadj(R2/'full_development_models.json')['models']

def pct(x):return f'{100*x:.2f}%'
def ci_pp(obj):
    lo,hi=obj['ci95'];return f'[{100*lo:+.3f}, {100*hi:+.3f}] pp'
def ci_num(obj):
    lo,hi=obj['ci95'];return f'[{lo:+.4f}, {hi:+.4f}]'

labels={'U0':'U0','U2':'固定 U2','U2_T':'U2 + T','Joint_NLL':'联合 NLL (scale+bias)','Task_T':'任务约束 lambda + T','Robust_T':'患者稳健 lambda + T','MCC_T':'MCC-only lambda + T（探索）'}

lines=[
'# 035：支持边界与置信度解耦',
'',
'## 结论先行',
'',
'**本轮把固定 lambda 的“标签决策”与概率置信度尺度明确拆开。主要结果是：lambda=2 在预定的PA/false-S约束下没有被其他lambda工作点支配；在所有16个患者外拟合折中，任务约束与患者稳健规则均保留lambda=2。固定lambda=2后只学习温度T，可保持每一条分类标签完全不变，同时显著降低NLL。**',
'',
'这不意味着“2由无先验算法重新发现”：任务/稳健规则以U2为可行锚点。为检验这一点，本轮另做探索性MCC-only选择；它会选出1.35–3.45之间明显漂移的lambda，并在main40上取得更高PA但更多false-S，在020两轮重复中方向不稳。因此当前更可辩护的定位是：**lambda=2是现有评分体系上一个稳定、风险受控的决策工作点，而T负责独立修正置信度尺度。**',
'',
'0新增API、未使用reserved40，不改变Judge、检索、prompt或医生GT。',
'',
'## 1. Main40患者外主结果',
'',
'全部40名development、3675条claim按患者4折外推；任何参数均只在另外患者上拟合。',
'',
'| 方法 | 正确/N | PA | MCC | false-S | NLL | Brier |',
'|---|---:|---:|---:|---:|---:|---:|',
]
for method in ('U0','U2','U2_T','Joint_NLL','Task_T','Robust_T','MCC_T'):
    r=allm.loc[method]
    lines.append(f"| {labels[method]} | {int(r.correct)}/{int(r.n)} | {pct(r.PA)} | {r.MCC:.4f} | {int(r.false_S)} | {r.NLL:.4f} | {r.Brier:.4f} |")

ut_nll=p_ut['probability_and_risk']['NLL']
joint_nll=p_joint['probability_and_risk']['NLL']
joint_fsr=p_joint['probability_and_risk']['FSR']
mcc_fsr=p_mcc['probability_and_risk']['FSR']
lines += [
'',
'### U2 + T：标签不动，只调整置信度尺度',
'',
f"- U2与U2+T的3675条预测标签逐条完全相同，因此PA、MCC、false-S及全部混淆矩阵完全不变。",
f"- NLL由 **{allm.loc['U2','NLL']:.4f} 降至 {allm.loc['U2_T','NLL']:.4f}**，配对患者bootstrap ΔNLL={ut_nll['delta']:+.4f}，95%区间 {ci_num(ut_nll)}。",
f"- 全development拟合得到T={full['U2_T']['T']:.3f}；四个main40外层折T为 {', '.join(f'{x:.2f}' for x in pdf[pdf.source.eq('main40')].U2_T_T)}。",
f"- NLL改善主要来自降低错误样本的过度置信：U2错误样本NLL **{breakdown.loc[('U2','U2_wrong'),'NLL']:.3f}→{breakdown.loc[('U2_T','U2_wrong'),'NLL']:.3f}**；真实类别原评分为0的260条为 **{breakdown.loc[('U2','true_class_score_zero'),'NLL']:.3f}→{breakdown.loc[('U2_T','true_class_score_zero'),'NLL']:.3f}**。相反，U2原本判对样本NLL {breakdown.loc[('U2','U2_correct'),'NLL']:.3f}→{breakdown.loc[('U2_T','U2_correct'),'NLL']:.3f}。",
f"- 不能据NLL下降宣称所有概率指标都改善：整体Brier从 {allm.loc['U2','Brier']:.4f} 变为 {allm.loc['U2_T','Brier']:.4f}，反而略升；human分层Brier改善，而LLM分层恶化。T应准确称为**NLL优化的置信度缩放**。",
'',
'### 联合NLL：概率拟合会主动选择更激进的支持边界',
'',
f"- 在与(lambda,T)相同两自由度的参数空间中，联合NLL在所有来源/折均把有效lambda推到预定上界 **4.0**；全development拟合为lambda=4、T={full['Joint_NLL']['T']:.3f}。",
f"- main40相对U2多判对 **{int(allm.loc['Joint_NLL','correct']-allm.loc['U2','correct'])}条**，PA {pct(allm.loc['U2','PA'])}→{pct(allm.loc['Joint_NLL','PA'])}，ΔPA 95%区间 {ci_pp(p_joint['metrics']['percent_agreement'])}。",
f"- 但false-S **{int(allm.loc['U2','false_S'])}→{int(allm.loc['Joint_NLL','false_S'])}**，FSR增加{100*joint_fsr['delta']:.2f}个百分点，95%区间 {ci_pp(joint_fsr)}；MCC仅+{p_joint['metrics']['mcc']['delta']:.4f}，区间 {ci_num(p_joint['metrics']['mcc'])} 跨0。",
f"- NLL与Brier均改善，说明NLL目标并非“无效”，而是它选择了一个更激进、不同风险偏好的工作点。",
]

lines += [
'',
'## 2. 为什么预定任务/稳健规则都回到lambda=2',
'',
'预定Task_T要求训练侧PA不低于U2、false-S不高于U2，再取MCC最高；Robust_T在同一可行集合上最大化患者bootstrap下MCC差的第10百分位。实际在old_R0、main40、DeepSeek、Qwen四类评分材料的4折中，**每折都只有lambda=2这一决策状态同时满足上述约束**，因此16/16折均选2。',
'',
'这支持“2在当前约束下是不被支配的工作点”，但不能写成“完全无先验地重新发现2”。',
'',
'## 3. 独立探索：只追训练MCC会发生什么',
'',
f"探索性MCC_T在main40取得 {int(allm.loc['MCC_T','correct'])}/{int(allm.loc['MCC_T','n'])}、PA {pct(allm.loc['MCC_T','PA'])}、MCC {allm.loc['MCC_T','MCC']:.4f}，相对U2多{int(allm.loc['MCC_T','correct']-allm.loc['U2','correct'])}条正确；但false-S {int(allm.loc['U2','false_S'])}→{int(allm.loc['MCC_T','false_S'])}，FSR增加{100*mcc_fsr['delta']:.2f}个百分点。",
f"其PA增量95%区间 {ci_pp(p_mcc['metrics']['percent_agreement'])}，MCC增量{p_mcc['metrics']['mcc']['delta']:+.4f}、区间 {ci_num(p_mcc['metrics']['mcc'])} 跨0。",
f"更关键的是参数并不稳定：main40四折lambda为 {', '.join(f'{x:.3f}' for x in pdf[pdf.source.eq('main40')].MCC_lambda)}；Qwen四折为 {', '.join(f'{x:.3f}' for x in pdf[pdf.source.eq('bridge_qwen')].MCC_lambda)}。",
f"在020同879条重复中，MCC_T第一轮相对U2为 **{int(repeat.loc['MCC_T','correct_R0']-repeat.loc['U2','correct_R0']):+d}条**，第二轮为 **{int(repeat.loc['MCC_T','correct_R1']-repeat.loc['U2','correct_R1']):+d}条**；标签跨轮翻转84条，对U2的81条没有稳定性优势。",
'',
'因此“直接学一个最优lambda”并没有自然解决固定2显得经验化的问题：选择准则本身会决定风险偏好，而且按单一开发指标选出的lambda明显更漂移。',
]

# Cross-model summary.
transfer=loadj(R2/'transfer_vs_refit.json')
max_transfer_nll=max(abs(v['probability_and_risk']['NLL']['delta']) for v in transfer.values())
lines += [
'',
'## 4. 重复与跨Judge材料',
'',
'旧019/020材料中，U2+T/Task_T/Robust_T与U2保持完全相同标签；NLL在R0由1.1742降至0.5082，在R1由1.2236降至0.5628。联合NLL在R0更差于U2分类并显著增加false-S；R1正确数略高但MCC更低、false-S更多。',
'',
'024的DeepSeek与Qwen评分上，任务/稳健规则仍16折中的相应折全部选lambda=2。联合NLL仍选lambda=4；MCC-only的lambda在模型间及折间明显漂移。',
f"将DeepSeek拟合的参数直接用于Qwen、或反向迁移，与目标模型重新拟合相比，所列方法的分类标签没有变化；NLL绝对差最大仅约{max_transfer_nll:.4f}。这是同10名患者上的辅助参数迁移现象，不视为外部泛化。",
'',
'## 5. 方法学解释',
'',
'035支持把当前后处理写成两个正交步骤：',
'',
'1. **支持决策边界 lambda**：决定哪些样本跨入Supported；它是风险—收益工作点，不是概率校准常数。',
'2. **置信度温度 T**：在固定lambda后统一缩放调整分数，不改变argmax标签；当前T约4–6，说明原自报评分的对数尺度非常尖锐。',
'',
'因此U2不必包装成“神奇的+2”。更准确的论文表述是：**在一个可解析的一维支持边界族中，lambda=2形成了跨患者材料可重复的风险受控工作点；概率尺度问题可由独立温度处理，而无需改变已经有效的决策。**',
'',
'035没有证明lambda=2是普适理论常数，也没有证明T产生了严格概率校准。联合NLL和MCC-only结果恰好显示：换优化目标会选择更激进或更漂移的边界。',
'',
'## 6. 执行与边界',
'',
'- run_001：预定六方法正式结果；run_002：加入明确标注为探索性的MCC_T，并逐项精确复现run_001六方法指标。',
'- 0收费API、0新Judge/检索、未使用reserved40。',
'- 当前research-verifact-029环境中的scipy.optimize.minimize存在进程级异常；联合NLL改用同一有界参数空间的确定性一维根求解坐标优化。9项数值/安全单元测试通过，正式预测冻结后分析。',
'- 四次工程失败运行均保留现场，不纳入正式结果。',
'- 035执行者复核见verification_001.json；不冒充独立审计。',
'',
'## 结果入口',
'',
'- 主表：run_002/main40/metrics.csv',
'- 配对区间：run_002/main40/paired.json',
'- 参数：parameter_summary.csv 与 run_002/fits/',
'- 重复：run_002/repeat_stability.csv',
'- 跨Judge：run_002/transfer_vs_refit.json',
'- 图：figures_001/',
]
(OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

status=[
'# 035 当前状态','',
'状态：执行与自检完成，0 API、未用reserved40；尚未独立审计。',
'',
'主结论：lambda与置信度尺度可解耦。预定Task/Robust规则在16/16个患者外折中均保留lambda=2；U2+T保持分类标签逐条不变，将main40 NLL从1.1806降至0.5790。联合NLL在所有折把有效lambda推到4.0，PA升至83.78%但false-S由183增至237。探索性MCC-only选择lambda在1.35–3.45间漂移，main40 PA提高但false-S增加，020重复轮次方向不稳。',
'',
'run_001为预定六方法正式结果；run_002加入探索性MCC_T并精确复现六方法。',
'',
'入口：report.md、run_002/main40/metrics.csv、run_002/main40/paired.json、parameter_summary.csv、verification_001.json。'
]
(OUT/'CURRENT_STATUS.md').write_text('\n'.join(status)+'\n',encoding='utf-8')
print('035 finalized')
