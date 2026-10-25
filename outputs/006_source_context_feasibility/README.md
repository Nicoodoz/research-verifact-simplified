# 006：局部来源上下文可行性验证

原主报告及交审／自查文件保留当时状态，当前完成状态以本入口和审计为准。后续研究见[009入口](../009_retrieval_baselines/README.md)，不自动重新执行原“下一步”建议。

**已通过2026-09-14精简独立审计，无阻塞修正；依据见[审计记录](../../reviews/006_source_context_feasibility.md)。** 只需优先阅读 [简明中文主报告](run_001/review_001/semantic_001/report.md)。建议修改切入点，暂不扩大当前来源上下文方案；没有确立方法收益或论文贡献。

获用户批准后，在 2 名新开发患者的固定 64 条命题上实际尝试三臂 192 个请求：190 个收到回答、189 个有效预测。2 个通信未知、1 个截断均保留失败，未补标签或重跑答案。预算占用约 ¥3.8661＜¥8，不是已核对账单。两个主比较均受缺失阻塞；human 来源−重复的完整 ΔMCC +0.0326，区间跨 0，伴随 NS/NA 召回下降。原医生标签按独立命题形成，补入来源上下文不保证目标/GT 对应不变。

| 资料 | 入口 |
| --- | --- |
| 当前唯一主报告 | [report.md](run_001/review_001/semantic_001/report.md) |
| 授权、实际执行及中断处理 | [authorization](authorization_001.json) · [continuation_summary](run_001/continuation_summary.json) · [追加登记](execution_amendment_001.json) |
| 统一评价、完整覆盖及全量转移 | [metrics](run_001/analysis/metrics.json) · [transitions](run_001/analysis/transitions.csv) |
| 28 例完整输出/证据分析 | [病例索引](run_001/review_001/case_index.csv) · [语义记录](run_001/review_001/semantic_001/notes_snapshot.json) · [316 处锚点](run_001/review_001/semantic_001/evidence_anchors.json) |
| 执行自查及实际交审版本 | [verification](verification_live_001/verification.json) · [handoff](verification_live_001/handoff.json) |
| 运行前研究问题、方案、边界与预算 | [历史准备报告](preparation_001/report.md) · [任务说明](../../tasks/006_source_context_feasibility/README.md) |
| 相关论文/标注流程与旧病例补查 | [依据记录](../../tasks/006_source_context_feasibility/research_notes.md) · [public source files](../../docs/sources/006_source_context_feasibility/) |
| 固定样本与原生请求 | [cohort.csv](preparation_001/cohort.csv) · [inputs.jsonl](preparation_001/inputs.jsonl) · [requests.jsonl](preparation_001/requests.jsonl) |
| 输入语义风险（非 GT） | [input_scope_notes.json](../../tasks/006_source_context_feasibility/input_scope_notes.json) |
| 113 项离线测试与重复准备 | [verification.json](verification_offline_001/verification.json) · [tests.log](verification_offline_001/tests.log) |
| 发送前版本清单 | [execution_readiness.json](preparation_001/execution_readiness.json) |

preparation_001 是本次执行的冻结输入；preparation_002 是逐字节一致的重复准备。offline_review_001 仅含 005 已读患者的局部补查，不作为新验证队列。run_001/run_summary.json 保留首次暂停快照，最终调度见 continuation_summary；有效标签数见离线 analysis，全部失败身份见 verification。上述执行自查不等于独立审计通过。旧任务、历史 run、原始回答及独立审计均保持不变。
