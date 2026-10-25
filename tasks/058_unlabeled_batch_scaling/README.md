# 058：Unlabeled Batch-size Scaling

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/058_unlabeled_batch_scaling/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

058只测试一个问题：057 soft detector如果获得更多无标签target claims，conditional-shift detection是否继续改善。

完全复用057方法，不调任何detector参数。测试n=240/480/960/1920/3840。

结果：两方向平均检测率在n=960已达99.4%/97.4%，n=1920当前六种场景均为100%；误报约4–6%。说明样本量是当前zero-label detector的重要瓶颈。

注意：现有真实池仅236/237条，较大n为有放回重采样模拟统计趋势，不代表真实新增claims已经验证。

详见outputs/058_unlabeled_batch_scaling/report.md。
