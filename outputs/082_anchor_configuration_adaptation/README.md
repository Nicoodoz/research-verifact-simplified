# 082结果入口

- [中文总报告](report.md) · [执行摘要](executive_summary.md) · [交审说明](audit_handoff.md) · [执行者自检](selfcheck.json)
- 冻结：[盲样本](blind_freeze.json) · [费用计划](cost_plan.json) · [训练选择](training_selection.json) · [主模型](models_frozen.json) · [评价前绑定](evaluation_apply_freeze.json)
- 结果：[逐例预测](evaluation_predictions.jsonl) · [主评价](evaluation_results.json) · [重复](repeat_results.json) · [完整费用台账](cost_ledger.json) · [图](figure_082.png)
- 补充：[标签使用](label_use_ledger.json) · [曝光审计](exposure_audit.json) · [来源登记](source_manifest.jsonl) · [有效配对视图](training_effective.json) · [共同核心有效](common_core_valid_sensitivity.json) · [暴露子集](sensitivity_results.json) · [权重敏感性](unweighted_sensitivity_results.json) · [机制配对](diagnostic_pairs.json)
- 原始新调用保留在`attempts/`；缓存只复用请求体SHA完全一致的历史HTTP200回执。协议与实现见[任务目录](../../tasks/082_anchor_configuration_adaptation/README.md)。

默认系统维持B＋Frozen PriorG。082未使用reserved，未改历史冻结工件，不自动启动后续编号；自检PASS，独立审计未执行。
