# 038：证据—标签—解释一致性审计

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/038_evidence_explanation_audit/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

本任务在036最终评价完成后开展，只回答一个问题：离线后处理改善claim-level标签一致性时，实际C48证据和原Judge解释是否与最终标签同步。

范围：
- 全量统计036最终标签与scoring原verdict/reason的分歧；
- 对全部342条U0非S→U2 S翻转和120条固定hash稳定对照做双模型盲证据审计；
- 对346条“U2最终S但原verdict非S”做Qwen解释一致性审计；
- 不修改036任何预测、参数或方法，不把自动审计当医生gold。

执行入口：

    pwsh -NoProfile -File scripts/run_research.ps1 tasks/038_evidence_explanation_audit/verify038.py

结果入口：
- outputs/038_evidence_explanation_audit/report.md
- outputs/038_evidence_explanation_audit/analysis_001/
- outputs/038_evidence_explanation_audit/verification_001.json

本任务不自动启动039，不自动提交或推送。
