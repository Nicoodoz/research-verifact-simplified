# 084 成果入口

- [中文总报告](report.md)、[083冻结OOF零API诊断](083_oof_diagnosis.md)、[材料与精确回执覆盖说明](coverage_inventory.md)。
- 事前[协议](../../tasks/084_f4_coverage_validation/protocol.md)、[冻结队列与费用口径](freeze.json)、[盲样本](sample_blind.jsonl)、[两臂完整请求体](main_jobs.jsonl)。
- [逐例新增预测](new_predictions.jsonl)、[完整机器评价](evaluation_results.json)、[原生回答关联](native_manifest.jsonl)、[所有尝试](attempt_ledger.jsonl)、[原价费用](cost_ledger.json)。原始request/receipt保存在`attempts/`，逐条哈希见`native_manifest.jsonl`。
- [22患者盘点](coverage_inventory.csv)、[精确缓存覆盖](cache_receipt_inventory.csv)、[历史532请求体等价核查](historical_reference_consistency.json)、[旧24同体重复摘要](historical_repeat_sensitivity.json)。
- [执行者自检](selfcheck.json)、[审计交接](audit_handoff.md)、[当前状态](CURRENT_STATUS.md)。
- [071选例患者池曝光口径更正](analysis_amendment_001.md)、[文件哈希交接清单](handoff_manifest.json)。

结果是已暴露development扩覆盖，不是新的独立最终测试。执行者自检不代表独立审计；不使用reserved40、不修改历史冻结成果或默认系统。
