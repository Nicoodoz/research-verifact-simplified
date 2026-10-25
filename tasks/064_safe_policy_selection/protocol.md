# 064：Target-local Safe Policy Selection

## 目标

不再从0/少标签恢复完整target Judge reliability，也不训练新分类器。

目标改为：

> 只在Frozen PriorG附近定义少数局部动作，用0/3/5/10/20个target标签判断哪些动作在当前环境值得执行；证据不足时回退Frozen。

这直接对应“保留低风险Supported rescue，同时阻止高风险non-S被错误推成Supported”。
## 固定policy library

BASE：Frozen T-S + PriorG。

Qwen U0作为第二个真正不同的Judge。定义：
- q = Qwen hard argmax；
- qtop = Qwen最高score；
- qS = Qwen Supported score。

候选：
1. BASE
2. V80：BASE=S 且 q!=S 且 qtop>=80 → q
3. V60：BASE=S 且 q!=S 且 qtop>=60 → q
4. R90：BASE!=S 且 q=S 且 qS>=90 → S
5. C80：R90 + V80
6. C60：R90 + V60

source-only / target-GT-blind检查已确认所有候选均是局部策略；U2相对Frozen PriorG在052/053没有新增non-S→S动作，因此不作为独立候选。
## 为什么用policy signature

每条claim记录6个policy的预测向量signature。

只有signature中存在至少两个不同预测的claim才是policy-disagreement region。

在当前052/053无标签池中各只有6种signature，其中3种真正涉及policy分歧；因此few labels只需要学习这些局部区域的真实类别组成，不需要学习整个target分类器。

source有GT，可得到每个signature的P_s(Y|signature)。
固定Jeffreys +0.5平滑后，只保留shape；source先验总强度固定为1个等效target label，允许少量target标签快速覆盖source conditional drift。
## Target-local posterior

对每个target signature s：

alpha_s =
1.0 * P_s(Y|s) + target labeled counts in s。

若source从未出现某signature，则P_s取uniform。

每个candidate policy只在其相对BASE改变预测的signature上产生局部效应。

对posterior做固定2000次Dirichlet Monte Carlo，估计：
- Δcorrect；
- P(Δcorrect > 0)；
- rescue false-rescue rate：改成S的claims中真实non-S比例；
- veto S-harm rate：从S改成non-S的claims中真实S比例。

MC seed固定，由source/target/budget/rep派生。
## Policy认证与选择

候选非BASE policy只有同时满足才被认证：
1. posterior mean Δcorrect > 0；
2. P(Δcorrect > 0) >= 0.80；
3. 若含rescue：posterior mean false-rescue rate <= 0.25；
4. 若含veto：posterior mean S-harm rate <= 0.25。

在所有认证policy中，选择posterior mean Δcorrect最大的。
若没有认证policy，选择BASE。

注意：
- veto动作结构上不会新增false-S，但会伤真S，因此约束S-harm；
- rescue允许小量false-S风险，但要求预计至少75% rescue对象是真Supported。
## Label budgets与采样

budget固定：
0 / 3 / 5 / 10 / 20。

### random_global
patient-diverse地从整个target随机取标签。
50 repeats。

### active_policy（主方案）
只从policy-disagreement region取标签，GT-blind、顺序式。

规则：
1. budget允许时先让每个disagreement signature至少获得1个标签；
2. 之后根据当前posterior计算每个signature的action-decision uncertainty；
3. 优先标注“该action到底该接受还是拒绝”最不确定、且仍有未标注claim的signature；
4. 同时优先未覆盖sid；
5. 固定seed打破并列。

decision uncertainty结合：
- action正确性增益P(gain>0)接近0.5的程度；
- rescue/veto风险均值距离0.25阈值的接近程度；
- signature剩余规模。

不读取target GT，只有选中后才揭示该条GT并更新posterior。
## Oracle policy（仅诊断）

使用完整target GT，在6个candidate policy中计算真实局部风险与整体metrics。

非BASE policy被视为oracle-safe需要：
- 相对BASE correct数严格增加；
- 若含rescue，真实false-rescue rate <=25%；
- 若含veto，真实S-harm rate <=25%；
- NS recall与NA recall均不得下降超过0.02。

在oracle-safe中选择MCC最高、再PA最高者。
若无safe beneficial policy，则oracle=BASE。

Oracle不参与任何few-label选择，只定义“当前环境正确的动作/回退是什么”。
## 评价

每个方向：
- 052→053；
- 053→052。

每个strategy × budget × 50 repeats：
- 已标注claims从主holdout移除；
- 选定policy应用到剩余未标注claims；
- 与同一holdout Frozen BASE比较。

报告：
- selected policy分布；
- oracle-policy match rate；
- unsafe-switch rate；
- BASE fallback rate；
- mean ΔPA / ΔMCC / Δfalse-S-rate / ΔS / ΔNS / ΔNA；
- operation-level metrics（人工标签直接采用GT）；
- 每个signature获得的target标签数。
## 事前“missing link closed”标准

某个最小budget b只有同时满足才算当前development setting下少标签链路闭合：

对两个方向：
1. unsafe-switch rate <=10%；
2. 若该方向oracle policy != BASE：选择任一oracle-safe beneficial nonBASE policy的概率 >=70%；
3. 若该方向oracle policy == BASE：BASE fallback rate >=90%；
4. mean ΔPA >=0；
5. mean ΔMCC >=0；
6. mean ΔNS >=-0.02；
7. mean ΔNA >=-0.02。

另外报告exact oracle-match，但不要求必须选同一个等价policy。

budget=0若只能安全回退，记为zero-label safe但不视为adaptation链路闭合。
## 边界

- 052/053仍是development内部池，policy library也受到此前development分析启发，因此不能作为独立外部验证。
- 064验证的是“局部policy认证”是否比“重建target分类器”更label-efficient。
- 0 API，不使用reserved，不自动commit/push。
