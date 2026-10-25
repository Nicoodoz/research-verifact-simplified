# 053：Thinking Scoring Prior-Adjustment Validation

## 结论

053在全部40名development患者上，各抽6条此前未用于051/052的冻结C48 claim，共240条，比较N-S/U2、036 Gate A、T-S+U2、T-S+prior-adjusted G/M，以及原VeriFact。分类性能优先；reason同步只作次级指标。

本轮最强结论是：**prior-adjusted G（TS_PriorG）相对同批 T-S+U2 明确改善，而且不增加false-S。** 这复现并强化了052的类别比例修正信号。

| 方法 | correct/240 | PA | MCC | false-S | S / NS / NA recall |
|---|---:|---:|---:|---:|---|
| 原VeriFact | 194 | 80.83% | 0.4532 | 12 | 90.26 / 50.00 / 35.48% |
| U2 | **203** | **84.58%** | 0.5311 | 14 | **92.31** / 50.00 / 51.61% |
| Gate A | **203** | **84.58%** | 0.5511 | 11 | 91.79 / **57.14** / 51.61% |
| T-S+U2 | 194 | 80.83% | 0.5179 | 8 | 85.13 / 50.00 / **67.74%** |
| **T-S+PriorG** | **201** | **83.75%** | **0.5607** | **8** | 88.72 / 50.00 / **67.74%** |
| T-S+PriorM | 200 | 83.33% | 0.5125 | 12 | 90.26 / 21.43 / 67.74% |

GT构成：S=195、NS=14、NA=31；human=138、LLM=102。

## 1. PriorG 相对 T-S+U2：本轮最强确认

TS_PriorG vs TS_U2：**7 rescue / 0 harm，净+7**；PA +2.92pp，患者cluster bootstrap 95%区间 **[+0.83,+5.00]pp**；MCC +0.0428，95%区间 **[+0.0132,+0.0755]**；false-S变化=0。

这意味着052上发现的prior adjustment并非只在那批240条上偶然改善：在另一批未重复claim上，它再次把thinking评分中漏掉的真Supported捞回，同时没有新增false-S。

PriorM也比TS_U2多对6条，但带来4个额外false-S、MCC略降，因此不如PriorG。

## 2. PriorG 相对两条基线

相对U2：14 rescue / 16 harm，净-2；PA -0.83pp，95%区间[-5.83,+4.17]；MCC +0.0296，区间[-0.101,+0.178]；**false-S 14→8**。S recall下降3.59pp，NS recall相同，NA recall由51.61%升至67.74%。

相对Gate A：14 rescue / 16 harm，净-2；PA -0.83pp；MCC +0.0096；**false-S 11→8**。Gate A的NS recall更高（57.14% vs 50.00%），PriorG的NA recall更高（67.74% vs 51.61%）。

所以PriorG不是在所有指标上支配U2/Gate A，而是形成更均衡的低false-S、高NA recall、高MCC工作点；只牺牲2/240个总体正确。

## 3. 与原VeriFact系统级比较

TS_PriorG vs 原VeriFact：**22 rescue / 15 harm，净+7**；PA +2.92pp，95%区间[-1.67,+7.50]；MCC **+0.1074，95%区间[+0.0058,+0.2111]**；false-S **12→8**。

三类recall：S 88.72% vs 90.26%，NS 50.00% vs 50.00%，NA **67.74% vs 35.48%**。因此主要系统级收益来自NA识别和更好的整体类别平衡，而不是继续推高S recall。

## 4. 作者路由：可作为额外性能工作点

纯离线探索中，作者类型作为可观测路由特征得到两个工作点：

| 方法 | correct/240 | PA | MCC | false-S | S / NS / NA recall |
|---|---:|---:|---:|---:|---|
| AuthorG：human→PriorG，LLM→U2 | 203 | 84.58% | **0.5689** | **9** | 89.74 / 35.71 / **74.19%** |
| AuthorM：human→PriorM，LLM→U2 | **204** | **85.00%** | 0.5567 | 11 | 91.28 / 21.43 / **74.19%** |

AuthorG在PA上追平U2/Gate A，同时MCC更高、false-S更低、NA recall更高；代价是NS recall下降。AuthorM取得本轮最高correct/PA，但NS recall更低。它们是性能导向的探索工作点，不作为053主方法，因为类别间trade-off明显。

## 5. Final label / reason结构同步

原分析脚本误读reason字段位置，导致summary.csv中同步率错误为0；分类预测和所有分类指标不受影响。修正结果记录于reason_sync_corrected.csv：

- U2：210/240 = 87.5%；
- Gate A：214/240 = 89.17%；
- T-S+U2：224/240 = **93.33%**；
- T-S+PriorG：217/240 = **90.42%**；
- T-S+PriorM：209/240 = 87.08%；
- AuthorG：215/240 = 89.58%；AuthorM：209/240 = 87.08%。

同步定义仅为“所选reason存在且生成该reason时的raw verdict等于final label”；它不等同于reason语义正确或citation完全grounded。按用户原则，分类性能优先，因此PriorG的90.4%结构同步可接受，不用同步Gate回退分类收益。

## 6. T-S无效输出与fallback

T-S核心无效3/240：1条thinking达到8192 token长度上限且无完整JSON；2条正常stop但缺label_scores。三个T-S scoring候选均按事前固定规则回退同期N-S U2，因此主表保持240/240完整覆盖。没有因输出内容重跑任何HTTP200。

## 7. 费用与完整性

主DeepSeek 480/480完成；fresh U2候选29条，Qwen Gate peer 29/29完成。总API 509次，509/509 HTTP200，usage估算费用 **¥9.87753 / ¥15 hard cap**，符合余额收缩要求。

Executor verification：**974项PASS**。240条样本覆盖40名development患者、每患者6条，且具体claim ID与051/052样本不重叠；main body只含proposition/reference；thinking/non-thinking参数逐条核验；Qwen集合可由fresh N-S U0→U2候选重建；attempt/receipt唯一绑定。

本任务允许患者复用于性能开发，因此证据定位为development内部新claim复制，不冒充外部或reserved确认。

## 8. 当前研究判断

1. **主保留：T-S + PriorG。** 它在053再次稳定优于T-S+U2：+7 correct、0 harm、MCC和PA bootstrap区间均为正，false-S不增加。
2. **U2/Gate A仍是高PA基线。** PriorG相对它们只少2个正确，但false-S明显更低、NA recall更高、MCC最高。
3. **PriorM不如PriorG。** 虽然PA略高于PriorG，但NS recall和false-S更差。
4. **AuthorG/AuthorM可保留为性能工作点。** AuthorG尤其值得以后继续看：PA追平U2/Gate A，MCC最高0.5689，false-S仅9；但当前NS recall只有35.71%，不宜直接替代主线。
5. reason同步作为次级目标：PriorG结构同步约90.4%，没有出现“为了更好分类就完全失去解释同步”的情况。

下一步若继续开发，优先围绕PriorG/AuthorG做低成本离线或少量定向验证，而不是重新开启N-V/T-V、检索或复杂Gate路线。
