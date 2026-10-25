# 007：上下文辅助检索

原主报告及交审／自查文件保留当时状态，当前完成状态以本入口和审计为准。后续研究见[009入口](../009_retrieval_baselines/README.md)，不自动重新执行原“下一步”建议。

**已通过2026-09-14精简独立审计，无阻塞修正；依据见[审计记录](../../reviews/007_context_retrieval.md)。只需优先阅读 [简明中文主报告](run_001/review_001/semantic_001/report.md)。** 有目标关系和零命中补充召回的局部信号，但主比较无稳定净收益，不能直接确立论文主线。

96 条 claim 四臂＋8 个重复基线共 392 次有效回答，另有事后零预算边界的 3 例四臂 12 次补充，均有效；总估算 ¥4.1703＜¥16，非已核对账单。主 mixed−claim 的 ΔMCC 为 LLM +0.0089、human −0.0718，两个区间均跨 0。原主结果保留，不用补充对照替换；同输入 Judge 分歧与查询召回收益分开。

- [完整主指标](run_001/analysis/metrics.json) · [逐例转移](run_001/analysis/transitions.csv) · [描述性诊断](run_001/diagnostic_summary.json)
- [18 例主分析＋3 例补充的执行者记录](run_001/review_001/semantic_001/notes_snapshot.json) · [377 处原文锚点](run_001/review_001/semantic_001/evidence_anchors.json)
- [零预算补充的登记与授权](zero_budget_sensitivity_001/protocol_and_authority.json) · [补充结果](zero_budget_sensitivity_001/summary.json)
- [124 项测试与首次离线重放](verification_001/verification.json) · [文档同步后重放](verification_002/verification.json) · [实际交审版本](verification_001/handoff.json)

- [任务说明与运行前方案](../../tasks/007_context_retrieval/README.md)
- [正式冻结输入 preparation_003](preparation_003/manifest.json) · [样本与费用概览](preparation_003/summary.json)
- [122 项离线测试与输入检查](offline_checks_004/checks.json) · [旧病例检索标记](offline_checks_004/old_case_markers.json)

此前 preparation_001/002 均未发送，原因见各自 status JSON；旧病例标记不作为医生 gold evidence。初始 8 项 API 费用规则修改保留，001–006 历史实验/原始回答和独立意见保持不变。自查与独立审计分别记录；当前独立结论见上方审计链接。
