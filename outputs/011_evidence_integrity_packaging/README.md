# 011成果入口

**精简独立审计PASS，可冻结／结项。** 建议停止当前B/C规则组合扩展，保留冻结C48对照；没有证据将B整体作为新性能baseline或扩大C。唯一必读：[简明中文主报告](report.md)。

650条已离线构建/检查；24条三臂各三轮诊断完成，195个独立请求全部有效。C−B净正确数−1/0/0、B−A为−2/0/0，未达到预设继续门槛，**650条main没有执行**。费用按usage估算¥1.2873834＜40；不新增患者，009/010保持冻结。

|用途|入口|
|---|---|
|固定规则与范围|[执行协议](execution_protocol_001.md)、[授权登记](authority_001.json)、[650条离线摘要](offline_003/summary.json)、[预设小组](offline_003/pilot_selection.json)|
|真实结果与停止判定|[pilot摘要](pilot_analysis_001/summary.json)、[门槛结果](pilot_analysis_001/gate.json)、[每轮指标](pilot_tables_001/results.md)、`live/pilot`原生回执|
|患者/类别/重复|[重复标签](pilot_analysis_001/repeats.json)、[患者/类别计次](synthesis_001/)、[完整配对区间](pilot_tables_001/paired.csv)|
|输入完整性与挤占|[全量来源/重叠检查](input_diagnostics_001/summary.json)、[正文和结构分别命中](input_context_diagnostics_001/anchors.json)、[45例收费前检查](offline_review_003/reading_conclusion.json)|
|完整案例|`pilot_review_001`保存24条全部输入/输出；[8例阅读诊断](case_analysis_001/cases/)、[27处原文锚点](case_analysis_001/anchors.json)|
|复现与交审|[执行验证](verification_001/verification.json)、[交审说明](audit_handoff.md)、[实际文件指纹](handoff_001.json)、[任务/运行说明](../../tasks/011_evidence_integrity_packaging/README.md)|

`offline_001/002`及`offline_review_001/002`是收费前历史草稿，对应代码保存在`development_history_001/002`，不是当前实验规则。正式输入只用`offline_003`。`main_preparation_001`只是门槛通过时的预备方案，**不是待补跑实验**；当前阶段门槛已明确拒绝继续。案例解释不是新医生GT，执行自查不是独立审计PASS；交审后停止改动同批成果。

当前状态：2026-09-15[精简独立审计PASS](../../reviews/011_evidence_integrity_packaging.md)，可冻结／结项；历史报告与交审说明中的等待状态保留。
