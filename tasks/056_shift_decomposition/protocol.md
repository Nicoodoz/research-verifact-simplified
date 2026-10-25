# 056：Unlabeled Shift Decomposition

## 目标

回答一个单一问题：target 无标签时，能否区分“主要是类别比例变化”与“Judge 类条件行为也发生变化”。

本任务 0 API，不改 retrieval、prompt、T-S、PriorG 或 055 已有预测，不使用 reserved。

## 固定输入

- 052 T-S 有效 236 条及对应 full-Qwen scoring。
- 053 T-S 有效 237 条及对应 full-Qwen scoring。
- 两方向都做：source=052→target=053，source=053→target=052。
- target GT 不进入真实 target 的 prevalence 估计、残差计算、阈值或 alarm；仅在冻结无标签结果后用于评价。

## Frozen monitors

- DeepSeek monitor：T-S + 053 冻结 G + 冻结 reference prior，即 Frozen PriorG。
- Qwen monitor：full-view Qwen scores 的 U0 hard decision。
- DeepSeek 用于 BBSE prevalence estimation；DeepSeek×Qwen 的 3×3=9 个联合 hard-output state 用于 shift compatibility。

## 主方法

1. source 有标签数据估计 DeepSeek confusion matrix C_DS 和联合 state matrix C_DQ=P(D,Q|Y)。
2. target 只读无标签 monitor outputs；用 C_DS + target DeepSeek hard distribution 做 constrained BBSE，得到 pi_hat。
3. 在“只有 label shift”假设下，预测 target 联合分布：
   expected(D,Q)=C_DQ @ pi_hat。
4. 观察真实 target 联合分布 observed(D,Q)，主残差为 TV=0.5*sum(|observed-expected|)；JS divergence 为次级量。
5. 用 source 类条件行为按 pi_hat 有放回重采样 2000 次，每次重新 BBSE，形成 target-n 对应的纯 label-shift null；95% 分位为 alarm threshold。
6. 同时报告 DeepSeek-BBSE 与 Qwen-BBSE 的 prior L1 disagreement，作为次级诊断，不作为主判据。

## 压力测试

- H0：从 source 自身类条件池按固定 prior 重采样，只改变 P(Y)。
- H1：保持相同 prior，但从另一批数据的 P(D,Q|Y) 重采样，模拟真实观察到的 conditional behavior replacement。
- prior 场景沿用 054：source、90/5/5、70/15/15、60/20/20、60/30/10、60/10/30。
- batch n=60/120/240/480；每条件 500 次。
- 每个 source/scenario/n 先用独立 1000 次 H0 建立95%阈值，再评价 H0 false-alarm 与 H1 detection rate。

## 事前判据与边界

机制 screen 认为“值得进入057”的最低证据：n=240 时两方向 H0 false-alarm 均 <=10%，且 H1 detection rate 均 >=70%。
真实052/053 alarm只作机制诊断，不把两批 development claim 描述成外部 domain。
若 screen 失败，优先停止 zero-label reliability gating，转 few-label adaptation；不据056结果继续调 detector。
