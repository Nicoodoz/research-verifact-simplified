# 038 独立审计交接

请独立核查038“证据—标签—解释一致性审计”，不要把执行者自检当独立审计。

重点复核：
1. planning_001/blind_cohort.csv 是否严格为342条U0非S→U2 S翻转 + 三类各40条固定hash稳定对照。
2. 924个证据审计请求的user payload是否只有 proposition + C48 reference，不含GT、U0/U2/Gate、原verdict或原reason。
3. 346个reason审计是否对应全部U2最终S且原scoring verdict非S样本。
4. 所有1270个HTTP200只使用一次；33个证据结构无效回答是否保留并未重跑。
5. common038.py引用原文匹配修正后，是否仅从原HTTP200重新解析；analysis_000_buggy_quote_regex为旧错误汇总，正式结果仅看analysis_001。
6. 随机抽取若干strict trace-supported样本，核对引用quote可在对应C48 reference_id中逐字定位。
7. 重算U2最终S=2647、non-S reason来源=346，以及R/H/W=219/42/81。
8. 核对Qwen R有效214、判S68、strict trace-S51；DeepSeek R有效206、判S2、strict trace-S2；两模型都有效R=201，其中133条都给non-S。
9. 核对reason alignment 346/346 contradictory。
10. 确认报告没有把自动模型审计写成医生gold，也没有据038重新优化reserved方法。

关键入口：
- tasks/038_evidence_explanation_audit/protocol.md
- outputs/038_evidence_explanation_audit/planning_001/
- outputs/038_evidence_explanation_audit/analysis_001/
- outputs/038_evidence_explanation_audit/report.md
- outputs/038_evidence_explanation_audit/verification_001.json

当前状态：执行者核验完成；独立审计尚未进行。
