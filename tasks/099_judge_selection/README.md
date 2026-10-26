# 099 Judge选型入口

用户授权四个阿里云/千问AI候选及全部新增API累计20元。当前默认模型、098和Git发布保持不变。科学设计：[protocol.md](protocol.md)；公共来源核对：[model_audit.md](model_audit.md)；实际规模：[execution_freeze.json](../../outputs/099_judge_selection/execution_freeze.json)。

实际冻结自然80条O（发布reference）、其中32条C48，额外NS/NA各16条O，8条O四模型重复，共608次目标请求。所有患者已有暴露；小规模选型不当稳定全面胜出或新holdout。Qwen max_tokens512仅限制最终回答，thinking_budget2048单独计入费用。选择首先依据O原系统输入，不按C−O增量择模型。

统一使用当前CPU环境research-verifact-029和scripts/run_research.ps1；不安装包、不运行GPU。新文件UTF-8无BOM。原文与完整请求回执在受忽略.local_models/099_judge_selection；公开结果只含ID、标签、指纹、usage和指标。

准备完成顺序：fetch_sources099.py（公开元数据，无权重）→prepare099.py（一次性冻结）→test099.py→runtime099.py preflight→freeze_format099.py（纯格式工程）→runtime099.py all。全部HTTP200，包括无效，均不重发；解析只去完整外层JSON围栏，严格原解析结果并列保留，见format_amendment.md。

若进程中断，先确认没有仍在运行的099执行器，再沿原账本恢复：

~~~powershell
pwsh -NoProfile -File D:\Research-VeriFact\scripts\run_research.ps1 D:\Research-VeriFact\tasks\099_judge_selection\runtime099.py all --workers 4
~~~

runtime099.py status只查账，不调用模型。run.lock存在时不得强行开第二个执行器；先检查进程，不因对错或格式无效清除成功记录。恢复复用已成功request_id、保留所有失败/未知预留，不重置20元额度。

全部冻结请求结束后，analyze099.py→report099.py→selfcheck099.py；分析入口拒绝按部分成绩选型。完整输出对应report.md、analysis.json、predictions.jsonl、main_table.csv、cost_ledger.json、attempt_ledger.jsonl、selfcheck.json及A800_bridge_plan.md。自检不是独立审计；本轮不部署AutoDL或执行后续桥接。
