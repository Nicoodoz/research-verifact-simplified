# 055：Zero-label Prevalence-conditioned Policy Adaptation

## 目标

实现真正的目标域0标签自适应：
target环境只提供一批无标签claim/model outputs；系统自动估计prevalence shift，并在需要时选择source阶段预先学好的决策policy。target GT只用于最终评价。

本任务不新增LLM调用，不改retrieval/prompt/T-S Judge。所有适应发生在冻结T-S scores之后。

## 关键设计

1. Frozen PriorG仍是默认policy。T-S base logits保留053冻结G；其精确相对偏置为：
   - S vs NA: +1.87451343
   - NS vs NA: -0.50957484
   - NA: 0
2. source监督集：
   - target=052时：051有效143 + 053有效237；
   - target=053时：051有效143 + 052有效236。
   target的任何GT不进入source policy/shift detector。
3. BBSE：用source的Frozen PriorG类条件混淆矩阵和target无标签Frozen predictions估计target S/NS/NA prior。
4. shift detector：对每个adaptation batch size，在source上按source prior重采样1000次，得到BBSE估计prior距source prior的L1 null分布；95%分位作为触发阈值。target估计L1不超过阈值时，保持Frozen PriorG。
5. prevalence-conditioned policy：source阶段预计算一组低维加性policy：
   - S bias grid 0.5..3.0，步长0.25；
   - NS bias grid -1.5..1.5，步长0.25；
   - NA=0；
   - 加入精确Frozen PriorG作为候选。
   对每个候选仅保存source类条件混淆，不使用target标签。

## 自适应policy

- Detect-PA：检测到shift后，在估计target prior下选择source预期PA最高的policy；tie-break为MCC更高、false-S更低。
- Detect-MCC：检测到shift后选择source预期MCC最高的policy；tie-break为PA更高、false-S更低。
- Always-PA / Always-MCC仅作诊断，说明shift detector的价值。
- Oracle-PA / Oracle-MCC使用真实target prior选择source policy，只作上限；target GT仍不参与policy训练。
- Frozen PriorG、Naive BBSE PriorG、U2、Gate A、原VeriFact为基线。

不新增手工作者路由、文本规则或target-specific参数。
