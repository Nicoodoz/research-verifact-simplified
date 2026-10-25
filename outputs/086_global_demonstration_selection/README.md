# 086输出入口

状态：完整V/E实测结项，522次HTTP200、原价¥21.150990/30；N1仅V优势，E未超过同期F4或R1。[中文报告](report.md) · [自检](selfcheck.json) · [交审](audit_handoff.md)。

- [冻结规则](freeze.json) · [候选池](candidate_pool.jsonl) · [五组定义](groups.json) · [V病例](V_cases.jsonl) · [E盲病例](E_cases_blind.jsonl)
- [V请求](V_jobs.jsonl) · [逐例预测](V_predictions.jsonl) · [效用表](V_utility.json) · [D*冻结](D_star_freeze.json) · [留一患者敏感性](V_LOPO_sensitivity.json)
- [E请求](E_jobs.jsonl) · [E冻结](E_jobs_freeze.json) · [逐例预测](E_predictions.jsonl) · [统一评价](E_analysis.json) · [费用台账](cost_ledger.json)
- [V旧/新同请求F4桥接](V_old_new_F4_bridge.json) · [E无效用控制比较](control_comparison.json) · [输出层机制台账](mechanism_cases.jsonl) · [机制摘要](mechanism_summary.json)
- [085A资产暂停盘点](085A_pause_inventory.json) · [D/V/E claim重叠检查](claim_overlap_check.json)
- [中文总报告](report.md) · [自检](selfcheck.json)

`attempts/*/request.json`与`receipt.json`为原生请求/回执，包括临床reference。GitHub提交前逐项检查发布边界与凭据；不要将未核对的本地缓存、模型文件或`.env`加入提交。
