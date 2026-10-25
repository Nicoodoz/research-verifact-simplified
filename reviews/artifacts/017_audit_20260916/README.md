# 017独立审计附件

结论见[017审计](../../017_verification_supervised_evidence_utility.md)。

- handoff_snapshot.json：审计开始时复制的交审清单，1717项SHA-256已独立复算。当前导航的审计后状态同步另行记录，不回写原handoff。
- raw_audit.py / raw_summary.json：独立标准库解析所有原始回执、费用、逻辑重复、稳定rescue/harm及事前gate。在仓库根目录用research-verifact Python运行脚本，并指定一个新的输出JSON路径；不发送API。
- replay_invocation.py / replay_summary.json：本次断网重放／报告渲染／测试调用及重放摘要。调用脚本记录当时临时目录；适配Path.relative_to仅允许审计输出落在该临时目录，不放松冻结输入。重跑需指定全新临时目录。摘要沿用执行器的self_check字样，独立意见见审计记录。
- tests.log：223项断网测试全部通过，包括017的输入隔离、单段替换、跨供应商不作强监督、累计预算、失败门槛禁止训练等检查。
- manifest.json：本附件和审计记录的指纹。

仅保存审计证据，不复制病例正文或重新标注。统一指标仍通过002原实现重放。
