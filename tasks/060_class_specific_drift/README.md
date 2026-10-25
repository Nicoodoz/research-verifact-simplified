# 060：Unlabeled Class-specific Judge-drift Estimation

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/060_class_specific_drift/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

060研究target 0标签时，能否把059发现的真实class-specific Judge drift直接恢复出来。

方法：DeepSeek+Qwen 4维log-odds；source有标签固定三类分布；target无标签用带hierarchical shrinkage的3类latent mixture同时估target prior与3×4=12维class-specific drift。

结果：方向信息仍存在，但可识别性不足。n=960 synthetic中nonzero drift sign accuracy=93.32%，但prior L1=0.204、delta MAE=0.573，事前门槛FAIL。真实052→053还出现NS component近乎完全塌缩；两方向class-specific R2为0.004/-0.254，均不如059 global模型约0.17。

因此不进入dynamic decision。下一步若继续zero-label，需要低秩/结构化class-dependent drift，而不是继续增加自由参数。

0 API、未使用reserved、17项executor verification PASS；独立审计未执行。
