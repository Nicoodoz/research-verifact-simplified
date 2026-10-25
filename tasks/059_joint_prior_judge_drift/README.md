# 059：Joint Prior and Judge-drift Estimation

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/059_joint_prior_judge_drift/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

059研究target 0标签时，能否从DeepSeek+Qwen soft scores同时估类别比例与Judge漂移方向/幅度。

Judge漂移先压成4个可解释参数：DeepSeek/Qwen各自的Supported bias与NS-vs-NA bias。利用联合log-odds协方差估prior，再由均值残差估theta。

Synthetic n=960恢复良好：prior L1 0.074、theta MAE 0.085、非零方向识别99.66%。

但真实052↔053的Judge变化高度class-specific，global 4参数模型只能解释约17%的类条件均值漂移能量，因此事前真实R2门槛失败，不进入060。

0 API、未用reserved、15项executor verification PASS；独立审计未执行。
