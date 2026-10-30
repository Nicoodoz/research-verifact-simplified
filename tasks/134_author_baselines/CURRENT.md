# 134 author_baselines：完整统一比较已完成

两个9B各1817首次回执，paper_r1复用1817历史结果。严格共同有效1793：author_base9b MCC .3422、正确1210、FS44/361；author_lora9b .6104、1562、100/361；paper_r1 .4819、1468、105/361。

120适配器对同模型未微调有真实收益与NS/false-S代价；作者接口对104接口120少对15条、FS少9，未全面胜出。11/13条无效原样保留、不补旧答案；166个有效适配器判定缺reason。全部私有回执已回传，GPU计算结束，未关机。窗口截至134回传累计估算7.62元，后续继续累计。

下一研究为135 reason_first；133仍未训练。

[完整报告](../../outputs/134_author_baselines/report.md) · [详细结果](../../outputs/134_author_baselines/full1817.md)
