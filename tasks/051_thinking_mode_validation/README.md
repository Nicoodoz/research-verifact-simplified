# 051：Thinking Mode and Scoring Interface Validation

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/051_thinking_mode_validation/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

051固定原C48/E0和DeepSeek-V4-Flash-0731，拆分thinking开关与是否要求label_scores两个因素。四条件为N-S、N-V、T-S、T-V；thinking固定high，不搜索强度。

48条balanced screen后T-V通过预注册risk lane，随后在另外8名development患者的96条balanced confirmation上完成四条件验证。T-V相对N-S+U2少12条false-S、净多3条正确，但N-V仍有最高正确数和MCC，因此T-V定位为低false-S风险工作点而非总体winner。

正式结果：`../../outputs/051_thinking_mode_validation/report.md`；当前状态：`CURRENT_STATUS.md`；executor verification：`verification_001.json`。独立审计未执行。
