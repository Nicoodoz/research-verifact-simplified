# 067 当前状态

## 更正导航（2026-09-23，优先于下方旧状态快照）

068直接核对请求发现：v1的原包ID全空，226次修改实际把约12段原包替换为1–2段；“0显式drop”不能证明保留原包。下方“保守增补”“普遍追加上下文”的方法归因已不成立，199/236等数字仅属于错误实现的历史结果。

v2映射修正后27条改包包含增33段、删38段，最终200/236，但两条final救回未在068重复中重现。v1/v2的历史正式口径互相冲突，不在此择优追认。详见[068核查](../068_final_pack_utility_diagnosis/report.md)与[069更正](../069_final_pack_controlled_repair/067_correction.md)。独立审计未执行；原请求、指标、报告及协议不改写。

## 原状态快照（历史，不能作为现行方法结论）

067 Conservative Requirement-Preserving Evidence Packing 已完成正式执行、离线总评和artifact replay verification。

## 正式结果

评价集：052自然development中T-S有效236条 / 24患者。

Baseline T-S + Frozen PriorG：
- 198/236 correct
- PA 83.90%
- MCC 0.5946
- false-S 6
- S/NS/NA recall = 89.30 / 38.89 / 77.42%

067 Conservative Pack + 同一T-S + 同一Frozen PriorG：
- 199/236 correct
- PA 84.32%
- MCC 0.5819
- false-S 10
- S/NS/NA recall = 90.91 / 50.00 / 64.52%

Paired：
- rescue 14
- harm 13
- net +1
- patient wins/losses/ties = 6/6/12

因此067未通过事前晋级标准，advance=false。

## Raw T-S层

不经过PriorG：
- correct 177/236 -> 177/236
- MCC 0.50585 -> 0.51590
- false-S 3 -> 3
- NS recall 50.00% -> 72.22%
- NA recall 77.42% -> 64.52%

所以packer并非完全无效：它明显把一部分NS从NA中分离出来；但代价是大量真NA被推向NS，整体正确数没有净增。

## Pack行为

227/236可重建C48。
Qwen audit：
- 226/227有效audit最终改变pack
- 424个addition
- 0个drop
- changed pack平均+1.876个passage
- 平均增加约1278字符

这说明当前GT-blind audit触发极度宽松，几乎把“保守补证据”退化成“普遍加上下文”。

Addition roles：
- direct_support 246
- temporal 46
- event_state 41
- scope 32
- numeric_or_trend 26
- direct_contradiction 24
- certainty 5
- negation 4

## 主要诊断

1. 066定位的C48→final pack瓶颈是真实的，但不能用“给几乎每条claim都补1–2段C48”解决。
2. 067避免了065的过度裁剪：0个baseline passage被删除；但问题转成过度增补与context noise。
3. 对GT=NS，新增证据平均使NS score约+19.17、NA约-19.39，明显帮助NS识别。
4. 对GT=NA，新增证据平均使NS score约+10.38、NA约-11.07，说明相邻主题证据会错误地把“不涉及”变成“涉及但不支持”。
5. Raw T-S的false-S没有增加；final false-S从6升到10主要与旧Frozen PriorG在新score几何上的兼容性下降有关。
6. Baseline raw→PriorG为23 rescue /2 harm；新pack raw→PriorG为26 rescue /4 harm。上游改变后PriorG仍能救S，但NS→false-S harm翻倍。
7. 下一版前处理不能继续“普遍augmentation”，必须先解决高精度no-change gate和NA addressability。

## 执行账

正式冻结请求：
- stage1 audit 227
- stage2 T-S Judge 226
- 共453个HTTP200
- 正式费用约 ¥11.839566

另有正式预测完成后出现的superseded stage1v2/stage2v2：
- 252个HTTP200
- 约 ¥8.894004
- request_id与正式请求不同
- 不参与067正式预测/方法选择/指标
- 保留回执，不删除

## Verification

- verification_001：因核验脚本把EHR原文中的“gold”误当GT泄漏、且把冻结后追加的common辅助代码hash变化当硬失败，已superseded。
- verification_002：artifact replay共2984项PASS、0 FAIL。
- warning：common067.py在freeze后有辅助代码追加，源码hash与freeze不同；但stage2 builder hash匹配，冻结stage1/stage2请求体、audit recommendation、pack mapping与final Judge reference均逐条replay通过。
- independent audit未执行。
- reserved=false。
- 未commit/push。
