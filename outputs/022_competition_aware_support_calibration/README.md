# 022成果入口

**阶段A完成，未过门槛，按计划停止；待独立审计。** 唯一必读[中文主报告](report.md)。新API费用0/80元，没有阶段B或Qwen调用。

- [冻结执行协议](protocol_001.md)：4折患者隔离、固定NLL/ridge、原U2、继续门槛。
- [评分/队列清单](preparation_001/rows.jsonl)、[患者分折](preparation_001/folds.json)：1529个独立claim，另879条R1只评价不拟合。
- [正式OOF预测](stageA_002/oof_predictions.jsonl)、[参数](stageA_002/fitted_parameters.json)、[门槛](stageA_002/decision.json)。
- [统计附录](statistics.md)：002全部指标、混淆矩阵、作者/患者/类别/概率诊断。
- [零费用台账](stageA_002/budget.json)、[执行记录](execution_notes.md)、[相关工作](related_work.md)。
- [断网复核](verification_001/summary.json)、[冻结证据来源](verification_001/evidence_provenance.csv)、[审计交接](audit_handoff.md)。

stageA_001是序列化异常留下的未完成工程运行，不是另一方法或正式效果。正式结果仅stageA_002，历史失败/源码保留，不删除重跑。没有阿里云同期结果，不借用旧硅基流动B冒充阿里云基线。
