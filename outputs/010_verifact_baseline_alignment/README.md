# 010 成果入口

**2026-09-15精简独立审计PASS，可冻结／结项。** 复用009确认650条命题，两套reference均完整；保留C48作为实用对照，建议下一阶段单独验证证据身份/条件完整性，未证明新packaging方法有效。009保持冻结，无新患者。

唯一必读：[简明中文主报告](report.md)。发布reference−C48的同期ΔMCC为LLM −0.0572、human −0.0497，两区间跨0；human PA/AC1区间倾向C48。较高的发布系统历史PA不能直接归因检索。所有调用已停止，预计/保护上限为¥33.05/¥40，最终usage估算加未知请求预留¥23.4671，非账单。

|用途|入口|
|---|---|
|设计、输入与发布配置核实|[执行前协议](execution_protocol_001.md)、[输入摘要](preparation_001/summary.json)、[release绑定](preparation_001/release_binding.json)、[授权/冻结记录](authority_001.json)|
|真实回答与评分|`live/judge/` 原回执、[评分摘要](analysis_001/summary.json)、[完整配对指标](analysis_001/metrics.json)、[核心表](tables_001/core_results.md)|
|证据与案例|[全量结构](reference_diagnostics_001/summary.json)、[metadata追溯](metadata_linkage_001/summary.json)、[34例解释及完整输入/输出](review_002/semantic_001/)、[原文条件核对](additional_diagnostics_001/N642_raw_condition.json)|
|波动、费用及患者|[重复诊断](analysis_001/repeat_diagnostics.json)、[跨运行C48](analysis_001/cross_run_c48_drift.json)、[费用拆分](additional_diagnostics_001/cost_breakdown.json)、[逐患者差值](additional_diagnostics_001/patient_differences.csv)|
|复现与独立审计|[交审说明](audit_handoff.md)、[实际版本指纹](handoff_001.json)、[150项断网测试和重放](verification_001/verification.json)、[任务代码说明](../../tasks/010_verifact_baseline_alignment/README.md)|
|论文材料|[设置与定位草稿](paper_materials.md)、[表格CSV](tables_001/)|

`review_001`是初选26例快照；`review_002`补入全部剩余8条原NS且两臂标签不同的命题，正式解释为`review_002/semantic_001`。`reading_001`仅保存阅读过程，最终结论以主报告及正式案例页为准。原始reference不是医生gold，病例观察不是医学重新标注。执行者未写独立审计PASS；审计期间停止修改本批成果。

当前独立状态见[010审计记录](../../reviews/010_verifact_baseline_alignment.md)。主报告和交审快照中的“等待审计”保留历史状态，150项测试及53个内容文件重放已由独立审计核对。
