# 025 成果入口

唯一必读[中文主报告](report.md) · [当前状态](CURRENT_STATUS.md) · [审计交接](audit_handoff.md)。执行及自检完成，尚未独立审计。

- [事前协议](protocol_001.md)、[冻结输入与特征](preparation_001/source_manifest.json)。
- 正式结果analysis_003：[全队列指标](analysis_003/full_metrics.csv)、[操作点及区间](analysis_003/summary.json)、[完整global-λ曲线](analysis_003/global_lambda_curves.csv)、[OOF排序曲线](analysis_003/gate_curves.csv)、[OOF逐候选](analysis_003/candidate_oof.csv)、[训练隔离记录](analysis_003/fit_audit.json)。
- [主图](figures_002/024_D_risk_rescue.png)、[Qwen辅助图](figures_002/024_Q_risk_rescue.png)，同目录SVG可用于论文。
- [门槛可评估性说明](interpretation_001/gate_scope.json)、[补充确定性/混合区间](interpretation_001/operating_uncertainty.json)。
- [自检](verification_001/checks.json)、[离线重放](verification_001/replay.json)。analysis_001/002和figures_001是保留的工程中间版本，不是当前正式结果。

无API、无reserved40、不改变λ、不自动后续。
