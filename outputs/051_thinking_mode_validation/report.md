# 051：Thinking Mode and Scoring Interface Validation

## 核心结论

051首次在本项目中正式比较同一 deepseek-v4-flash-0731 的 thinking 与 non-thinking 模式，并把“是否要求模型同时输出 label_scores”作为第二个独立因素。

最重要的结论不是“thinking全面更准”，而是：

> thinking显著改变了当前系统的风险—类别权衡：相对 non-thinking scoring + 固定λ2，它大幅减少 false-S，并提高NS/NA识别，但会牺牲一部分真实Supported召回；相比普通non-thinking Judge，它仍不是总体准确率winner。

96条患者隔离confirmation（S/NS/NA各32）：

| 条件 | 最终输出 | 正确/96 | PA | MCC | false-S | S/NS/NA recall |
|---|---|---:|---:|---:|---:|---|
| N-S | non-thinking scoring + 固定U2 | 62 | 64.58% | 0.4920 | 21 | 93.75 / 46.88 / 53.13% |
| N-V | non-thinking ordinary verdict | **67** | **69.79%** | **0.5557** | 15 | 87.50 / 53.13 / 68.75% |
| T-S | thinking-high scoring raw verdict | 63* | 65.63%* | 0.4960** | 9 | 75.00 / 59.38 / 62.50% |
| T-V | thinking-high ordinary verdict | 65 | 67.71% | 0.5180 | **9** | 78.13 / 62.50 / 62.50% |

* T-S有1条HTTP200但最终content不是可解析JSON，按96分母计错；其余95条有效。  
** MCC按95条有效核心结果计算。

因此：
- T-V相对当前N-S+U2：**+3正确，false-S -12**；
- T-V相对N-V：**-2正确，false-S -6**；
- N-V仍是本批正确数与MCC最高的单调用方案；
- T-V提供的是一个明显更低false-S、但更保守的替代工作点，而不是全面支配。

## 1. 设计与隔离

051没有继续使用048-050反复分析的8名患者。031剩余development材料中的16名患者按固定患者hash分成8名screen、8名confirmation，患者完全不重叠。

Screen固定48条，S/NS/NA各16；Confirmation在任何051 screen结果出现前冻结96条，三类各32。GT仅用于预先声明的类别均衡诊断抽样，不进入任何API请求或模型特征。

四个条件只改变thinking与scoring接口：
- N-S：non-thinking + scoring，正式最终输出为固定λ2的U2；
- N-V：non-thinking + ordinary verdict；
- T-S：thinking-high + scoring，正式主输出为raw verdict；
- T-V：thinking-high + ordinary verdict，为主要thinking候选。

Thinking固定 enable_thinking=true、reasoning_effort=high、max_tokens=8192；non-thinking保持enable_thinking=false、max_tokens=2048。没有在结果后搜索low/max、改prompt或重新选λ。

接口preflight在正式screen前完成。四条件均HTTP200、最终content可解析；thinking条件实际返回reasoning_content。随后才冻结screen criteria、语义行为测试和预算修订。

## 2. Screen为什么让T-V晋级

48条balanced screen中：
- N-S：35/48正确，false-S=7；
- N-V：33/48，false-S=4；
- T-S：35/48，false-S=0；
- T-V：36/48，false-S=1。

T-V相对N-S+U2为6 rescue / 5 harm，净+1，但false-S从7降到1；按事前风险通道达到screen晋级要求。T-V相对N-V为6/3，净+3。固定6条同输入repeat中四条件均0次标签变化，因此没有触发额外稳定性screen。

Screen同时包含12组、24条合成语义最小对照。N-V为22/24、10/12组两条都正确；T-V为24/24、12/12组全对。N-V的两处错误都是把明确未完成的事件判成Not Addressed，而T-V正确判为Not Supported：
- 已记录“计划CT”，但没有完成记录；
- “若发热则启用ceftriaxone”，患者始终无热。

这组结果只说明目标语言边界行为，不是新增医生gold，也不混入临床PA/MCC。

## 3. Confirmation：thinking的收益主要是降低错误支持

T-V相对N-S+U2：14 rescue、11 harm，净+3；rescue覆盖6名患者、harm覆盖5名患者。患者正确数方向为4正、2负、2平。

类别变化解释了为什么总正确数只增加3，但风险明显改善：
- Supported正确数：30→25（-5）；
- Not Supported：15→20（+5）；
- Not Addressed：17→20（+3）；
- false-S：21→9（-12）。

也就是说，thinking ordinary Judge明显收回了部分λ2推向Supported的判断，把更多non-S病例留在NS/NA；其中一些是正确修复，也会漏掉部分真实Supported。

固定预测的1000次患者cluster bootstrap：
- T-V−N-S ΔPA均值约+3.09个百分点，95%区间[-7.45,+13.33]；
- ΔMCC均值约+0.0265，95%区间[-0.121,+0.168]；
- Δfalse-S均值约-12，95%区间[-20,-5]。

因此不能宣称总体PA/MCC已稳定显著提高；但在本批8名confirmation患者的cluster bootstrap中，false-S下降方向较稳定。

相对N-V，T-V为11 rescue / 13 harm，净-2；false-S 15→9。N-V在本批balanced confirmation上拥有最高正确数与MCC，因此thinking不是简单accuracy升级，而是更偏风险控制的工作点。

