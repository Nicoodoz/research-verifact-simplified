# 059：Joint Prior and Judge-drift Estimation

## 目标

在target完全无GT时，同时估计：
1. target类别比例 pi_t；
2. DeepSeek与Qwen的低维Judge score drift。

059不修改最终分类器，不做adaptation，只回答“Judge具体往哪边漂、漂多少”是否可估。

## 低维Judge行为定义

对每个Judge，把0–100三类score统一加0.5分pseudo-count后转成两个log-odds：
- u_S = log((score_S+0.5)/(score_NA+0.5))
- u_NS = log((score_NS+0.5)/(score_NA+0.5))

一个环境的全局Judge drift定义为 additive log-odds bias：
- theta_S：整体更偏向/远离 Supported；
- theta_NS：整体更偏向 Not Supported 相对 Not Addressed。

DeepSeek和Qwen各2个参数，共4维theta。

这不是完整target confusion matrix，也不声称恢复class-specific recall变化。

## Joint moment decomposition

source有标签，可估每类Y的4维联合log-odds均值 mu_y 与协方差 Sigma_y。

假设target主要变化可近似为：
u_target | Y=y = u_source | Y=y + theta

其中theta对所有真实类别共享。

关键点：
- theta只平移均值，不改变协方差；
- 因此target总体协方差只由 pi_t 与source类条件矩决定。

先用target无标签联合4维log-odds协方差拟合 pi_t：
Cov_target ≈ sum_y pi_y (Sigma_y + mu_y mu_y^T) - mu(pi) mu(pi)^T

再估：
theta_hat = mean_target - sum_y pi_hat_y * mu_y

这样不依赖“DeepSeek hard prediction confusion稳定”的BBSE前提。

## 输入

- 052 T-S有效236条 + full-Qwen scores；
- 053 T-S有效237条 + full-Qwen scores；
- 双向source=052→target=053、source=053→target=052；
- target GT只在无标签估计结果冻结后用于评价。

## Synthetic recovery

从source类条件池重采样，再人为加入已知theta。
prior场景固定四种：
- source prior
- S60 = 60/20/20
- NS-heavy = 60/30/10
- NA-heavy = 60/10/30

batch n=240/480/960。
drift pattern固定：
- none
- DS_S +0.5 / -0.5
- DS_NS +0.5 / -0.5
- Q_S +0.5 / -0.5
- Q_NS +0.5 / -0.5
- conflict: DS_S +0.5, Q_S -0.5

每条件200次。

## 评价

Synthetic：
- prior L1；
- theta MAE / RMSE；
- 非零drift维度sign accuracy。

实际052↔053解盲后：
- true prior与pi_hat误差；
- oracle global theta = target mean - sum true_pi * source mu_y；
- theta_hat对oracle theta误差；
- class-conditional mean shift delta_y = mu_target,y - mu_source,y；
- common-shift explained fraction：
  R2_shift = 1 - weighted residual energy / weighted total shift energy。

## 事前判据

只有同时满足才认为当前4参数drift可进入060：
1. n=960 synthetic总体 prior L1 mean <=0.10；
2. n=960 synthetic theta MAE mean <=0.15；
3. n=960非零drift sign accuracy >=90%；
4. 真实两个方向 joint common-shift R2_shift 均 >=0.50。

若synthetic可恢复但真实R2不足，说明“全局bias drift”过于简单，应停止该参数化，不直接进入060。

## 边界

- 059估的是score-space global drift，不是完整Judge reliability/confusion matrix。
- 052/053是development内部batch，不是外部domain。
- 0 API，不使用reserved，不自动commit/push。
