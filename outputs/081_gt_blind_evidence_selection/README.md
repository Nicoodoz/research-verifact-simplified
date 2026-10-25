# 081 输出入口

- [中文主报告](report.md)：决策、主比较、重复诊断、局限与费用。
- [事前协议](../../tasks/081_gt_blind_evidence_selection/protocol.md)、[样本冻结](sample_freeze.json)、[盲样本与C48/原包](sample_blind.jsonl)、[患者清单](patients.csv)、[暴露清单](overlap_manifest.jsonl)。
- [U最终包冻结](u_packs_freeze.json)、[T最终包冻结](t_packs_freeze.json)、[交错Judge冻结](judge_extra_freeze.json)。`*_jobs.jsonl`及`attempts/`保存所有原始请求和回执；不要运行覆盖历史目录的旧生成器。
- [主机器结果](results.json)、[逐例结果](case_results.jsonl)、[证据干预分类](teacher_intervention_events.jsonl)。
- [重复触发与样本冻结](repeat_decision.json)、[重复机器结果](repeat_results.json)、[逐例重复](repeat_case_results.jsonl)。首轮主回答不可被重复回答替换。
- [历史暴露敏感性](overlap_sensitivity.json)、[全任务费用账本](cost_ledger_final.json)、[执行者自检](self_check.json)、[交审说明](audit_handoff.md)。

本任务没有独立审计；研究结项时未自动提交，随后用户另行授权推送；不启动082。
