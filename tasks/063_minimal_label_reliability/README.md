# 063：Minimal-label Target Reliability Calibration

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/063_minimal_label_reliability/report.md)。 下文自检不自动代表独立审计。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

063测试target标签预算0/5/10/20/40，比较random、unlabeled active与oracle-balanced采样，目标是补齐zero-label无法恢复的conditional reliability。

主方法用Frozen PriorG×Qwen U0的9种hard joint pattern做Bayesian reliability更新；正式失败。

Protocol Amendment 001进一步保留4维soft log-odds，用few labels直接更新target class means；仍然失败。

两种方法即使oracle-balanced 40 labels也没有在052→053和053→052两个方向同时满足预注册安全改善标准。失败主要表现为false-S上升、NS recall下降。

因此063不能给出“5/10/20/40哪个够”的正阈值；当前证据说明calibrator/decision rule而非单纯标签量是瓶颈。

24项executor verification PASS；0 API；未使用reserved；独立审计未执行。
