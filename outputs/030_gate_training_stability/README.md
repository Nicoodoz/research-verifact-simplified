# 030 运行与进度入口

**当前：自动程序全部完成；用户随后明确授权收尾，中文主报告、自检和交审材料已完成，待独立审计。** 原运行时RUN_STATUS及冻结协议保留当时约定。

唯一必读：[中文主报告](report.md)。另见[当前状态](CURRENT_STATUS.md)、[交审说明](audit_handoff.md)、[收尾核验](closeout_001/checks.json)。

- [冻结协议](preparation_001/protocol.md) · [组合配置](preparation_001/config.json) · [原029学习配置](preparation_001/learning_config.json)
- [完整训练/测试计划](preparation_001/units.jsonl) · [各组合实际R/risk](preparation_001/unit_summary.csv) · [数据与组合计数](preparation_001/scope.json)
- [输入和代码指纹](preparation_001/manifest.json) · [环境](preparation_001/environment.json) · [启动前测试](preflight_001/tests.txt)
- [运行状态](run_001/execution_status.json) · [启动记录](launch_run_001/launch.json) · [最近日志](launch_run_001/stdout.log) · [错误日志](launch_run_001/stderr.log)
- 完成/失败后自动生成 [RUN_STATUS.md](run_001/RUN_STATUS.md)，异常另存 [errors.json](run_001/errors.json)。未完成时不预写研究结论。

## 人工查看进度

在PowerShell中执行：

```powershell
Set-Location D:\Research-VeriFact
Get-Content outputs/030_gate_training_stability/run_001/execution_status.json -Raw
Get-Content outputs/030_gate_training_stability/launch_run_001/stdout.log -Tail 15
```

`state`：running=正在运行，completed=完成，failed=失败。`stage`显示阶段；模型数和轮次数是训练进度，之后还会继续bootstrap/稳定性统计。`updated_utc`为UTC时间，加8小时为北京时间。无需重新运行任何启动命令。

## 机器结果

- `run_001/models/`：所有唯一训练集合的内外Logistic参数、scaler、阈值、训练ID及内层OOF。
- `run_001/sweeps/`：单患者完整测试结果、155候选预测、1529条全队列评价、作者/队列分层、曲线、逐患者和留一测试患者诊断；重复计划只作alias。
- `run_001/analysis/learning_curves.csv`、`source_comparison.csv`、`matched_risk.csv`：预定规模和来源结果。
- `candidate_stability.csv`、`source_paired_contrasts.csv`、`training_patient_inclusion.csv`、`ranking_correlations.csv`：真实重训后的动作/概率/阈值波动。
- `size_source_summary.json`：经验组合范围，不是独立样本CI；`conditional_patient_bootstrap.json`：固定各重训结果后重抽测试患者的条件区间。

重复组合不当新增患者，k14只有一个独特组合/held，不能据零波动证明组成稳健。0 API、无新特征、无新分类器，不改原环境，不使用reserved40，不自动commit/push或后续研究。
