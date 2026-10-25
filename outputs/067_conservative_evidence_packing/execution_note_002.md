# 067 Execution Note 002：Superseded v1 Judge Calls

067 Amendment 001 已将v1 parser/audit/pack标记为 implementation-invalid / superseded。

在后续恢复执行时，执行者误将现有 `stage2_jobs.jsonl` 识别为正式待执行Judge队列，因此额外发送了226个基于v1无效pack的DeepSeek T-S请求。

处理原则：
- 这226个请求及HTTP200回执全部保留，不删除、不覆盖；
- v1 Judge输出未被读取用于067方法选择、阈值、prompt、风险词、addition/drop规则或v2 pack构造；
- v1所有科学结果均无效，不进入067主分析；
- v2使用独立文件与独立request_id：
  - cases_blind_v2.jsonl
  - stage1v2_jobs.jsonl
  - pack_mapping_v2.jsonl
  - stage2v2_jobs.jsonl
  - 067v2_audit_* / 067v2_judge_*
- 正式067科学结果只使用v2；
- 成本统计包含全部v1无效调用；
- 全部累计API成本约¥20.73，仍低于原¥30 hard cap；
- reserved未使用。

这属于执行浪费/状态识别错误，不改变冻结的方法定义，但必须在审计中显式披露。
