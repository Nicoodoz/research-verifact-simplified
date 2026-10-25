# Task 043 — Targeted Evidence Utility

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/043_targeted_evidence_utility/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

目标：验证039定位出的新增EHR证据，真正交给原DeepSeek scoring Judge后，是否能让Judge自己改变判决并生成与新判决一致的reason。

这是reserved后的post-hoc机制实验，不是新的无偏性能测试，也不用于方法选择。

三条件：
- A：原C48；
- B：原C48 + 039实际引用的目标证据；
- C：原C48 + 同数量matched context控制。

主要结果：B相对A在普通DeepSeek verdict上13 rescue / 0 harm；B相对C 14 rescue / 3 harm。

主报告：../../outputs/043_targeted_evidence_utility/report.md
执行者核验：../../outputs/043_targeted_evidence_utility/verification_001.json

独立审计：待进行。
