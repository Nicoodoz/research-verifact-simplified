# 035：支持边界与置信度解耦

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/035_lambda_boundary_calibration/report.md)。 独立结论查[审计末尾](../../reviews/035_lambda_boundary_calibration.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

本任务研究固定 lambda=2 为什么有效、lambda 是否应自动学习，以及概率置信度是否可以在不改变分类标签的情况下单独修正。

## 核心方法

- U2：固定 lambda=2。
- U2+T：固定 lambda=2 后仅拟合正温度 T，保持 argmax 标签不变。
- Joint_NLL：在同一低维参数空间联合拟合分数尺度和 Supported 偏置。
- Task_T：在 PA 不低于 U2、false-S 不高于 U2 的工作点中选择 MCC，并拟合 T。
- Robust_T：在相同约束下使用患者重抽样的较差分位表现选择 lambda，再拟合 T。
- MCC_T：执行后增加的探索性对照，仅按训练患者 MCC 选择 lambda，不参与预定主结论。

全部实验离线复用既有评分，0 API、不用 reserved40。

## 运行与复核

使用 `research-verifact-029` 环境：

```powershell
E:\miniconda3\envs\research-verifact-029\python.exe -B tasks\035_lambda_boundary_calibration\test_extension.py
E:\miniconda3\envs\research-verifact-029\python.exe -B tasks\035_lambda_boundary_calibration\verify035.py
```

正式预定六方法结果为 `outputs/035_lambda_boundary_calibration/run_001`；`run_002`加入探索性MCC_T，并精确复现run_001的六方法指标。

主报告：`outputs/035_lambda_boundary_calibration/report.md`。
