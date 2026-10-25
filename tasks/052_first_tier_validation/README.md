# 052：First-tier Same-cohort Validation

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/052_first_tier_validation/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

052将036后的第一梯队 N-V、T-S+U2、T-V 与 U2、patient-out Gate A、原VeriFact在同一批24名development患者240条patient-balanced随机claim上比较，并用051另外16名患者训练同配方N-S/T-S G/M标准校准。

结果：N-V/T-V和selective cascade的051 accuracy优势未迁移；051-trained G/M也未提高分类性能。唯一保留的跨患者正信号是 **T-S + 固定U2**：相对U2总体PA大致持平但false-S明显减少、MCC/NS/NA更健康；相对patient-out Gate A的MCC配对患者区间为正。Human-written子组信号尤其强。

正式结果见 `../../outputs/052_first_tier_validation/report.md`，当前状态见 `CURRENT_STATUS.md`，执行者核验见 `verification_001.json`。Operational invalid→U2 fallback单列于 `operational_sensitivity.json`，不替换冻结主结果。独立审计未执行。
