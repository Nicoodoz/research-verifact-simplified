# 063 当前状态

063已完成主实验 + Protocol Amendment 001，并完成executor-side verification：24项PASS。0 API，未使用reserved，未commit/push，独立审计未执行。

## 研究问题

目标是回答：target环境给多少个真标签，可以补上zero-label无法恢复的NS/NA conditional reliability，并安全改善最终分类。

固定budget：0 / 5 / 10 / 20 / 40。
两个方向：052→053、053→052。
每个非零budget、每个采样策略50 repeats。
主评价仅在未标注holdout claims，并与同一holdout的Frozen PriorG比较。

## 主063：9-pattern reliability table

只用Frozen PriorG hard label + Qwen U0 hard label形成9种joint pattern；source reliability作Dirichlet prior，few target labels更新P(pattern|Y)。

结果：random / active / oracle-balanced在0–40 labels内均没有两个方向同时通过事前deployment标准。

关键失败：
- 052→053始终明显损伤NS recall并提高false-S；
- oracle-balanced 40已经平均拿到14/13/13个S/NS/NA标签，但ΔMCC=-0.004、ΔNS=-0.500、Δfalse-S-rate=+0.186；
- 因此不是单纯“没采到NS”，hard pattern表示/决策本身不足。

## Amendment 001：soft-score mean calibration

保留4维DeepSeek/Qwen log-odds；source提供class means + pooled covariance；few target labels直接shrinkage更新target class means；BBSE prior固定。

结果同样没有budget通过。

值得注意：
- 052→053 active_soft 20/40：ΔMCC=+0.071/+0.091、ΔPA=+0.046/+0.041，但ΔNS=-0.571/-0.500，false-S-rate +0.212/+0.238；
- 052→053 oracle-balanced 40：ΔPA=+0.051、ΔMCC=+0.080，但ΔNS=-0.240、false-S-rate +0.118；
- 053→052 oracle-balanced 40：ΔMCC=-0.007、ΔNS=-0.216、false-S-rate +0.097。

因此few labels确实携带有用环境信息，但“用标签重建一个Bayes/LDA分类器”会改变S/non-S边界，产生更多false-S并牺牲NS recall。

## 当前科学结论

**063没有找到0–40中的有效标签阈值，missing link尚未闭合。**

但不能解释成“40个标签本身不够”。更准确是：
1. hard reliability table不够；
2. soft class-mean校准也不够；
3. 即使oracle-balanced labels也失败，说明当前calibrator/decision rule是主瓶颈，而非仅仅acquisition或标签数量。

下一步更合理的few-label用途应是：用少量target labels估计/选择一个有限的safe policy，并在不确定时回退Frozen PriorG；而不是再次从头构造Bayesian argmax classifier。

详见report.md、soft_report.md。
