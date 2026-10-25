# 034：原 VeriFact、U2 与 U2+A全40 同ID比较

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/034_same_data_comparison/report.md)。 独立结论查[审计末尾](../../reviews/034_same_data_comparison.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

目标：在完全相同的40名development患者、3675条valid atomic claims上，离线比较原论文VeriFact历史发布系统、固定U2和033推荐的A Gate训练策略。

本任务不调用任何API，不重新训练Judge/Gate，不使用reserved40。原VeriFact逐条预测来自002；U2和A全40患者外预测来自033。

主比较使用A_all40的患者外/LOPO预测：每个development患者评价时均不进入对应Gate训练，避免直接报告训练本人结果。

运行：

    python -B tasks/034_same_data_comparison/run034.py
    python -B tasks/034_same_data_comparison/verify034.py

结果入口：outputs/034_same_data_comparison/report.md。
