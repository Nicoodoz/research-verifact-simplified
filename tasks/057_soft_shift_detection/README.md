# 057：Soft Multi-view Conditional-shift Detection

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/057_soft_shift_detection/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

057测试056的hard-label detector失败是否主要因为连续score信息被压掉。

固定主方法：
- DeepSeek Frozen PriorG hard output → BBSE估target prevalence；
- DeepSeek T-S + Qwen共6维连续scores；
- source-only z-score + RBF Random Fourier Features；
- 比较target soft mean embedding与按BBSE prior重混合的source类条件embedding；
- source纯label-shift重采样给出95% alarm阈值。

结果：soft detector较056 hard detector明显提升conditional-replacement检测率，但n=240两方向仅64.43%和56.57%，仍未达到事前70%门槛；真实052↔053两方向也均未报警。

因此057证明hard压缩确实损失信息，但当前soft multi-view信号仍不足以作为zero-label动态适配的安全开关。0 API、未使用reserved、未自动commit/push。
