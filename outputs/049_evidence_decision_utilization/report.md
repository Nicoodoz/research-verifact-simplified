# 049：Evidence Decision Utilization

## 核心结论

049没有找到值得进入患者隔离confirmation的决策利用机制，按事前门槛停止。结果说明：048已经查出的requirements、quotes和relations本身有可读信息，但把它们作为Gate或提示交给DeepSeek，并没有稳定优于当前Fresh-U2。

### 0 API规则诊断

|方法|正确/16|false-S|相对U2变化|
|---|---:|---:|---:|
|U2|9|2|—|
|A：明确反证否决|6|0|−3正确|
|B：直接audit label|5|1|−4正确|
|Hard：全部支持才放行|5|0|−4正确|

A虽然消除了2条false-S，但同时误杀更多真Supported；028的“过度保守Gate”问题没有因为只用contradiction就自动消失。

### 收费DeepSeek screen

Fresh-B先重新评分，13/16在本轮真正满足raw非S且U2=S；其余3条按协议不触发方法。

|方法|最终正确/16|false-S|rescue/harm/net vs Fresh-U2|
|---|---:|---:|---:|
|Fresh-U2|10|3|baseline|
|E：同证据只追加原文，取新raw|2|0|2/10/−8|
|C：requirements→quotes，无relation|5|0|2/7/−5|
|R：requirements+relation|3|0|2/9/−7|
|E的λ2辅助|9|1|1/2/−1|
|C的λ2辅助|8|2|0/2/−2|
|R的λ2辅助|7|0|2/5/−3|

三条方案均不过accuracy或risk晋级门槛。

## Requirement alignment没有显示独立作用

C相对E的raw正确数从2提高到5，看起来有局部作用。但在事前固定的5条可打乱病例中，把完全相同的quotes/evidence IDs循环错配到别的requirement后：
- C与打乱control标签差异：0/5；
- C正确2/5，control也2/5。

因此本批没有证据说明“正确的requirement↔quote对应关系”是C变化的原因。更可能的解释包括：额外结构化文字本身改变了Judge，或者DeepSeek主要依赖原reference而没有真正使用对应关系。不能把C−E差异包装成语义对齐成功。

带relation的R更差，说明把独立audit的关系判断显式交给最终Judge并没有提供可靠增量，也可能进一步强化过度保守。

## 运行稳定性

固定6条repeat：
- Fresh-B raw：0/6变化；
- C raw：0/6；
- R raw：0/6；
- Fresh-B的U2：2/6变化。

这与043、047、048反复出现的现象一致：DeepSeek最终verdict在这些病例上较稳定，而label_scores在固定λ边界附近存在足以改变U2的运行波动。

## 研究判断

049否定的是当前这几种“查证结果直接参与决策”的实现，不是否定证据本身：
- 硬Gate降低风险但严重丢真S；
- 直接audit没有超过U2；
- 将requirements/quotes/relations放进最终prompt无法替代λ，并且正确quote配对没有显示特异价值。

因此不继续在049里调prompt、Gate阈值或组合条件。新的明确问题是：既然raw稳定而U2不稳定，固定λ的输入score是否可以通过多次同prompt scoring的稳健聚合变得更可靠。该问题未被现有repeat/trace Gate实验直接回答，因此按用户授权另立050。

## 成本与完整性

049新增DeepSeek调用78次，78/78 HTTP200，usage估算¥1.013049。执行者verification 100项PASS；没有confirmation API调用。独立审计未执行。
