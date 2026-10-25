# 034 当前状态

状态：执行与自检完成；0 API、0费用、未使用reserved40；尚未进行独立审计。

同一40名development、3675条valid atomic claims上，原VeriFact O预测覆盖3675/3675。

主结果：
- 原VeriFact O：2973/3675，PA 80.90%，MCC 0.4771，false-S 235。
- U2：3012/3675，PA 81.96%，MCC 0.5275，false-S 183。
- U2+A全40 Gate（患者外/LOPO）：2978/3675，PA 81.03%，MCC 0.5317，false-S 137。

U2相对O多39条正确、MCC +0.0503、false-S少52；A Gate相对U2少34条正确、MCC +0.0042、false-S少46。
统一评价与三组主要配对患者bootstrap已重放，自检PASS。

入口：report.md、metrics.csv/json、paired.json、predictions_common.csv、verification_001.json。
