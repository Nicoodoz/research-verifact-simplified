# 016 独立审计附件（2026-09-16）

结论见[独立审计](../../016_disagreement_triggered_review_validation.md)。本目录只保存独立审计证据，不复制临床病例正文。

- audited_files_sha256.json：审计开始时独立计算的2492个文件指纹，与执行者handoff一致，审后复验无变化。
- raw_audit.py / raw_summary.json：不导入执行者normalizer、费用或分析函数的独立回执、答案、费用、时序核查；在仓库根目录用research-verifact环境运行脚本，并传入一个新的输出JSON路径。
- replay_invocation.py / replay_summary.json：此次断网重放的实际调用脚本及结果。脚本中的TEMP为当时临时目录；Path.relative_to适配仅使仓库外审计输出可写，不改变输入校验。重跑请使用新的空临时目录。summary保留原执行器的executor_self_check状态字样，独立审计结论由审计报告给出。
- tests.log：独立断网运行unittest discover的215项测试结果，全部通过；测试使用虚构服务回执，没有收费API。
- manifest.json：本附件及独立审计报告的指纹。

统一评价重放沿用002实现；独立原始标签/费用解析用于避免只依赖执行者汇总自证。没有医学重新标注或reserved test正文检查。
