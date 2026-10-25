# 062：Low-rank Empirical Transport

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/062_low_rank_empirical_transport/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

062测试：固定BBSE prior后，能否用非Gaussian的经验分布RFF/MMD匹配，从0标签target恢复低秩class-specific Judge drift。

主模型rank-1 delta_y=a_y v；source-null fit/holdout校准防止无漂移时产生伪漂移。rank-2仅作诊断。

结果：none false-accept降到0%，说明防伪成功；但n=960四个rank-1真值pattern平均accept仅58.75%，active MAE 0.607，sign 55%，事前门槛FAIL。S类漂移较易恢复，NS/NA少数类明显困难。

真实052↔053的GT mean-shift矩阵确实高度低秩（rank-1能量90.24%，rank-2 99.46%），但rank-1/rank-2的GT-blind heldout gain两方向均未超过source-null阈值，因此全部安全回退。

0 API、未使用reserved、21项executor verification PASS；独立审计未执行。