## 4. Thinking与scoring接口不是同一件事

051把这两个因素拆开后发现：thinking本身并没有让scoring接口的raw verdict明显变好。Confirmation共同有效95条上，T-S raw相对N-S raw为10 rescue / 10 harm，净0。

在thinking内部，T-V相对T-S raw为6 rescue / 4 harm，净+2；这说明“开启thinking”与“是否同时要求0–100 label_scores”存在交互，不能把所有差异只归因于推理计算量。

辅助结果也说明固定λ不应直接无条件移植到thinking scores：
- N-S raw：63/96正确，false-S 12；N-S U2：62/96，false-S 21；
- T-S raw：63/95有效，false-S 9；T-S U2：64/95，false-S 11。

这批数据是类别均衡诊断样本，不代表自然总体prevalence；尤其不能据此回写036中固定λ2在reserved自然队列上的既有结论。但它说明：改变推理模式或评分分布后，旧λ的风险工作点必须重新评价，不能假定保持不变。

## 5. 标签与解释：T-V解决了“后处理标签没有同步reason”的结构问题，但没有解决所有grounding问题

T-V的最终label、reason和checks来自同一次thinking回答，因此不会出现“原Judge写NS reason、离线λ把标签改成S”的结构性不同步。这一点比U2天然更干净。

但同次生成不等于解释一定可靠。对96条confirmation T-V做结构化引用复核：
- 96/96都有非空reason；
- 94/96至少引用一个reference编号；
- 84/96所有整数引用都能对应到实际reference block；
- 12/96至少存在一个超出/不对应现有reference编号的引用。

因此051可以说T-V消除了post-hoc label/reason不同步这一结构来源，但不能声称已经解决了证据grounding或citation correctness。后续若把T-V作为解释方法，需要专门处理引用合法性与语义充分性。

## 6. 稳定性、计算量与费用

Screen固定6条病例对四条件各做一次repeat，N-S、N-V、T-S、T-V均6/6标签一致。这个小重复集没有显示thinking降低稳定性，但分母只有6，不能当作总体稳定性证明。

Thinking确实使用了额外推理计算。Confirmation中：
- T-S reasoning tokens平均约1729，中位1539；
- T-V reasoning tokens平均约1455，中位1168。

整个051共652次请求，652/652 HTTP200。按保存usage与3/9元每百万token登记口径，累计估算约¥11.900463 / 50元任务cap；其中confirmation 384次约¥7.473747。没有因结果重跑HTTP200，也没有使用Qwen/BGE新调用。

四条件全任务调用/费用：
- N-S 145次约¥1.835277，另6次repeat约¥0.076752；
- N-V 169次约¥1.812522，另6次repeat约¥0.072063；
- T-S 145次约¥4.094235，另6次repeat约¥0.134100；
- T-V 169次约¥3.743286，另6次repeat约¥0.132228。

这些全任务数字包含preflight、screen、semantic或confirmation的不同角色，不应直接解释为单次部署成本比；但thinking明显增加输出token和费用，这个代价需要与false-S下降一起报告。

## 7. 研究判断

051给出了一个比042-050更清晰的正向机制信号：同一证据、同一模型快照下，thinking ordinary Judge在两个患者隔离阶段都表现出更低false-S，并且在预定义的计划/完成、条件句等语义边界测试中优于non-thinking ordinary Judge。

但它没有成为新的总体winner：
1. Confirmation中N-V正确67/96、MCC0.5557，仍高于T-V的65/96、MCC0.5180；
2. T-V相对N-S+U2虽然+3正确并少12条false-S，但PA/MCC患者bootstrap区间跨0；
3. T-V的主要收益是从Supported转向更谨慎的NS/NA，伴随S recall下降；
4. citation结构仍有12/96不完全合法。

因此最准确的定位是：

> **Thinking不是一个全面提高accuracy的替代方案，而是一个有证据支持的低false-S、较强限定条件推理工作点；普通non-thinking verdict仍是本balanced confirmation中正确数最高的单调用基线。**

这也解释了为什么原VeriFact论文专门分析推理能力是有价值的：模型是否真正处理计划/完成、否定、时间和不确定性，确实会改变核验错误结构；但更强推理不等价于所有类别同时改善。

## 8. 结论边界与下一步

051不修改036的reserved最终结果，也不重新选择036部署参数。96条confirmation是类别均衡的development内部确认，不是自然prevalence总体，也不是新的reserved test。

当前可以支持：
- thinking-high在相同C48证据上显著改变风险结构；
- 相对N-S+U2，T-V在confirmation上少12条false-S并净多3条正确；
- 语义最小对照24/24，显示其在本组限定条件测试中优于N-V；
- T-V的label与reason来自同一次判断，避免U2式post-hoc reason不同步。

当前不能支持：
- thinking全面优于non-thinking；
- T-V总体PA/MCC已显著提高；
- thinking解决了citation/grounding问题；
- 用thinking结果重新调λ并宣称新winner；
- 将balanced development结果外推到真实医院prevalence。

如果继续研究，优先级应从“再改检索/再加Gate”转向两件事：一是对T-V的解释grounding和引用合法性做专门修复；二是在真正自然分布、未参与开发的外部或新增评价材料上比较N-V与T-V的风险—准确率前沿。不能再用已消费reserved40调方法。
