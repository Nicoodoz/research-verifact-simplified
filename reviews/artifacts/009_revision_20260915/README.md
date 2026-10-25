# 009 修订定向独立复核（2026-09-15）

结论见 [审计末尾追加](../../009_retrieval_baselines.md)。本目录仅保存复核证据。

`audit_revision.py` 为审计者检查：核对修订 handoff、旧验证程序快照、原成果与既有审计指纹，独立构造八项隔离篡改检查，再在禁网条件下重放并运行146项测试。`results.json` 保存独立结果，`actual_verifier.diff` 为实际新旧程序差异。`replay_verification.json` 和 `tests.log` 是亲自运行结果，不直接采信执行者自查。

所有测试及重放输出位于仓库外临时目录；仅在内存中改输出位置断言，其余执行逻辑与校验未修改。当前真实 Git 工作区的 reviews/README.md 修改被记录且不再阻塞。109个内容文件逐字节一致，provider token CSV一致；未调用API、读取密钥或访问reserved test病例。

需重现时将脚本复制到新的隔离临时目录；脚本 root 是本次实际仓库 D:/Research-VeriFact。审计之后更新的可变状态文档与原交审指纹有意不同，历史冻结成果不回写；版本及状态同步变更见 state_sync.json。
