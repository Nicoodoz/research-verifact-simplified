# 018独立审计证据

结论与实际语义阅读范围见[独立审计](../../018_verifact_gap_attribution.md)。

- handoff_snapshot.json：审前复制的388项交审指纹，已独立复算。后续只有允许的现行导航同步，不覆盖原交审快照。
- raw_audit.py / raw_summary.json：以本批ID查询原发布parquet，绑定1251条完整原始输出与reference；独立重算四格、类别净差、false-S、桥接和覆盖率。在仓库根目录用research-verifact Python运行脚本并传入新的输出JSON路径，无API。
- replay_invocation.py / replay_summary.json：真实断网重放调用与95文件一致结果；Path.relative_to适配仅允许临时审计输出，不改变输入校验。初次包装器在重放通过后复用unittest loader造成测试目录ImportError，随后以独立loader运行test_invocation.py解决；这是审计包装器问题，未修改项目代码。
- test_invocation.py / tests.log：独立23项测试最终全部通过。
- render_check.json：主报告、统计附录与病例索引写到新临时目录，与正式文件逐字节一致；没有覆盖原文件。
- state_sync.json：审后导航变更列表，其余被审字节保持。
- manifest.json：本附件及独立审计记录的指纹。

独立完整语义抽查为3例N180/S522/S599，非执行者全部78例；199个锚点全量机械核对不能替代医学语义审查。附件不重复临床正文，不含凭据。
