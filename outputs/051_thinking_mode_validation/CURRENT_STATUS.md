# 051 当前状态

051 thinking-mode validation 已完成 preflight、48条balanced screen、24条语义最小对照、96条患者隔离confirmation；executor verification PASS，独立审计未执行。

核心确认结果（96条，S/NS/NA各32）：
- N-S：non-thinking scoring + 固定U2，62/96正确，MCC 0.4920，false-S 21。
- N-V：non-thinking ordinary Judge，67/96正确，MCC 0.5557，false-S 15。
- T-S：thinking-high scoring 的raw verdict，63/96正确（1条核心JSON无效按错计），false-S 9。
- T-V：thinking-high ordinary Judge，65/96正确，MCC 0.5180，false-S 9。

T-V相对当前N-S+U2：14 rescue / 11 harm，净+3；false-S 21→9（-12）；患者方向4正/2负/2平。S recall 93.75%→78.13%，NS 46.88%→62.50%，NA 53.13%→62.50%。因此thinking主要改变了风险/类别权衡，而不是单向提高所有类别。

T-V相对N-V：11 rescue / 13 harm，净-2；false-S 15→9。N-V仍是本批正确数和MCC最高的单调用Judge；T-V是更保守、false-S更低的风险工作点，而非总体accuracy winner。

患者cluster bootstrap（固定预测1000次）：T-V−N-S ΔPA约+3.1pp，95%区间[-7.45,+13.33]pp；ΔMCC区间[-0.121,+0.168]；Δfalse-S区间[-20,-5]。分类增益不确定，但false-S下降在本批患者bootstrap中方向稳定。

语义最小对照：N-V 22/24、10/12组双项全对；T-V 24/24、12/12组双项全对。T-V修正了non-thinking对“计划≠完成”和“条件计划≠已经执行”的两处NS/NA边界错误。

总API 652次、652/652 HTTP200；累计usage估算约¥11.900463 / 50元任务cap。Confirmation 384次均收到HTTP200；仅T-S一条最终JSON核心不可解析，未重跑。executor verification 7200项PASS。
