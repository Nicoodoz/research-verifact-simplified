# 044 当前状态

044执行已完成，冻结evaluation已收尾；当前为 **PASS_WITH_PROVENANCE_WARNING**。独立审计未执行。

Development-only、患者隔离：
- 训练10名患者、固定240条；
- evaluation 8名不同患者、696条；
- reserved overlap=0。

模型训练：
- 434个有效utility pair；
- 原始+1仅10个，reason/evidence筛后真正+1仅1个；
- OOF 240条中238条不追加，Score净−1，U2净0。

Evaluation：
- 696条中learned选择base 693条、time 3条；
- 1443个唯一DeepSeek请求中1434个有可解析HTTP200结果（1432 valid、2 format anomaly），1个invalid core；
- 原中断留下8个无receipt未知请求未重发；
- 三条件共同有效主分析687条。

687条上：
- base Score 512/687，learned 513/687：1 rescue / 0 harm，false-S不变；
- base U2 562/687，learned 563/687：1 rescue / 0 harm，false-S不变；
- rank Score净−1，rank U2净−6。

learned唯一真实救回：
“The patient was eventually cleared for transfer.”
追加后续护理证据“Pt to Tx to [ward] 11, has bed.”后，DeepSeek从NS→S；GT盲Qwen reason/evidence audit从joint fail→joint pass。

结论：增量证据机制存在，但当前utility模型正例过稀，尚不足以形成稳定可泛化的新主方法。

费用：已用或预留约 **¥29.993616 / ¥80**。

完整性警告：
common044.py、prepare044.py、protocol.md 当前版本与freeze时源码哈希不一致；冻结inputs/model/choices/eval jobs/mapping保持完整，数值已从真实receipt独立重建。不能声称当前源码可完整重建方法生成过程。

入口：report.md · results_recovery_001/summary.json · eval_audit_recovery_001/summary.json · verification_recovery_001.json
