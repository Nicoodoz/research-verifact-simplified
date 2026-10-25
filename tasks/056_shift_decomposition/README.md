# 056：Unlabeled Shift Decomposition

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/056_shift_decomposition/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

056测试target完全无GT时，能否把“类别比例变化”和“Judge类条件行为变化”拆开。

固定方法：
- DeepSeek Frozen PriorG hard label → BBSE估target prevalence；
- DeepSeek×Qwen 9格联合hard-output分布 → label-shift compatibility residual；
- source纯label-shift重采样给出95% alarm阈值；
- 用另一批真实P(D,Q|Y)做conditional replacement压力测试。

结果：事前机制screen未通过。n=240两方向conditional-shift detection为55.17%和38.20%，虽H0误报仅4.13%和5.70%。真实052↔053两方向也均未报警。

因此当前hard-output detector不支持直接进入reliability-gated zero-label adaptation。详见outputs/056_shift_decomposition/report.md与CURRENT_STATUS.md。

0 API、未使用reserved、executor verification 12项PASS；独立审计未执行。
