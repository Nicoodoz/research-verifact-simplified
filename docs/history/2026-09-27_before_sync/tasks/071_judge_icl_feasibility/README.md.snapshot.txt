# 071：医生标注示例驱动的 Judge 上下文学习可行性验证

## 现行解读（2026-09-23，结项后的用户原则）

071保留为**首轮development阳性候选**：固定四示例、96条最终E/B正确83/78，5救回0伤害，false-S均3；尚未证明重复性或具体证据关系学习。用户已经决定按首轮结项，不自动恢复原192次重复。

后续研究不再默认以全量同体重复作为继续前提，普通网络故障按预算内有限重试自动恢复。见[研究执行原则](../../docs/RESEARCH_EXECUTION.md)。下方旧预算gate、停发和续跑描述只记录071历史执行，协议、回执及报告保持不变；新原则不等于旧runner已实现自动恢复，也不自动启动072。

[事前协议](protocol.md)在任何 071 付费调用前冻结。[中文报告](../../outputs/071_judge_icl_feasibility/report.md)说明首轮 B/E/C 结果、预算 gate 与未完成重复的结论；[首轮分析](../../outputs/071_judge_icl_feasibility/stage1_analysis.json)、[逐例审阅](../../outputs/071_judge_icl_feasibility/stage1_case_review.md)、[自检](../../outputs/071_judge_icl_feasibility/verification.json)为核查入口。

离线准备脚本 `prepare071.py` 只适用于空的新输出目录，不覆盖已冻结 071 文件；`scan_examples071.py` 为首次选择前的阅读清单。`run071.py` 是带预算与停发规则的 append-only 执行器，当前**不要直接续跑**：20 元预算 gate 未通过。`diagnose071.py`、`verify071.py`、`review_cases071.py`、`cost_summary071.py` 离线核查；`analyze071.py` 在完整三臂同 ID 回执后运行了首轮统一评价。

用户随后明确要求继续，续跑边界见[受控续跑登记](continuation_001.md)：`prepare_continuation071.py` 冻结原 6 条未知请求的同体新 ID 恢复及别名，原回执保留，任务预算不重置。最终方法报告以续跑完成后的新状态为准；此前 `execution_diagnosis.json` 继续保留首次停止快照。首轮效果 gate PASS、重复预算 gate FAIL；用户按[结项补充](closure_001.md)决定不重复，不缩减重复样本或改成功标准。
