# 022 竞争感知支持边界校准

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/022_competition_aware_support_calibration/report.md)。 独立结论查[审计末尾](../../reviews/022_competition_aware_support_calibration.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

本任务依用户指定的[022计划](../../docs/022_竞争感知支持边界校准_任务计划.md)执行。阶段A先用019/020历史评分做零API、患者分组折外筛查；通过才登记阿里云DeepSeek快照同期阶段B。不得自动启动reserved40、切本地BGE或回写019–021。

**当前：阶段A未过门槛，任务按停止分支结束，待独立审计。** [唯一中文主报告](../../outputs/022_competition_aware_support_calibration/report.md) · [审计交接及重放命令](../../outputs/022_competition_aware_support_calibration/audit_handoff.md)。正式stageA_002；stageA_001输出序列化失败保留。没有阶段B/Qwen请求。

结果前登记见[protocol_001.md](../../outputs/022_competition_aware_support_calibration/protocol_001.md)。当前API路线：022的Judge直接阿里云DeepSeek V4 Flash 0731；BGE继续硅基流动Pro BGE-M3及Pro reranker，优先复用冻结缓存。总任务收费上限80元，阶段A为0元；收费前另核实地域、固定快照、接口与实际预算。无须为阶段A探测key。
