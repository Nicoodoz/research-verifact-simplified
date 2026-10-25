# 071 交审说明

- `protocol.md`、`freeze.json` 在首次 071 收费调用前锁定四示例、16/24 患者划分、96 条完整评价、B/E/C 请求及效果/重复停止标准。B 全请求体与 053 T-S 同体；E/C 仅 system message 的示例标签对应关系不同，C 匹配格式、长度和类别比例。无 reserved。
- `attempts/` 保存 295 次请求和回执，按 SHA-256 绑定。首次停发的 `execution_diagnosis.json` 记录 108 个 HTTP200、6 个 HTTP0、174 未发送；原未知回执未覆盖。用户授权后续跑的 `continuation_001_freeze.json`、`recovery_mapping.json` 和六条同体不同 ID 回执可证明恢复逻辑；原 174 条仅首次发送，主队列逻辑 288/288 完成。
- `stage1_analysis.json` 使用 `verifact_research.evaluation.evaluate` 与 `paired_compare`，完整 96 条 Frozen PriorG、raw 三臂共同有效 93 条分开报告。首轮效果 gate PASS，预算 gate FAIL；没有 `repeat_jobs.jsonl`、无第二轮效果，稳定性未验证。
- `stage1_changed_cases.jsonl` 收集所有 18 条三臂/历史正确性变化的实际 claim、完整 reference、三臂输出与分数；`stage1_case_review.md` 保留可见证据与解释限度。原生理由不是新增 GT 或内部机制证明。
- `cost_summary.json`：已知 usage 估算 ¥10.589400、原六条未知预留 ¥0.873951、此前密钥检查保守预留 ¥0.60，任务占用 ¥12.063351/20。192 次 B/E 同体重复按已知成本预计 ¥7.219269；冻结波动/在途缓冲下总界 ¥21.526474，故停发。不是服务商账单核对。
- `verification.json` 为执行者 509 PASS、0 FAIL，不等于独立审计或方法通过。未修改历史回执/医生标签/冻结 PriorG，不 commit/push，不自动 072。
- `tasks/071_judge_icl_feasibility/closure_001.md` 记录用户在知悉效果与费用界后决定“不需要重复，按现有结果完成071收尾”。该决定保留预算 gate FAIL 与稳定性未验证，不改写原协议或历史回执。
