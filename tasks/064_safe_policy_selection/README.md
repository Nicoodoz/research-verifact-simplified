# 064：Target-local Safe Policy Selection

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/064_safe_policy_selection/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

064把问题从“恢复完整target Judge reliability”改成“认证Frozen PriorG附近的局部policy”。

候选policy：BASE、Qwen强non-S veto（V80/V60）、Qwen高置信S rescue（R90）及组合。少量target标签只学习policy disagreement region，不重建分类器；证据不足回退BASE。

Oracle诊断：
- 052→053正确policy是R90（+5 correct，MCC 0.5596→0.5905，false-rescue 16.7%）；
- 053→052正确policy是BASE（R90风险66.7%）。

最终patient-disjoint Exposure Fix结果：
- 052→053 active 10 labels：R90认证58%，unsafe 0%，future ΔPA +1.06pp、ΔMCC +0.0127；
- 053→052 active 20 labels：BASE fallback 90%，unsafe 10%；
- 尚未达到两方向同时通过的预注册门槛，因此missing link未正式闭合。

关键新诊断：R90 region只有6条/6患者。当前瓶颈不是总label budget，而是稀有action-region标签证据不足。

29项executor verification PASS；0 API；未使用reserved；独立审计未执行。
