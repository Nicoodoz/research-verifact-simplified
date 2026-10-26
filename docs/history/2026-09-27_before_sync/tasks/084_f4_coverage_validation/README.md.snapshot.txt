# 084：固定 F4 扩展验证与 083 OOF 离线结项

本任务依据用户提供的 `docs/084_Codex_固定F4扩展验证与083离线结项_执行提示词.md`，在不改变C48、B/F4提示、`deepseek-v4-flash-0731`或Frozen PriorG的条件下，分析083原OOF并新增180条两臂评价。研究结果与当前状态见[`outputs/084_f4_coverage_validation/report.md`](../../outputs/084_f4_coverage_validation/report.md)。

执行顺序与边界：

1. `oof083.py`只读取083冻结OOF，不训练模型；`inventory084.py`盘点032汇合的全development原C48、历史532及暴露；`cache_inventory084.py`补核旧精确两臂回执。
2. [`protocol.md`](protocol.md)在新请求与评价GT前冻结。`freeze084.py`按哈希及患者轮转写一次`sample_blind.jsonl`、`main_jobs.jsonl`、`freeze.json`；正式文件已存在，**不要重跑**或覆盖。
3. `run084.py`读取冻结请求体，用阿里云北京固定模型和原价¥20硬上限成对执行，保存每次attempt的request/receipt；网络恢复只重试未成功请求。命令 `pwsh -File scripts/run_research.ps1 tasks/084_f4_coverage_validation/run084.py --preflight` 仅离线核对，`... run084.py 4` 会**调用收费API**，只用于已获授权的本任务续跑，不能作自检重放。
4. `analyze084.py`在完整回执之后才连接医生GT，原规则离线评分并调用统一`evaluate`／`paired_compare`；`verify084.py`只读核验请求、费用、患者隔离及结果。安全离线复核命令：`pwsh -File scripts/run_research.ps1 tasks/084_f4_coverage_validation/verify084.py`。

历史032、082、083及002的冻结文件只读；不使用reserved40，不改默认系统或`.gitignore`。执行者自检并非独立审计。任务完成后不自动启动下一任务，也不自动提交推送。
