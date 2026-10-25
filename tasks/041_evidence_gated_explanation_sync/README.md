# 041 Evidence-gated Explanation Synchronization

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/041_evidence_gated_explanation_sync/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

零API、确定性解释门控。

只对严格证据trace通过的post-hoc Supported改判生成同步解释；C/D/U一律abstain。
不根据final label自由调用LLM重写理由。

报告两个工作点：
- C48-only：只接受039 A；
- Expanded A+B：接受039 A/B。

入口：outputs/041_evidence_gated_explanation_sync/report.md
