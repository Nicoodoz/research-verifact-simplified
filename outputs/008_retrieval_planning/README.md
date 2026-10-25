# 008 成果入口

原主报告及交审／自查文件保留当时状态，当前完成状态以本入口和审计为准。后续研究见[009入口](../009_retrieval_baselines/README.md)，不自动重新执行原“下一步”建议。

**已通过2026-09-14精简独立审计，无阻塞修正；依据见[审计记录](../../reviews/008_retrieval_planning.md)。优先只读 [简明中文主报告](run_001/report.md)。** 有局部证据补充，但未证明 planner 的稳定独立收益；008当时建议检查候选融合与证据组织；009已完成基础对照，目前优先证据组织，暂缓扩大通用planner。

六名新开发患者、144 条 claim，三臂各 144 条有效预测。Planner−direct 的 ΔMCC 为 LLM +0.0176、human 0，两个患者区间跨 0；12 次预设重复无翻转。全部服务共 684 次，按 usage 估算 **¥4.1528＜¥40**，不是账单。100 个计划使用、44 个按预设退回；不能以格式失败推断模型未理解。

- [固定协议](execution_protocol_001.md) · [输入与估算](preparation_001/summary.json) · [40 元长期授权的本次登记](authority_001.json)
- [统一评价](run_001/analysis/metrics.json) · [全量转移](run_001/analysis/transitions.csv) · [分阶段费用](run_001/analysis/costs.json)
- [20 例阅读范围](run_001/review_001/semantic_003/coverage.json) · [执行者语义记录](run_001/review_001/semantic_003/notes_snapshot.json) · [79 处锚点](run_001/review_001/semantic_003/evidence_anchors.json)
- [候选融合/截取链路](run_001/diagnostics_001/case_candidate_gates.json) · [原记录日期覆盖](run_001/diagnostics_001/corpus_availability.json) · [接口诊断](planner_diagnostics_001/summary.json)
- [断网离线重建与评分](verification_001/verification.json) · [交审文件清单](handoff_001.json)

`live/` 保存五阶段不可改写的原生回执。无 API 预检、答案补跑、原数据或历史 run 修改；统一评价实现、独立审计意见和 `.gitignore` 未变。阅读材料 `semantic_001` 因嵌套 manifest 写入异常不作为当前版本，`semantic_002` 的 P097 接口归因在自查中更正；**semantic_003** 是正式阅读版本，指标均未改变。

离线复核使用：`python -B tasks/008_retrieval_planning/verify.py --output outputs/008_retrieval_planning/verification_local`，输出目录必须不存在，不调用 API。当时基准HEAD及未提交成果见历史交审清单；当前独立状态见上方审计记录。
