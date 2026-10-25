# 029 已有语义信息的Gate增量实验

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/029_semantic_information_gate/report.md)。 独立结论查[审计末尾](../../reviews/029_semantic_information_gate.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

[冻结协议](protocol.md) · [固定配置](config.json)。使用用户独立环境 `research-verifact-029`，不修改原环境。

正式准备完成后，单入口运行：

```powershell
conda run --no-capture-output -n research-verifact-029 python -u -B tasks/029_semantic_information_gate/run029.py --run-id run_001
```

当前非登录shell未配置conda命令，可用等价绝对路径 `E:/miniconda3/Scripts/conda.exe`；无需改PATH或环境。新运行必须换全新run-id，已有目录拒绝覆盖。重放仍会在独立环境重新拟合固定模型，不含任何API。

本次通过以下一次性后台入口启动，stdout/stderr保存在独立launch目录，关闭Codex会话后仍由Windows进程自行执行：

```powershell
pwsh -NoProfile -File tasks/029_semantic_information_gate/launch029.ps1 -RunId run_001
```

该命令不监控、不循环、不自动重启；同run-id重复启动会拒绝。`preflight_001/tests.txt`保存启动前8项合成测试结果。

启动前只需一次 `prepare029.py`（已存在的冻结目录拒绝重建）；冻结后源码/配置/环境版本变化将阻断执行，不允许据成绩改配置。

程序自动运行12条件（8主比较＋4去引用/格式特征消融）、16折患者嵌套OOF、两方向迁移、002指标、1000次固定预测患者bootstrap、完整global包络及冲突检查。每折落盘，异常保存traceback和failed状态，不自动改参数、补跑或覆盖旧run。

机器结果：`outputs/029_semantic_information_gate/<run-id>/`。优先读 `RUN_STATUS.md` / `execution_status.json`，后读各scope的evaluation。`predictions.json/csv`为每条件候选预测；`fold_*.json`包含内外训练ID、scaler、模型参数、阈值及fallback；`full_predictions.csv`含全部claim；`metrics.json/csv`、`patients.csv`、`transitions.csv`、`curves.csv`、`matched_risk.json`、`matched_bootstrap.json`、`ranking.json`、`conflicts.csv`及`bootstrap_draws.json`足以继续科学分析。

不自动选择winner、不写长篇报告、不自动审计/commit/push/030或reserved40。Codex启动后不轮询值守。
