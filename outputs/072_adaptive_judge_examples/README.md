# 072 输出索引

- [中文总报告](report.md)、[当前状态](CURRENT_STATUS.md)、[确认后决策](confirmation_decision.md)、[执行者自检](verification.json)
- [首次冻结](freeze.json)、[教学示例池](example_pool.jsonl)、[来源范围说明](source_scope_note.md)、[目标盲输入](target_blind.jsonl)、[目标GT台账](target_gt.jsonl)、[探索/确认动态选择](dynamic_selections.jsonl)、[确认动态选择](confirmation_dynamic_selections.jsonl)
- [探索请求](pilot_jobs.jsonl)、[探索执行摘要](pilot_execution_0144.json)、[探索分析](pilot_analysis.json)、[探索预测](pilot_predictions.jsonl)、[探索逐例材料](pilot_changed_cases.jsonl)、[探索同体敏感性](pilot_same_body_sensitivity.json)
- [阶段1选择依据](pilot_decision.md)、[选择机器记录](pilot_decision.json)、[确认冻结](confirmation_freeze.json)、[确认预算说明](confirmation_budget_note.md)、[确认请求](confirmation_jobs.jsonl)、[确认执行摘要](confirmation_execution_0324.json)
- [确认分析](confirmation_analysis.json)、[确认预测](confirmation_predictions.jsonl)、[确认逐例材料](confirmation_changed_cases.jsonl)、[确认同体敏感性](confirmation_same_body_sensitivity.json)、[071/072同体历史比较](anchor_071_072_comparison.json)
- [完整逐次请求与脱敏回执](attempts)、[逐阶段费用汇总](cost_summary.json)、[交审说明](audit_handoff.md)

任务脚本及前置协议见`tasks/072_adaptive_judge_examples/`。探索与确认分开报告；072的阳性绝对分数不等于动态选择有净增量，不使用reserved，不自动073。
