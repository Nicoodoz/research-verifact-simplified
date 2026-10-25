# 032 当前状态

状态：快速独立审计PASS，可冻结／结项；用户本轮已授权通过后提交推送GitHub。

固定DeBERTa三类关系模型、本地C48双粒度实例、小型注意力/残差三分类对照已跑完。
范围：28名/2527条训练；12名已暴露确认患者/1148条；54236组NLI配对；135套保存模型。

主方案（双粒度注意力）：954/1148正确，PA 83.10%，MCC 0.4960，错误Supported 77。
固定λ=2：947/1148正确，PA 82.49%，MCC 0.5210，错误Supported 57。
因此主方案多判对7条，但MCC下降且错误Supported多20条，未实现PA/MCC共同提高。
仅片段注意力的辅助条件为962/1148、PA 83.80%、MCC 0.5111、错误Supported 79；不根据确认结果改选主方案。

新增收费API 0；reserved40未用于本轮；未更改原模型环境或031输入。
报告生成的编码兼容问题已通过副本处理，模型/预测/评价不重跑，详情见execution_notes.md。

结果入口：report.md、analysis_001/metrics.csv、analysis_001/paired.json、analysis_001/changes.json。
复查入口：verification_001/checks.json、completion_verification_001.json、audit_handoff.md。
独立审计已完成20项测试、135模型重放、NLI配对重建、训练内选择复算和7个评价文件重放；不自动033或最终测试。见[审计报告](../../reviews/032_evidence_relation_correction.md)。原待审／未推送记录为历史快照。
