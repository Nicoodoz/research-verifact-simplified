# 063 Protocol Amendment 001：Soft-score Few-label Reliability Calibration

## 触发原因

主063的9-pattern hard reliability table正式失败：
- random / active / oracle-balanced到40 labels均未两方向通过；
- 关键失败是NS recall和false-S；
- oracle-balanced 40在052→053已含约13个NS标签，但hard-pattern模型仍不能泛化。

因此本amendment不改budget、不改主指标、不改通过标准，只测试：

> 少量target标签是否能在保留连续soft-score信息后补齐conditional reliability。
## 模型：source-anchored few-label LDA

特征固定为059–062沿用的4维log-odds：
- DeepSeek S-vs-NA；
- DeepSeek NS-vs-NA；
- Qwen S-vs-NA；
- Qwen NS-vs-NA。

仅用source统计：
- source全体mean/std做z-score；
- 每个真实类别source mean mu_s,y；
- pooled within-class covariance Sigma_s；
- Sigma = Sigma_s + 0.1 I，固定ridge。

target prior仍固定为BBSE pi_hat。
## Few-label更新

给budget b个target标签后，只更新每类target mean：

mu_t,y =
(kappa * mu_s,y + sum_{i:Y_i=y} z_i) /
(kappa + n_y)。

协方差不更新。

预测未标注claim：
log score_y =
log BBSE_pi_y
- 0.5 * (z - mu_t,y)^T Sigma^{-1} (z - mu_t,y)。

这样target真标签直接校准class-specific Judge score geometry，不需要latent assignment。
## kappa选择

候选仍为：
{1, 3, 10, 30, 100}。

budget=0时等价于source mean。

budget>0时仅在few-label subset内leave-one-out：
- 每次移除一个已标注target claim；
- 用其余labels计算adapted means；
- 对被移除label计算Gaussian-LDA posterior NLL；
- 选择平均NLL最低kappa；
- tie取更大kappa。

不读取holdout GT。
## Label budgets与评价

完全沿用主063：
- b = 0 / 5 / 10 / 20 / 40；
- 主评价只在剩余未标注claims；
- Frozen PriorG在同一holdout做baseline；
- PA / MCC / false-S rate / S/NS/NA recall；
- safe-win定义和deployment-pass六项标准完全不变；
- 50 repeats。

保留random与oracle-balanced。
## 新active_soft采样

主063的hard-pattern entropy active会漏掉NS，因此amendment用与soft calibrator一致的unlabeled acquisition：

1. 用source means/covariance + BBSE prior计算每个target claim的LDA posterior；
2. uncertainty = posterior entropy；
3. predicted class = argmax posterior；
4. greedy score =
   uncertainty / (1 + 已选择的该predicted-class数量)；
5. 仍优先未覆盖sid；
6. 同分固定seed打散。

全程不读取target GT。
## 事前判读

“很好解决”的标准与主063完全相同。

若active_soft某个最小budget在两个方向同时通过：
- 记录该budget为063的few-label operational threshold；
- missing reliability link视为在当前development setting下被补齐。

若oracle-balanced通过但active_soft不通过：
- 信息量足够，acquisition仍是瓶颈。

若oracle-balanced 40仍不通过：
- 说明即使保留soft scores，当前mean-shift few-label calibrator也不足；
- 063不得宣称已补齐链路。

## 边界

这是主063失败后的预注册amendment，结果单独保存，不覆盖主结果。
0 API，不使用reserved，不自动commit/push。
