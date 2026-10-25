# 069 输出索引

- [中文主报告](report.md)：研究问题、受控操作、稳定性、停止决策与费用。
- [当前状态](CURRENT_STATUS.md)：可快速引用的结论与边界。
- [067 更正说明](067_correction.md)：v1/v2 来源和实现冲突；历史工件保持原样。
- [审计交接](audit_handoff.md)：请求、回执、指纹和独立复核重点。
- `preflight.json`／`preflight_cases.jsonl`：10 条 066 C48 内修复病例的原包映射与构造可行性。
- `freeze.json`／`stage1_jobs.jsonl`／`stage1_controls.jsonl`：第一步收费前冻结的五条件清单与上界。
- `stage1_results.jsonl`／`stage1_analysis.json`：48 次核心请求的逐例与汇总。
- `repeat_freeze.json`／`stage1_repeat_jobs.jsonl`：按事前规则冻结的 16 次成功条件重复。
- `stage1_final_cases.jsonl`／`stage1_final_analysis.json`／`stage2_gate.json`：严格稳定性、未过门槛与停止依据。
- `stage2_cohort_blind.jsonl`／`stage2_cohort_evaluation.csv`：条件触发的另一批 development 候选，**未运行选择器或 Judge**。
- `attempts/`、`execution_stage1.json`、`execution_repeat.json`：全部请求、回执与累计费用。
- [执行者自检](verification.json)：574 PASS、0 FAIL；独立审计未执行。
