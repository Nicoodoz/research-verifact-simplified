# 027 双Judge迁移瓶颈诊断

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/027_dual_judge_transfer_diagnosis/report.md)。 独立结论查[审计末尾](../../reviews/027_dual_judge_transfer_diagnosis.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

零API、零新训练、固定λ=2。仅读025/026及其冻结来源，保留026停止结论；完整阈值曲线仅用于诊断，不能选新工作点或winner。

[诊断协议](../../outputs/027_dual_judge_transfer_diagnosis/protocol_001.md)。正式结果入口为outputs/027_dual_judge_transfer_diagnosis/report.md。`analyze027.py`为禁网离线入口；所有输出只写新目录。独立审计待另行开展。
