# 083结果入口

- [中文总报告](report.md) · [执行摘要](executive_summary.md) · [当前状态](CURRENT_STATUS.md) · [交审说明](audit_handoff.md) · [执行者自检](selfcheck.json)
- 冻结：[协议](../../tasks/083_native_rationale_information/protocol.md) · [预算与请求](preflight_and_cost_plan.json) · [评价前模型](models_frozen.json) · [评价前绑定](evaluation_apply_freeze.json) · [错配负对照](permutation_frozen.json)
- 原生来源：[同回执核查清单](source_manifest.jsonl) · [原理由文字](native_texts.jsonl) · [清洗文本](cleaned_inputs.jsonl) · [抽取请求](extraction_jobs.jsonl) · [结构引文](structured_arguments.jsonl) · [来源质量](native_quality.json) · [抽取质量](extraction_quality.json) · [结构类别分布](structured_distribution.json)
- 监督与结果：[标签／曝光](label_exposure_ledger.json) · [折信息](fold_manifest.jsonl) · [逐例预测](evaluation_predictions.jsonl) · [评价](evaluation_results.json) · [共同结构可用敏感性](common_structure_valid_sensitivity.json) · [重复](repeat_predictions.jsonl) · [B辅助](B_aux_results.json) · [费用](cost_ledger.json)
- `attempts/`逐请求保留实际新请求和回执，`models_frozen.joblib`保存训练侧冻结的文本编码器与低容量模型。忽略目录`outputs/replays/083_verify_001/`也保存原始执行者自检回放。

本轮未更改默认系统或使用reserved；研究结项时未自动提交推送，此后用户单独授权推送083。执行者自检不是独立审计。
