# 055：Zero-label Adaptation

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/055_zero_label_policy_adaptation/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

055研究新环境完全没有target GT时，能否自动适应类别prevalence和判定策略。初始阶段仅使用既有DeepSeek outputs；在该路线跨环境不稳定后，根据用户“实现方法不限、目标是zero-label adaptation”的要求，通过Protocol Amendment 001加入完整Qwen second opinion。

最终结果：无标签prevalence估计和shift detection已经可行；Qwen提供明显互补NS信号；若允许看target评价结果，可以找到显著优于PriorG的工作点。但当超参数/是否启用adaptation严格只由source患者CV决定时，跨052↔053不能稳定复制，安全selector最终在两方向均回退Frozen PriorG。

因此055没有宣称已经实现稳定通用的zero-label automatic adaptation。正式报告见`../../outputs/055_zero_label_policy_adaptation/report.md`；状态见`CURRENT_STATUS.md`；完整性见`verification_001.json`。

Full Qwen extension：429新调用 + 51复用，实际费用7.451754 CNY，429/429完成。未自动commit/push。
