# 057：Soft Multi-view Conditional-shift Detection

## 目标

056只使用DeepSeek×Qwen的hard-label 9格联合分布，事前screen未通过。057只回答一个问题：

> 056失败是因为conditional-shift信息本来不存在，还是因为hard label把连续score信息压掉了？

本任务不修改分类器，不做057后的动态adaptation，不新增API，不使用reserved。

## 固定输入

- 052：T-S有效236条 + 对应full-Qwen scoring。
- 053：T-S有效237条 + 对应full-Qwen scoring。
- 两方向：source=052→target=053；source=053→target=052。
- target GT不进入实际target的prevalence估计、soft residual、threshold或alarm，只在GT盲结果冻结后用于评价。

## Prevalence sensor

沿用056：
- DeepSeek Frozen Monitor = T-S + 冻结G + 冻结reference prior；
- source有标签confusion matrix；
- target只读DeepSeek Frozen Monitor hard predictions；
- constrained BBSE得到 target prevalence pi_hat。

## Soft detector

主视图固定为DeepSeek T-S三类scores + Qwen三类scores，共6维连续向量。
每个source方向单独冻结：
1. scores先除以100，使用source均值/标准差做z-score；
2. source pairwise Euclidean distance的非零中位数作为RBF bandwidth；
3. 用固定seed生成128维Random Fourier Features，近似RBF mean embedding；
4. source按真实Y分别计算三类mean embedding mu_y；
5. target观测embedding均值 mu_t；
6. 在“纯label shift”假设下，期望embedding为 sum_y pi_hat(y) * mu_y；
7. 主soft residual = L2(mu_t - expected_embedding)。

所有transform/bandwidth/RFF参数只由source建立；target不参与拟合。

## Null threshold与压力测试

- 真实target：按 pi_hat 从source类条件池重采样2000次，每次重新BBSE并计算soft residual；95%分位为alarm threshold。
- 压力测试prior沿用054/056六种：
  source、90/5/5、70/15/15、60/20/20、60/30/10、60/10/30。
- batch n=60/120/240/480。
- 每个source/scenario/n：1000次H0用于threshold calibration；H0和H1各500次评价。
- H0：从source自身P(scores|Y)按指定prior重采样。
- H1：保持同一prior，但从另一批真实P(scores|Y)重采样，模拟conditional behavior replacement。

## 事前判据

与056保持同一机制门槛，避免事后放宽：
- n=240时，两source方向mean H0 false-alarm均 <=10%；
- n=240时，两source方向mean H1 detection均 >=70%。

另外做一个deployability check：055中source-only Qwen label-model在052→053与053→052都至少破坏一项安全指标，因此若057未来想作为“是否启用zero-label adaptation”的安全开关，真实两方向都应触发alarm。该check不参与detector拟合，只用于判断是否具备实际gate价值。

若机制screen或真实deployability check失败，不根据结果继续调RFF维度、bandwidth、feature transform或阈值。后续是否转few-label另行决定。

## 次级分析

- 与056 hard joint-TV在相同stress条件下比较检测率，仅作机制解释。
- 可报告DeepSeek-only / Qwen-only soft residual作为固定ablation，但不据ablation结果替换主6维joint detector。
- 052/053均为development内部claim批次，不能外推为外部医院/domain。
