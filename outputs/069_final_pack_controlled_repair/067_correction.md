# 067 来源与实现更正说明（069 离线核查）

本说明只为后续研究限定 067 的可用证据，**不覆盖、删除或改写 067 的任何冻结工件和历史报告**。详细逐请求复核见[068 报告](../068_final_pack_utility_diagnosis/report.md)及其 `forensics.json`、`forensics_v2.json`。

1. 067 v1 的 `cases_blind.jsonl` 中 236 条 `baseline_pids` 全空，227 个正式 Qwen audit 的 `current_pack_ids` 全空。226 个 changed pack 实际把约 12 段原包改成 1–2 段；`dropped_pids=[]` 只反映没有显式 drop，不表示原包保留。因此 v1 的 14 rescue/13 harm、MCC 0.5946→0.5819 是真实请求下的**错误实现**结果，不能称为“保守增补”的成绩，也不能据此否定真正保留原包的加证据操作。
2. v2 的 `cases_blind_v2.jsonl` 为 225 条病例恢复非空原包 passage 映射；27 条 changed pack 显式增 33 段、删 38 段。v2 同队列原结果 final correct 198→200、MCC 0.5946→0.6085、false-S 6→6，未达到 067 原净正确、MCC、救回患者数门槛。068 同输入重复中，v2 原 2 条 PriorG 后救回均未重现；raw Judge 原 4 条救回有 3 条同病例重现。
3. 067 形成时间较早的 `freeze_v2.json` 与 `execution_note_002.md` 指定 v1 实现无效、v2 才是科学结果；较晚的 `protocol_amendment_001.md`、`CURRENT_STATUS.md`、`report_final.md` 反向把 v1 设为正式、v2 列为 post-formal。两套声明冲突，不能选优或合并；正式来源须独立审计裁定，执行者不能宣布通过。

因此 069 仅把 067/068 用作风险和设计线索，不用 v1 指标选择方法。069 的真正机制对照使用 066 的 C48 内 oracle 诊断病例与冻结原始 EHR passage，收费请求重新冻结、保存、评价；GT-aware oracle 不算部署方法成绩。
