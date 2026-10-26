# 098运行与复核入口

当前授权：2026-10-26用户正式交办，新增收费全任务硬限50元，保留本地，不提交/推送。方法及继续/停止标准见[protocol.md](protocol.md)，执行规模与请求指纹见[execution_freeze.json](../../outputs/098_p90_native_confirmation/execution_freeze.json)。

CPU统一环境research-verifact-029，经pwsh及scripts/run_research.ps1运行。不要使用旧任务的写入型入口重新生成冻结材料，不重发已成功请求。

实际顺序：prepare098.py aux → runtime098.py aux（两个独立Q相关性评分）→ prepare098.py q → prepare098.py plan → test098.py → runtime098.py busy（冻结32次正式请求）→ complete098.py（等待闲时，恢复其余冻结请求，离线分析/报告/自检）。complete098.py各次等待仅30秒；所有调用沿同一SQLite任务总账恢复，不重置费用。

## 脱离Codex会话续跑（2026-10-26更新）

已注册Windows计划任务`Research-VeriFact-098-Resume`，2026-10-26北京时间22:00触发。任务已在20:18独立启动并核验：它自行等到闲时，不需要Codex保持运行；22:00再次触发时，任务的IgnoreNew设置及入口互斥锁防止并行重复。旧的会话等待进程已停止。没有更改原冻结方法、样本、生成参数、科学判定标准或费用账本。

计划任务使用当前Windows用户交互登录，不存密码或token；电脑须开机且该用户保持登录。设置了WakeToRun与StartWhenAvailable，但关机或注销后的实际恢复受Windows条件约束，不能保证在关机时执行。

状态文件：`.local_models/098_p90_native_confirmation/background_status.json`；每次日志：`.local_models/098_p90_native_confirmation/logs/resume_*.log`。正式请求/回执及累计账本仍在原目录，不另起账。

若需要手动恢复，在任意pwsh中执行：

~~~powershell
pwsh -NoProfile -File D:\Research-VeriFact\tasks\098_p90_native_confirmation\resume098.ps1
~~~

入口先核对冻结文件与已成功32次请求，随后从同一SQLite账本跳过全部HTTP200的request_id，仅处理剩余2088次。若已有独立进程则直接退出；若已complete则不发请求。忙时手动启动也只等待闲时。仅检查而不执行，用同一命令追加`-CheckOnly`。

只查看系统任务：`Get-ScheduledTask -TaskName Research-VeriFact-098-Resume`；运行计划任务：`Start-ScheduledTask -TaskName Research-VeriFact-098-Resume`。运行结果在report.md、selfcheck.json及complete.json，失败保留原回执与预留并在background_status.json记录FAILED，不重复成功回答。

runtime098.py status仅查询账本，不发请求。remaining只允许在闲时启动；运行中若跨价格边界，仍以起止时间保守结算。HTTP200内容无效不重发。最大3次有限通信重试，未知预留保留；遇持续权限、模型/usage异常或预算问题停止，不能绕过门槛。

临床正文、四例及原始request/receipt在既有忽略的.local_models/098_p90_native_confirmation下；公开成果仅ID/标签/指纹/数值。P逐字继承090，Q的相关性构造不读确认集，P/Q实际仅一个长槽不同。

离线分析要求全部冻结目标请求成功，禁止按部分成绩扩量。analyze098.py读取回执直接解析verdict并用evaluate/paired_compare评价；report098.py生成中文报告；selfcheck098.py逐条核对请求、患者隔离、原始预测、Decimal费用及独立算式/sklearn，属于执行者自检，非独立审计。已有输出不可覆盖成另一版结果。
