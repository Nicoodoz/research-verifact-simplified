# 005：结果入口

原主报告及交审／自查文件保留当时状态，当前完成状态以本入口和审计为准。后续研究见[009入口](../009_retrieval_baselines/README.md)，不自动重新执行原“下一步”建议。

**已通过2026-09-14独立审计，无阻塞修正；依据见[审计记录](../../reviews/005_pilot_effect_analysis.md)。** 请优先阅读唯一的 [简明中文主报告](run_002/review_002/report.md)。本任务只分析 004 已有材料，没有新增推理、补跑失败或使用保留测试病例。

全量统计覆盖 421 条；58 条两臂标签变化中，LLM 改对 13、改错 9，human 改对 12、改错 21、换标签仍错 3。深入阅读 25 例的完整输入/两臂完整输出，并补读 13 个原文来源片段；C17 另读整份原 BHC 确定操作指代。本任务的发现与当时推荐以主报告为准，当前方向见009，原文上下文不是临床证据，分析标签不是医生 GT。

| 用途 | 入口 |
| --- | --- |
| 唯一用户主报告 | [report.md](run_002/review_002/report.md) |
| 25 例及观察、假设、未解决处 | [case_index.csv](run_002/review_002/case_index.csv) · [cases](run_002/review_002/cases/) |
| 原文/完整输出锚点和阅读声明 | [evidence_anchors.json](run_002/review_002/evidence_anchors.json) · [review_notes_snapshot.json](run_002/review_002/review_notes_snapshot.json) |
| 完整队列转移与统一评价 | [all_transitions.csv](run_002/all_transitions.csv) · [metrics.json](run_002/metrics.json) · [transition_counts.csv](run_002/transition_counts.csv) |
| 患者、医生一致性与格式描述性计数 | [patient_counts.csv](run_002/patient_counts.csv) · [annotation_counts.csv](run_002/annotation_counts.csv) · [adherence_counts.csv](run_002/adherence_counts.csv) |
| 原始材料与固定选例 | [selected_cases.csv](run_002/selected_cases.csv) · [packets](run_002/packets/) · [完整 reference 阅读并集](run_002/reference_unions/) |
| 事后补读上下文的范围与源文件 | [context_request.json](run_002/context_request.json) · [source_context.json](run_002/source_context.json) |
| 来源/代码/产物指纹 | [提取 manifest](run_002/manifest.json) · [报告 manifest](run_002/review_002/manifest.json) |
| 重复生成、测试与最终版本 | [verification.json](verification_001/verification.json) · [tests.log](verification_001/tests.log) · [review_version.json](verification_001/review_version.json) |
| 任务设计与复现命令 | [任务说明](../../tasks/005_pilot_effect_analysis/README.md) |

104 项测试通过（005 新增 6 项）；两次提取的 86 个内容文件、两次最终报告渲染的 30 个文件逐字节一致；265 处证据/输出锚点及来源上下文通过自查。完整指标与 004 相同，自查不构成独立审计或新的医学判定。

历史记录：run_001 为初次提取的部分产物，因比较对象缺少 004 附加的转移计数字段而停止，说明见 [error.json](run_001/error.json)，选例与正式 run_002 一致。run_002 是正式提取，run_003 为重复提取。run_002/review_001 是报告呈现初稿，review_002 是现行主报告，review_003 是其重复渲染；临床解释与选例没有因这些呈现修订改变。旧 run、004 回执及独立 reviews 保留，不回写历史状态。
