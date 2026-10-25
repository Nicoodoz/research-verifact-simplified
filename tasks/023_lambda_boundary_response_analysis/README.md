# 023_lambda_boundary_response_analysis

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/023_lambda_boundary_response_analysis/report.md)。 独立结论查[审计末尾](../../reviews/023_lambda_boundary_response_analysis.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

对固定λ=2的Supported决策边界作离线响应/敏感性分析，不拟合或重新选择λ。使用已审019的650条R0、020的879条R0及同879条R1；pooled只含019＋020 R0的1529个不同claim。0新增API，不读reserved40，不修改019–022，不改变API路由或预算政策。

正式[结果前分析方案](../../outputs/023_lambda_boundary_response_analysis/protocol_001.md)。先对019七个旧锚点及020 U0/U2逐条标签和指标精确复现，失败则停止，不生成后续曲线。

**当前已执行完毕、待独立审计。** [唯一中文主报告](../../outputs/023_lambda_boundary_response_analysis/report.md) · [当前状态](CURRENT_STATUS.md) · [审计及安全重放](../../outputs/023_lambda_boundary_response_analysis/audit_handoff.md)。

prepare023绑定输入和锚点；analyze023生成密集/精确/患者曲线；summarize023做预定患者描述；connection022只定位旧022参数与预测；plot023导出图；verify023在新目录断网重放，不覆盖正式目录。统计使用research-verifact，作图复用research中的Matplotlib3.5.1，未安装/升级依赖。
