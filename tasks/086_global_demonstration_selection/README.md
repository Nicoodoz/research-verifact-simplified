# 086：全局固定四例效用选择

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/086_global_demonstration_selection/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

086机制归因以[087追加更正](../../outputs/087_f4_evidence_intervention/086_correction.md)为准：有效评分1救回/3伤害，另1救回涉及无效输出fallback，主结果不变。

## 原任务阶段说明（历史）

- [收费前协议](protocol.md) · [相关工作](related_work.md) · [中文报告](../../outputs/086_global_demonstration_selection/report.md)（结项后）
- `prepare086.py`：冻结D/V/E、既有医生示例池、五个有序完整四例组、36条V与110条E、V请求。只对V读GT，E盲。
- `verify_inputs086.py`、`check_overlap086.py`、`test086.py`：零API核查患者隔离、文本重叠、精确prompt、费用/失败mock等。
- `run086.py preflightV|V|preflightE|E`：统一¥30原价账本，append-only真实请求/回执、最多3次有限恢复；不能单独用历史runner继续。
- `select086.py`：V完整五组效用表及唯一D*冻结，不读E GT。`sensitivity086.py`只做V患者留一敏感性。
- `prepare_e086.py`：D*冻结后产生同期F4、D*、无效用组及12条B桥接E请求，不读E GT。
- `analyze086.py`：E全部完成后读取GT，以共享评价器报告raw/U0/U2/Frozen PriorG。
- `verify_results086.py`：独立重算费用、正确数、错误支持、来源SHA与病例覆盖，不做新推理。
- `pause_inventory085a.py`和[085A暂停记录](../085_r1_70b_model_swap/PAUSED_BY_USER.md)：只读本地盘点，无AWS调用。

源码与输出均为任务独立目录；不运行会覆盖071–085A固定成果的旧生成器。不用reserved40、无R1调用、默认B＋Frozen PriorG不改。
