# 027 独立审计附件

结论见[027审计](../../027_dual_judge_transfer_diagnosis.md)。

- handoff_snapshot.json / initial_check.json：原199项交审哈希匹配。
- audited_files_sha256.json：排除6项可变导航后的193项冻结材料。
- independent_check.py / independent_summary.json：不导入027实现，核验保存概率、排序/AP/患者内AUC、患者bootstrap、精确/近似冲突、组级整数参考、高rescue完整包络、全部病例来源和引文；校验17,905项历史哈希。网络及新拟合均拦截。
- tests.log / tests_summary.json：6项027＋15项002，21项通过。
- verification.log / verification_summary.json：原核查器实际运行结果，原executor标签不代替本次独立审计意见。细项位于outputs/027_dual_judge_transfer_diagnosis/audit_verification_001。
- replay_check.json：11个正式文件实际断网重放一致。

仓库根目录research-verifact环境中，先建立新输出目录再运行：

~~~powershell
python -B reviews/artifacts/027_audit_20260919/independent_check.py outputs/replays/027_independent
~~~

脚本只读成果，向指定目录写摘要。四例完整文本深读是审计者本轮实际工作，摘要中的名单是记录，不是脚本自动完成医学阅读的证明。安全复查见[复现说明](../../../docs/REPRODUCIBILITY.md)。
