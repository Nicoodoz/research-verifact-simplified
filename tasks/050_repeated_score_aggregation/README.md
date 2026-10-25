# 050：Repeated Scoring Aggregation

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/050_repeated_score_aggregation/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

050研究完全相同DeepSeek scoring prompt重复调用后的label_scores稳定性，以及固定3-run聚合能否稳定U2。

Screen为32条、每条6次完全相同scoring调用；无聚合规则达到预设稳定性+性能门槛，因此58条患者隔离confirmation按协议不执行。

结果见 `../../outputs/050_repeated_score_aggregation/report.md` 与 `CURRENT_STATUS.md`；executor verification见 `verification_001.json`，独立审计未执行。
