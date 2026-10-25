# 030：固定Gate训练规模与患者组成稳定性

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/030_gate_training_stability/report.md)。 独立结论查[审计末尾](../../reviews/030_gate_training_stability.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

[协议](protocol.md) · [组合配置](config.json)。只用029已冻结A/B/D Logistic；0 API，不改原环境，不新增特征或模型。

独立环境：research-verifact-029。单一前台入口（只供复现；须新run-id）：

```powershell
conda run --no-capture-output -n research-verifact-029 python -u -B tasks/030_gate_training_stability/run030.py --run-id run_001
```

本次使用一次性后台入口，Windows进程在Codex结束后继续运行：

```powershell
pwsh -NoProfile -File tasks/030_gate_training_stability/launch030.ps1 -RunId run_001
```

首次冻结由preflight030.py检查合成测试后完成。源码/config/输入/环境版本改变将被runner拒绝。run与launch目录均拒绝覆盖；失败保留现场，不自动重试。非登录shell可用 `E:/miniconda3/Scripts/conda.exe` 替代conda命令，不需更改环境。

## 人工查看进度

在项目目录执行以下任一命令即可，不需要重新启动程序：

```powershell
Get-Content outputs/030_gate_training_stability/run_001/execution_status.json -Raw
Get-Content outputs/030_gate_training_stability/launch_run_001/stdout.log -Tail 15
Get-Content outputs/030_gate_training_stability/launch_run_001/stderr.log -Tail 20
```

`state=running`表示正在执行，`completed`表示完成，`failed`表示失败；`stage`说明阶段，`completed_unique_sweeps/total_unique_sweeps`和`unique_models_saved/total_unique_models`说明训练进度。训练完成后仍需bootstrap和稳定性统计，此时stage继续更新，不能仅凭模型数达到总数判断已完成。时间均UTC，北京/香港时间加8小时。

完成或失败后自动出现 `run_001/RUN_STATUS.md`；失败另有 `errors.json`。进程PID保存在status，必要时可手动 `Get-Process -Id <pid>`核对；暂时没更新不等于失败，较大的统计阶段可能耗时。请勿重复运行launch造成第二个任务。

## 输出

`preparation_001`包含字节一致的029输入、全部GT盲患者计划/ID/实际训练R-risk、特征schema和hash。`run_001/models`保存所有唯一训练集合的内外模型/阈值；`sweeps`保存测试单元、正式全队列预测和曲线；`analysis`保存训练规模、来源、bootstrap及候选决策翻转统计。重复k14计划只保存alias，不伪造20次独立训练。

本轮自动程序不生成正式长报告、不选择winner、不自动031/reserved40、commit或push。科研解释与独立审计留待后续明确指令。
