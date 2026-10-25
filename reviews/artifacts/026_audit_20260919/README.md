# 026 独立审计附件

结论见[026审计](../../026_frozen_sd_patient_transfer.md)。

- handoff_snapshot.json / initial_check.json：原2,885项交审哈希全部匹配。
- audited_files_sha256.json：除6项当前导航外的2,879项冻结材料。
- independent_check.py / independent_summary.json：不导入026实现，独立核验全部实际回执、训练/内部阈值、冻结与候选时序、条件调用、Decimal费用及含在途峰值、650条预测、混合包络/LOO/bootstrap；核验15,138项历史哈希。
- verification.log / verification_summary.json：审计者运行原核查器的记录；其executor_self_check标签保留，独立结论由审计正文给出。全部细项在outputs/026_frozen_sd_patient_transfer/audit_verification_001。
- replay_check.json：新目录15个正式文件断网重放一致。
- tests.log / tests_summary.json：026七项＋002十五项，22项全部通过。

仓库根目录、research-verifact环境中，先建立新输出目录再独立复算：

~~~powershell
python -B reviews/artifacts/026_audit_20260919/independent_check.py outputs/replays/026_independent
~~~

脚本只读研究材料，向指定目录写摘要，不显示密钥/临床正文。原核查器会在子进程再次运行7项只读单元测试；审计主进程禁止socket和DirectClient.send，子进程测试不调用HTTP。完整安全复查入口见[复现说明](../../../docs/REPRODUCIBILITY.md)。
