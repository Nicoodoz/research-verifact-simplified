# 100今晚任务与恢复入口

本次用户授权：完成098，按其结果只执行一个后续。新费用累计130元、运行线125元，接手前098费用不占新额度，但其原累计50元继续有效。基线不能因恢复重置。最终完成后用户明确要求同时推送完整与精简GitHub仓库；未完成前不提交。

接手快照：outputs/100_preregistered_followup/handoff_budget_snapshot.json。098现已完整结束，原2120目标+2构造，累计25.6387596元含旧未知0.9129；本次新增20.6114295元。P相对O/Q/C门槛均未通过，进入证据分支。099不重跑，默认/原GT/原始数据不变。

100输入、患者、规模、24K与判据在回答前冻结。因无缓存、全部最大输出及098原50元余量的最贵路径预测141.81元，按用户预定整体降档为开发48自然+24压力、确认192自然+32压力、重复16；预测121.30元。确认32人与098评价/示例开发患者隔离，全部有历史暴露。

开发360逻辑位、272唯一请求已完整完成；L24按原规则唯一晋级。确认运行O/C/S24/L24，重复O/S24/L24；944逻辑位、847唯一请求。相同body跨臂共享同一首次回答，重复槽独立。不因成绩扩大或追加。

原文/请求/回执与SQLite在既有忽略.local_models/100_preregistered_followup。主环境仍research-verifact-029；仅分词调用既有085辅助Python和公开0731 tokenizer，无GPU/权重/安装。

只查费用（不调用API）：

~~~powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/100_preregistered_followup/runtime100.py status
~~~

中断后先查真实Python进程和run.lock，禁止第二个worker；确认旧进程不存在才保留并移走陈旧锁。保留旧snapshot/账本，勿重跑handoff100.py或prepare100.py。按当前已冻结的L24确认恢复：

~~~powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/100_preregistered_followup/runtime100.py confirmation --workers 4
pwsh -NoProfile -File scripts/run_research.ps1 tasks/100_preregistered_followup/analyze100.py confirmation
pwsh -NoProfile -File scripts/run_research.ps1 tasks/100_preregistered_followup/material_summary100.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/100_preregistered_followup/report100.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/100_preregistered_followup/selfcheck100.py
~~~

成功HTTP200均不重发，包括无效答案；只对未成功按原最多3次和退避重试。每次先按峰时字节上界预留，本任务费用加098接手后的新增费保护125/130元。08:00若跨价则重算完整剩余阶段，不能完成则保存断点、不等下一夜。阶段分析拒绝未完成输入，不用部分正确率选型。

最终正式报告report.md；一页night_summary.md；逐阶段analysis/predictions/usage/main_table；cost_ledger与selfcheck。完整note机制须同时超过O和同长度S24；便宜C及压力/重复代价单列，S24/EHR-all不包装为新算法。
