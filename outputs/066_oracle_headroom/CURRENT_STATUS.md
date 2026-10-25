# 066 当前状态

## 后续解读（2026-09-23）

223/240、MCC 0.7968是GT逐例选择并保护原正确病例的经验oracle点，不是可部署方法的预期收益；同证据的候选还包含后处理差异，不能全部归为纯推理能力。069对C48内历史修复病例仍观察到6条/5患者的原包稳定错、oracle两次对，但简化操作未晋级；070显示候选整体替换会产生更多伤害。C48内段落被选入不证明该段的独立因果必要性，C48外段落被使用也不证明扩大检索必要。

参见[069](../069_final_pack_controlled_repair/report.md)、[070](../070_fixed_evidence_reasoning_diagnosis/report.md)及[项目现状](../../docs/PROJECT_STATUS.md)。下方保留066形成时的状态，原报告和实验数字不回写。

066 Oracle Headroom Decomposition 已完成。

核心数字：
- Baseline T-S+PriorG：201/240，PA 83.75%，MCC 0.5607。
- Observed Reasoning Oracle：215/240，PA 89.58%，MCC 0.7101。
- GT-aware Evidence Oracle + T-S+PriorG：212/240，PA 88.33%，MCC 0.6680。
- Combined Oracle：223/240，PA 92.92%，MCC 0.7968。

39个基准错误：
- reasoning-only 11
- evidence-only 8
- both 3
- neither 17

前处理Evidence Oracle修11条，其中进一步定位：
- 9条：关键证据已在C48，但原final pack未完整选入；
- 1条：所有oracle证据原本已在final reference，只需更好重组/聚焦；
- 1条：需要C48外证据或mixed retrieval。

因此前处理的首要瓶颈明确定位在 **C48 → final evidence pack selection/packing/composition**，不是扩大检索范围。

Reasoning Oracle修14条；7个NS基准错误全部可被oracle之一修，其中6个reasoning-only，因此NS错误主要属于推理/语义边界。

17条两个oracle都未修：11 S + 6 NA。9条GT-aware composer认为证据decisive但Judge仍错，另8条证据仍不充分/无法构造决定性pack。

Evidence pack变化后，T-S raw修10条，Frozen PriorG修11条；PriorG有1 harm、2 rescue，当前净+1，暂不需要重新研究后处理，但正式上游方法改变后需验证兼容性。

执行：113/113 HTTP200，费用约¥2.304612，reserved=false；143项executor verification PASS；独立审计未执行；未commit/push。
