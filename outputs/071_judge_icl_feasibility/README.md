# 071 输出索引

## 现行解读（2026-09-23，结项后的用户原则）

071保留为**首轮development阳性候选**：固定四示例、96条最终E/B正确83/78，5救回0伤害，false-S均3；尚未证明重复性或具体证据关系学习。用户已经决定按首轮结项，不自动恢复原192次重复。

后续研究不再默认以全量同体重复作为继续前提，普通网络故障按预算内有限重试自动恢复。见[研究执行原则](../../docs/RESEARCH_EXECUTION.md)。下方旧预算gate、停发和续跑描述只记录071历史执行，协议、回执及报告保持不变；新原则不等于旧runner已实现自动恢复，也不自动启动072。

- [中文报告](report.md)、[当前状态](CURRENT_STATUS.md)、[逐例审阅](stage1_case_review.md)、[全部 18 条改变正确性的原始核查材料](stage1_changed_cases.jsonl)
- [事前冻结](freeze.json)、[教学示例及来源](examples.jsonl)、[盲评价输入](evaluation_blind.jsonl)、[评价 GT 台账](evaluation_gt.jsonl)、[提示来源比较](prompt_comparison.md)
- [首轮请求](main_jobs.jsonl)、[恢复请求](recovery_jobs.jsonl)、[恢复映射](recovery_mapping.json)、[续跑冻结](continuation_001_freeze.json)、[预检请求](preflight_body.json)
- [逐次请求及脱敏回执](attempts)、[首次通信停发快照](execution_diagnosis.json)、[最终首轮执行摘要](main_execution_0295.json)、[费用台账摘要](cost_summary.json)、[结项补充](../../tasks/071_judge_icl_feasibility/closure_001.md)
- [首轮统一评价](stage1_analysis.json)、[逐例预测](stage1_predictions.jsonl)、[事前效果和预算 gate](stage1_gate.json)、[执行者自检](verification.json)、[交审说明](audit_handoff.md)

首轮方法效果有正向信号，但 20 元预算 gate 阻止预设重复；用户决定按现有结果结项。不称为稳定提升或方法成功。`tasks/071_judge_icl_feasibility/` 中保留协议、续跑登记与可复核脚本。当前不再发送收费请求，不自动 072。
