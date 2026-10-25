# 061：Prior-Anchored Class-specific Drift Estimation

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/061_prior_anchored_drift/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

061只验证一个问题：把target prior固定后，060的12维class-specific drift能否恢复。

Oracle-fixed prior作为诊断上限；BBSE-fixed prior作为0标签部署版本；060 joint-free作为历史基线。

结果：Oracle固定prior能提高真实R2，但仍未过门槛。n=960 Oracle synthetic delta MAE=0.407；真实R2仅0.307/0.097。BBSE实际prior非常准（L1=0.023/0.031），因此060的主要瓶颈不是BBSE，而是当前Gaussian latent mixture / 12维mean-shift表示本身。

0 API、未使用reserved、未自动commit/push。
