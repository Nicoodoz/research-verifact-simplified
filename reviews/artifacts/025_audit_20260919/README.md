# 025 独立审计附件

结论见[025审计](../../025_lambda_flip_risk_separability.md)。

- handoff_snapshot.json / initial_check.json：原94项成果＋4项导航全部匹配。
- audited_files_sha256.json：排除2份可变CURRENT_STATUS后的92项冻结成果。
- independent_check.py / independent_summary.json：不导入025实现，独立重建患者训练集、138个外层模型及内层阈值；用两点混合算法复核22个包络点、全部LOO及SE/SD的1,000次条件患者bootstrap；检查15,046项历史哈希。
- source_replay.log / source_replay_summary.json：重新从冻结输入生成特征等3项文件，逐字节一致。
- verification.log / replay_summary.json：32组预测、LP及标量LOO核验；正式15个核心文件实际断网重放一致。
- tests.log / tests_summary.json：8项025＋15项002，23项全部通过。

独立复算：在仓库根目录和research-verifact环境中，先建立新的输出目录：

~~~powershell
python -B reviews/artifacts/025_audit_20260919/independent_check.py outputs/replays/025_independent
~~~

脚本只读研究成果，向指定目录写独立摘要。完整重放见[复查入口](../../../docs/REPRODUCIBILITY.md)。原图保持字节，本次视觉检查不生成或替换图件。
