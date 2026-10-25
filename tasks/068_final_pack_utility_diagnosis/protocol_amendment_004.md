# 068 预检修订 004：把 067 v2 单独作为实现修正分支核查

在完成 v1 同输入重复后发现 067 内部存在相互矛盾的正式口径：`freeze_v2.json`（04:50 UTC）将 v1 明确标为 implementation-invalid/superseded；`execution_note_002.md`（05:14 UTC）写明 v2 才是正式科学结果。此后更新的 `protocol_amendment_001.md`、`analysis_final.json`、`CURRENT_STATUS.md` 又把 v1 当正式、v2 当 post-formal 排除。068 不替历史任务裁定哪次文档改写有效，分别标记来源和形成时间。先前 115 个 068 请求只诊断 v1 错误实现，不得外推到 v2。

为回答用户的三个问题，本任务追加一项**在 v2 新答案前冻结**的核查：读取 `cases_blind_v2`、`pack_mapping_v2`、`stage2v2_jobs` 与 `results_v2`，检验 baseline passage 映射、实际增删、请求体和 GT 盲性；对 v2 全部 27 个 changed 病例各做一次短包同输入重复。原包同输入重复优先复用 068 已有完全相同请求体的回执，仅对未覆盖者新增调用。另对 v2 原先 2 个 rescue 和固定 ID 哈希前若干个无净变化病例做字面量换行→真实换行的纯呈现对照，数量由发送前预算上界决定，不看新增答案。

全部请求继续共享 068 原 10 元硬上限，包含既有 115 次费用与任何未知预留；每次发送前检验累计占用。v2 只作为一个独立实现分支报告，不能与 v1 混算总指标或选择“最好”成绩。v2 已是 development，回执重复也不是独立患者确认。原 067 的独立审计未执行。
