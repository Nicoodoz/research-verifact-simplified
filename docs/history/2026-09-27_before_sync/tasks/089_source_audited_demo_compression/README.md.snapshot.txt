# 089 具体遗漏核对驱动的示例压缩与实测

本任务由用户明确交办，20元原价总上限；[协议](protocol.md)、[中文报告](../../outputs/089_source_audited_demo_compression/report.md)、[交审入口](../../outputs/089_source_audited_demo_compression/audit_handoff.md)。不重启088，不自动090。

构造器与独立Q调用、具体遗漏核对使用已授权阿里云模型；最终Judge只接原文段落和原示例标签。默认系统不变。构造失败的全保留与医学必须全文分开记录，原始成功回答不重发。

离线只读复核：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/089_source_audited_demo_compression/test089.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/089_source_audited_demo_compression/verify089.py
```

construct/coverage/prepare/api脚本是原执行入口，结项后不要作为复核命令重复运行。输出采用独占创建与冻结SHA，不覆盖原成果。self-check不冒称独立审计。
