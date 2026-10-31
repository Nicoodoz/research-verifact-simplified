#139 full_repeat：screen160

目标160，返回160，有效160，无效0，缺失0。无效和缺失不补旧答案。

|配置|MCC|PA|正确|false-S/非S|Macro-F1|S/NS/NA召回|
|---|---:|---:|---:|---:|---:|---|
|full_pool120|0.5114|76.25%|122|20/57|0.5976|95.15%/25.00%/54.55%|
|claim_repeat136|0.5707|78.75%|126|17/57|0.6384|94.17%/25.00%/69.70%|
|label_only107|0.4912|71.88%|115|10/57|0.6107|80.58%/37.50%/69.70%|
|midpoint132|0.5118|75.62%|121|17/57|0.6058|91.26%/25.00%/63.64%|
|extra_steps137|0.5937|79.38%|127|15/57|0.6923|92.23%/50.00%/60.61%|
|paper_r1|0.4198|71.25%|114|23/57|0.5630|90.29%/37.50%/36.36%|
|full_repeat|0.5848|79.38%|127|16/57|0.6629|94.17%/33.33%/66.67%|

相对120：ΔMCC+0.0734，Δ正确+5，Δfalse-S-4。

相对136：ΔMCC+0.0142，Δ正确+1，Δfalse-S-1。

原作者提示两9B基线的共同覆盖为158，104未微调9B共同覆盖为154；独立同ID表见JSON，不跨覆盖作差。

三类precision/recall/F1、混淆矩阵、false-S率和预测S假发现率、患者/作者/面板方向见JSON。完整1817按1000次患者bootstrap；不覆盖历史选型或新医院泛化。
同120权重，完整原文；batch1和32768容量与原缓存运行设置不同，未声称逐位一致或理由自洽。

扩大信号：{"applicable": true, "quality_signal": true, "risk_signal": true, "guards": {"valid_coverage": true, "all_first_requests_returned": true, "no_large_false_S_jump": true, "no_major_class_collapse": true, "no_near_zero_class": true}, "continue_signal": true}
