# 068 独立审计交接

## 范围与工作区

- 执行时 HEAD：`4bf9bb83a15aa684a5d125514f3a8ef9a51f9f37`。
- 068 新增 `tasks/068_final_pack_utility_diagnosis/`、`outputs/068_final_pack_utility_diagnosis/`；更新 `AGENTS.md`、根 `README.md`、`docs/API_POLICY.md`、`docs/PROJECT_STATUS.md`、阿里云与硅基流动现行说明。**未改 `.gitignore`、原始数据或 066/067 冻结工件；未 commit/push。**
- 独立审计未执行。`verification.json` 是执行者自检，不应标为独立 PASS。

## 优先核查的争议

1. 067 v1 的 236 条 `baseline_pids` 和 227 个 audit `current_pack_ids` 均为空；226 个最终 Judge reference 实际只含 1–2 段。`dropped_pids=[]` 不能证明原包保留。[v1 法证结果](forensics.json)及逐例映射 `forensic_cases.jsonl` 可从原 067 冻结请求体重算。
2. 067 v2 的 225 条可映射病例均有非空原包 ID；27 条改包，新增 33 段、显式删除 38 段。v2 原始结果 +2 final correct 未过原晋级门槛。[v2 法证结果](forensics_v2.json)、`forensic_v2_cases.jsonl`、[统一评价](unified_evaluation_v2.json)分别复查。
3. 067 `freeze_v2.json` 与 `execution_note_002.md` 在较早时间宣称 v1 实现无效、v2 正式；较晚 `protocol_amendment_001.md`、`CURRENT_STATUS.md`、`report_final.md` 反向指定。068 不追认任一正式来源。核查时间、文件 hash、请求 ID 是否支持解释；不要把两套结果合并或选优。
4. 068 原始 `freeze.json`/`jobs.jsonl` 与 `freeze_002.json`/`jobs_002.jsonl` 的前两轮预检，因解析器和历史工件发现而分阶段修订。前两份 freeze 保留、标明 superseded；所有真正发送的 v1 同输入重复请求与 `jobs_002.jsonl` 完全一致。`presentation_jobs.jsonl` 只替换字面量换行；`jobs_v2_068.jsonl` 只重复 v2 已冻结 body。各修订均在相应新增响应读取前保存，见任务目录 `protocol_amendment_001` 至 `_004`。

## 评价、费用与决策

- 统一 `evaluate`/`paired_compare` 主队列 236 条/24患者，raw 与 Frozen PriorG 分开；1,000 次患者 cluster bootstrap。v1 为错误实现诊断，不作方法成绩；v2 final 198→200、MCC 0.594609→0.608480、false-S 6→6；raw 177→181、MCC 0.505850→0.523844。[完整 v1/v2 统一评价](unified_evaluation.json)、[v2](unified_evaluation_v2.json)。
- v2 27 条改包均做 final 同输入重复，原包重复 22 次加精确复用 5 次；原 2 条 final rescue 均未重现。raw 原 4 条 rescue 中 3 条同病例重现。逐例见 `diagnostic_v2_cases.jsonl`，汇总见[分析](analysis_v2_068.json)。
- 新请求 164/164 HTTP200，估算费用 ¥3.785280/10，未知预留 0；无重试、无 reserved。每次请求/回执在 `attempts/<request-hash>_01/`。费用上界与来源见 `freeze_003.json`、`presentation_freeze.json`、`freeze_v2_068.json`；总账见 `execution.json`、`execution_presentation.json`、`execution_v2.json`。
- 结论：不训练 selector、不继续调 packer/prompt；先独立审计 067 来源口径。068 的事前“稳定救回≥3且≥3患者”在 v2 为 0，未通过。报告中的 v1 apparent signal 只作无效实现的警示。
- [最终自检](verification.json)：1346 PASS、0 FAIL。早期仅 v1 范围的 `verification_v1.json` 保留快照。

## 关键 SHA-256

| 文件 | SHA-256 |
|---|---|
| `report.md` | `2dacd6ff0cea5c5277c67370a0dbc107a6b22d83ec30df25d0f814a2ec80f6ed` |
| `analysis.json` | `c0d0812587f2e7c32ef3c8e259167fd17b6e71765d3b94aad57e08cecedf4760` |
| `analysis_v2_068.json` | `539ce5077af243eab1e2f77a63c697ba1bc4d9a2549bf0f85ece8f1ae5b63e9b` |
| `verification.json` | `ea0c327581e6167b6336c1aae0871a0eefd85deed36d881ebe90adffbaf7840a` |
| `forensics.json` | `5c89d61c7f440ada528e5c7770c8e6d9bc1eae3700cf6c76a3cf48e36ccf2948` |
| `forensics_v2.json` | `78fd1d8c8d2e5182f4d9c54a4a89ddd6569f18219c84bf78feae86c2f9425ed4` |
| `jobs_002.jsonl` | `9597543b641c5ccd96e0396621a9a79c7a2bf6afecafa0f1377f91194e9739f6` |
| `presentation_jobs.jsonl` | `6e57cd0f895a5ea91855732ceba1ac85ab83785528a96ab33ae1dac7fa64a8e7` |
| `jobs_v2_068.jsonl` | `f72c2aae803067482fadda63c970fecc154e3a2994e3503fb0b5a7212aab3334` |
