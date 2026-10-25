# 064 Protocol Amendment 002：Future-policy Exposure Fix

## 问题

Amendment 001 的代码在few-label认证时复用了主064的 same-batch 逻辑：
policy posterior 的作用规模使用“calibration中移除已标注claims后的 remaining signature counts”。

这对same-batch holdout是正确的，但对future-patient部署语义错误：
- calibration labels的作用是估计target action reliability；
- policy将应用于未来未见患者；
- 即使calibration中的某个action region已被全部标注，未来仍会继续出现该region；
- 因此不能因为calibration剩余action count=0就把policy自动视为无收益。

## 修正

Patient-disjoint future validation中：
- posterior class composition仍只由已揭示calibration labels更新；
- policy作用规模固定使用**完整calibration unlabeled signature counts**，作为future action prevalence的无标签估计；
- 不再减去已标注claims；
- acquisition、policy库、source prior、P_gain阈值、25% rescue/veto风险阈值、budgets、patient split、成功标准全部不变。

原 Amendment 001 结果保留，不覆盖。
修正结果写入 future_v2_* 文件。

0 API，不使用reserved，不自动commit/push。
