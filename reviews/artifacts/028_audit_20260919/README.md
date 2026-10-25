# 028 独立审计附件

结论见[028审计](../../028_traceable_claim_evidence_verification.md)。

- handoff_snapshot.json / initial_check.json：原791项交审哈希匹配。
- audited_files_sha256.json：除6项可变导航外的785项冻结材料。
- independent_check.py / independent_summary.json：不导入028实现，核验310份回执、Decimal费用/在途占用、空白归一化引用放行、所有新标签、三类参照及患者bootstrap/LOO、11个病例来源和19处C48锚点；检查18,044项历史哈希。网络禁止。
- tests.log / tests_summary.json：8项028＋15项002，23项通过。
- verification.log / verification_summary.json：原核查器实际运行结果；原executor标签不是独立审计结论。全部细项在outputs/028_traceable_claim_evidence_verification/audit_verification_001。
- replay_check.json：16个正式文件实际断网重放一致。

仓库根目录research-verifact环境中，先建立新输出目录：

~~~powershell
python -B reviews/artifacts/028_audit_20260919/independent_check.py outputs/replays/028_independent
~~~

脚本只读研究成果，向指定目录写摘要，不显示密钥或临床正文。病例阅读范围由审计正文明确，程序匹配不代替医学阅读。安全复查见[复现说明](../../../docs/REPRODUCIBILITY.md)。
