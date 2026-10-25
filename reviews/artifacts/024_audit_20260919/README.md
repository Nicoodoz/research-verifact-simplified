# 024 独立审计附件

结论见[024审计](../../024_lambda2_transfer_validation.md)。

- handoff_snapshot.json / initial_hash_check.json：原7,340项成果和4项导航全部匹配。
- audited_files_sha256.json：排除2份可变CURRENT_STATUS后的7,338项冻结成果。
- raw_audit.py / raw_summary.json：不调用024解析器，独立复核全部回执、核心字段、重试、Decimal费用、在途占用、42项配对和40行患者补表；禁止网络，不输出临床正文或密钥。
- verification.log / replay_summary.json：只读输入/费用及84项守恒检查，15个核心文件实际重放一致。
- tests.log / tests_summary.json：28项024＋15项002，43项全部通过。

仓库根目录、research-verifact环境中，先建立新的输出目录，再运行：

~~~powershell
python -B reviews/artifacts/024_audit_20260919/raw_audit.py outputs/replays/024_independent
~~~

脚本只读研究成果，向指定目录写摘要；完整重放见[环境与复查](../../../docs/REPRODUCIBILITY.md)。本次审计全部研究计算禁用socket网络，没有运行收费入口。
