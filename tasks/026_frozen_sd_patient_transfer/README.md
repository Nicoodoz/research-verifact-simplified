# 026 冻结SD跨患者组迁移

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/026_frozen_sd_patient_transfer/report.md)。 独立结论查[审计末尾](../../reviews/026_frozen_sd_patient_transfer.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

[发送前协议](../../outputs/026_frozen_sd_patient_transfer/protocol_001.md)。只在原024十患者训练最终SD，冻结后验证019六患者650条的新阿里云输出。固定λ2，Qwen只调用新D评分产生的候选，80元累计上限。

prepare026.py只准备/冻结；run026.py为真实收费入口，必须显式指定deepseek或qwen阶段。candidates026.py在D阶段结束后冻结不读GT的Qwen白名单。旧任务结果不覆盖，不自动reserved test。
