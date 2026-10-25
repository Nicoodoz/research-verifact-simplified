# 093 已完成：重复原文折叠与固定预算补证

[正式报告](../../outputs/093_lossless_evidence_budget/report.md) · [历史区别](../../outputs/093_lossless_evidence_budget/history_difference.md) · [方法](../../outputs/093_lossless_evidence_budget/method.md) · [病例](../../outputs/093_lossless_evidence_budget/case_analysis.md)

自然90与压力30分报；B/F/A core正确76/77/76（N88）和17/16/18（N30）。停止本版，默认B不变。153次HTTP200、0重试、未优惠原价¥4.097118/20；不自动下一任务。

## 复查与复现

主环境research-verifact-029，通过scripts/run_research.ps1。任务输入/原生回执在忽略目录.local_models/093，仅合法持有数据的本地环境可完整复查；公开哈希不是临床原文替代品。

零API功能检查：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/093_lossless_evidence_budget/test093.py`。

inventory093→build_pool093→prepare093→freeze_execution093是事前冻结链；api093为历史执行器，不是授权再次调用。analyze093→close093→report093→verify093→supplement093→deliver093为结果交付链。结果以独占创建保护，原目录重复分析遇FileExistsError为预期，不删除旧结果绕过保护。重算应复制代码与私有输入到隔离研究副本，保留冻结路径结构，对生成JSON逐值比对；不重新运行API或导航更新脚本。inspect093会在本地显示私有病例，不将终端输出发布。

selfcheck.json是执行者校验，非独立审计。来源源码指纹见source_manifest.json，构造与发送配置分别见main_freeze/execution_freeze；最初盘点版本已在engineering_archive按原SHA保留。解释、作者分层和交付代码是事后分析，不修改冻结候选。
