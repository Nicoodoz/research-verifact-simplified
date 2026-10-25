# 053 当前状态

053已完成：40名development患者，每患者6条此前未用于051/052的冻结C48 claim，共240条；仅运行N-S和T-S两路DeepSeek，fresh U2候选29条补Qwen Gate peer。

核心结果：
- 原VeriFact：194/240，PA80.83%，MCC0.4532，false-S12；
- U2：203/240，PA84.58%，MCC0.5311，false-S14；
- Gate A：203/240，PA84.58%，MCC0.5511，false-S11；
- T-S+U2：194/240，PA80.83%，MCC0.5179，false-S8；
- **T-S+PriorG：201/240，PA83.75%，MCC0.5607，false-S8，S/NS/NA recall=88.72/50.00/67.74%**；
- T-S+PriorM：200/240，PA83.33%，MCC0.5125，false-S12。

PriorG vs T-S+U2：7 rescue / 0 harm；ΔPA +2.92pp [0.83,5.00]；ΔMCC +0.0428 [0.0132,0.0755]；false-S无变化。
PriorG vs U2：净-2 correct，但false-S -6、MCC +0.0296、NA recall +16.13pp。
PriorG vs Gate A：净-2 correct，但false-S -3、MCC +0.0096、NA recall +16.13pp。
PriorG vs原VeriFact：净+7 correct，ΔMCC +0.1074 [0.0058,0.2111]，false-S -4。

探索作者路由：AuthorG=203/240，PA84.58%，MCC0.5689，false-S9，S/NS/NA recall=89.74/35.71/74.19%；AuthorM=204/240，PA85.00%，MCC0.5567，false-S11，但NS recall仅21.43%。

结构reason-sync修正后：U2 87.5%，GateA 89.17%，TS_U2 93.33%，TS_PriorG 90.42%，TS_PriorM 87.08%，AuthorG 89.58%，AuthorM 87.08%。原summary.csv中的0是parser nesting分析bug，分类结果不受影响；正式同步率看reason_sync_corrected.csv。

T-S无效3/240，均按冻结规则fallback到同期U2；无HTTP200内容重跑。

API 509次、509/509 HTTP200，费用¥9.87753/¥15 cap。verification 974项PASS。独立审计未执行。无reserved使用，无commit/push。
