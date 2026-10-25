# 024 固定λ=2跨后端与跨模型迁移验证

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/024_lambda2_transfer_validation/report.md)。 独立结论查[审计末尾](../../reviews/024_lambda2_transfer_validation.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

**024当前：** 用户amendment_002核心字段口径优先。解析core024.py，执行run024_direct.py（同一阿里云端点，本任务进程直连），评价analyze024_core.py，安全离线核查verify024_core.py。HTTP200包括核心invalid均不重跑。[最新状态](CURRENT_STATUS.md)。下方初版入口只代表历史阶段。


正式协议：[protocol_001.md](../../outputs/024_lambda2_transfer_validation/protocol_001.md)。完整020队列879条，阿里云DeepSeek0731与Qwen3.8-27B，B/S各一次，λ仅0/2，任务80元累计上限。

`prepare024.py`一次性冻结；`run024.py --health --workers 4`发送4个正式接口验证请求，之后`run024.py`断点补齐未发送请求。`--retry-unanswered`仅用于保留旧记录后的无回答失败，HTTP200绝不重跑。执行器是真实收费入口，不作为离线重放使用。
