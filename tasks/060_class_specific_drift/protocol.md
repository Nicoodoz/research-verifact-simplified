# 060：Unlabeled Class-specific Judge-drift Estimation

## 目标

059证明：
- 低维Judge drift在合成数据中可从0标签target恢复；
- 但真实052↔053漂移强烈依赖真实类别，单个全局bias只能解释约17%。

060因此只解决一个问题：

> target完全无GT时，能否把Judge漂移估成 class-specific drift，而不是全局漂移？

本任务仍不修改最终分类器，不做dynamic decision。

## 表示

沿用059的4维联合log-odds：
- DeepSeek: u_DS,S 与 u_DS,NS
- Qwen: u_Q,S 与 u_Q,NS

score统一加0.5 pseudo-count后取：
- u_S = log((score_S+0.5)/(score_NA+0.5))
- u_NS = log((score_NS+0.5)/(score_NA+0.5))

source按全体均值/标准差z-score。

## Source anchored mixture

source有GT，因此对每个真实类别 y 冻结：
- 4维均值 mu_y；
- 4×4 covariance Sigma_y。

为稳定少数类covariance：
Sigma_y = 0.5 * class_cov_y + 0.5 * pooled_cov + 0.05 * I。

target无标签模型中，每个latent真实类别都有自己的：
- pi_y：target类别比例；
- delta_y：4维class-specific Judge drift。

因此不再假设“Qwen整体更偏NS”，而允许：
- 真S时Qwen几乎不变；
- 真NS时Qwen强烈变化；
- 真NA时又是另一种变化。

## Regularized latent EM

仅使用target无标签4维log-odds。

E-step：
按当前pi、delta和固定source covariance计算三个latent class responsibility。

M-step：
- pi由responsibility均值得到；
- 每类计算raw target mean shift；
- delta_y向一个自由shared shift g做hierarchical shrinkage；
- penalty强度tau固定为20；
- g本身不向0收缩，所以允许整体Judge bias；
- 每个delta在source z空间限制到[-3,3]，仅防止少数类数值塌缩。

固定最多100轮，tol=1e-6。

## 初始化

每个target固定三个deterministic starts，不看GT：
1. source empirical prior + delta=0；
2. uniform prior + delta=0；
3. 059 covariance-moment prior + delta=0。

选择最终penalized log-likelihood最高的解。

不根据060结果调整tau、covariance shrinkage、clip或starts。

## Synthetic recovery

从source类条件池按指定prior有放回抽样，再按真实Y注入已知class-specific raw-log-odds drift。

prior固定四种：
- source
- 60/20/20
- 60/30/10
- 60/10/30

batch n=240/480/960。

drift pattern固定：
1. none
2. NS_QNS：真NS的Qwen u_NS +1.5
3. NA_DSS：真NA的DeepSeek u_S +1.0
4. NS_DSNS：真NS的DeepSeek u_NS +1.0
5. S_QS_down：真S的Qwen u_S -0.5
6. mixed：
   - 真S：DS u_S -0.5
   - 真NS：DS u_NS +1.0, Q u_S +0.5, Q u_NS +1.5
   - 真NA：DS u_S +0.8, DS u_NS +0.5

每条件30次。

评价：
- prior L1；
- 12维delta raw-log-odds MAE；
- 非零drift sign accuracy。

## 真实052↔053评价

actual_unlabeled先冻结：
- pi_hat；
- 3×4 delta_hat；
- fit likelihood与effective class mass。

随后才读取target GT计算：
- true prior与prior L1；
- true class-specific delta_y；
- delta MAE；
- weighted class-specific shift R2；
- 对明显非零真实漂移计算sign accuracy。

同时与059 global-shift R2作固定比较。

## 事前门槛

只有同时满足才允许下一步进入dynamic decision：
1. n=960 synthetic prior L1 mean <=0.10；
2. n=960 synthetic delta MAE mean <=0.30；
3. n=960 synthetic nonzero sign accuracy >=90%；
4. 真实两方向 class-specific R2 均 >=0.50；
5. 真实两方向 prior L1 均 <=0.15。

若synthetic通过但真实失败，不调tau或模型。

## 边界

- 估计的是score-space class-specific drift，不等同真实confusion matrix。
- source/target均为development内部claim batch。
- 0 API，不使用reserved，不自动commit/push。
