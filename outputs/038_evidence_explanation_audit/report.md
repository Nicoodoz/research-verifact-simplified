# 038：证据—标签—解释一致性审计

## 核心结论

**036/λ路线的claim-level标签结果仍成立，但不能再把“标签改对”直接写成“证据核验能力增强”。038确认了两个不同层面的缺口：后处理后的最终标签与原解释存在结构性冲突；同时，U2救回的真实Supported样本中，只有一部分能被盲自动审计明确地从实际C48中重新建立完整支持。**

本轮不修改任何036预测、λ、Gate或标准后处理。038是在reserved已经完成后开展的post-hoc审计，只用于界定论文主张。全部审计输入、原始HTTP200和结果保存；0次检索/原Judge重跑，新增审计API费用约12.052元。

最重要的四点：

1. U2最终判Supported的2647条中，346条（13.07%）继承自一个原scoring verdict为non-S的回答；其中342条就是U0非S→U2 S的边界翻转，另外4条是原score argmax与原verdict本来就不一致。
2. 对这346条只给“最终标签+原reason/checks”做语义一致性审计，Qwen **346/346均判定为contradictory**。
3. 对全部342条U2翻转和120条固定hash稳定对照，盲审计只看原claim+C48。219条GT=Supported救回中，Qwen有效214条，仅68条判Supported（31.78%），51条达到严格trace-supported（23.83%）。
4. 这不能反推“其余76%一定没有证据”：自动审计本身偏保守，且DeepSeek审计与原scoring属于同一模型家族。正确结论是：**证据充分性尚未被现有label指标证明，且U2翻转样本比稳定S样本明显更不清晰。**
## 1. 为什么要做038

036的scoring Judge一次生成verdict、reason、checks和三类label_scores。U0/U2、Std_M/V等后处理读取score重新决定最终标签，但不会重新生成reason/checks。

因此系统中实际存在两个对象：

- 原Judge的“verdict + reason + checks”；
- 离线后处理得到的“最终label”。

038直接审计这两个对象之间的关系，以及U2翻转是否能由Judge实际看到的C48证据重新支持。

本轮证据审计完全盲化：模型只收到原claim与原C48 reference。GT、U0、U2、Gate、原verdict、原reason均不进入证据审计请求。审计完成后才连接GT与R/H/W。

## 2. 最终标签与原解释到底有多少不一致

“最终S继承non-S解释”指：该方法最终输出Supported，但同一次scoring回答原verdict不是Supported，因此保存的原reason/checks原本是在解释一个non-S判断。

| 方法 | 最终标签与原verdict不同 | 最终S继承non-S解释 | 占该方法最终S比例 |
|---|---:|---:|---:|
| U0 | 43 | 4 | 0.17% |
| **U2** | **382** | **346** | **13.07%** |
| Gate_A | 281 | 242 | 9.52% |
| Std_G | 515 | 479 | 17.23% |
| Std_M | 581 | 473 | 17.05% |
| Std_V | 802 | 481 | 17.29% |
| Joint_NLL / U4 | 517 | 481 | 17.29% |

这个问题不是U2独有，而是所有“改变最终label但复用原解释”的后处理共有。
### 解释语义审计

对U2的346条冲突，只向Qwen提供最终标签Supported、原verdict、原reason和原checks，不给GT和C48；任务仅判断“这段解释是否与最终Supported语义一致”。

结果：**346/346 = contradictory**。

原reason大量明确写出“not fully supported”“does not state”“no evidence”“not addressed”等结论，而最终离线label已经变为Supported。该结果只证明文本解释与最终label冲突，不评价哪个label在医学上更正确。

## 3. C48证据能否支持U2救回

审计集合：

- 全部342条 U0非S→U2 S；
- 固定hash抽取40条稳定S、40条稳定NS、40条稳定NA对照；
- 共462条，每条分别由Qwen3.8-27b和DeepSeek-V4-Flash-0731审计；
- 要求拆分claim实质要求，标注supported/contradicted/unaddressed/uncertain，并引用实际C48编号和短原文；
- 只有覆盖完整、全部要求supported、且引用可在对应reference中逐字定位时，才记为strict trace-supported。

两模型全部请求HTTP200。结构化有效率：Qwen 451/462，DeepSeek 440/462。33个无效结构回答保留原回执，不重跑、不当成non-S。
### 主结果

| 组别 | N | Qwen有效 | Qwen判S | Qwen strict trace-S | DeepSeek有效 | DeepSeek判S | DeepSeek strict trace-S |
|---|---:|---:|---:|---:|---:|---:|---:|
| **R：GT=S，U2救回** | **219** | **214** | **68** | **51** | **206** | **2** | **2** |
| H：原U0正确non-S，被U2伤害 | 42 | 42 | 5 | 3 | 39 | 0 | 0 |
| W：原U0已错non-S，又被改S | 81 | 79 | 9 | 8 | 78 | 0 | 0 |
| 稳定S对照 | 40 | 39 | 30 | 24 | 39 | 21 | 20 |
| 稳定NS对照 | 40 | 40 | 6 | 5 | 38 | 0 | 0 |
| 稳定NA对照 | 40 | 37 | 1 | 1 | 40 | 0 | 0 |

R中，Qwen有效样本的Supported率为31.78%，严格trace-supported率为23.83%；DeepSeek分别为0.97%和0.97%。两个审计都有效的201条R中，133条（66.17%）两者都给non-S，2条两者都给S，另有66条为Qwen S / DeepSeek non-S。

DeepSeek就是原scoring的同一模型家族，因此它高度复现原保守判断并不构成独立外部证据。更有信息量的是：即便换成Qwen盲审，R的S率仍远低于稳定S对照；但Qwen也会漏掉部分稳定S，因此不能把31.78%或23.83%解释成真实“证据充分率”。
## 4. 这些R为什么会分裂

固定hash spot-check显示两类现象。

### A. 有较强C48支持，但模型对“完整支持”的严格程度不同

Qwen判S而DeepSeek仍判non-S的例子包括：

- atorvastatin由20 mg变为80 mg；Qwen认为足以支持“本次住院增加剂量”，原reason/DeepSeek要求更显式的increase动作表述；
- segment VIII低密度灶may represent cholangiocarcinoma；Qwen认为影像把cholangiocarcinoma列为可能性即可，DeepSeek因报告同时写less likely而拒绝；
- serial ECG中出现sinus tachycardia rate slower / rate has decreased；Qwen认为支持心率改善；
- vancomycin有明确用药/给药记录，但原reason把was placed on vanco要求成显式措辞；
- 当前住院有nystatin治疗oral thrush，Qwen认为支持had thrush。

这些例子说明部分R确实更像**语义等价与决策严格度**问题。

### B. 医生GT=S，但C48对claim中的限定词/关系只给部分支持

两模型都给non-S的例子包括：

- closely monitored for leukocytosis：C48只有continue to trend，没有closely的强度；
- again hemodynamically stable：生命体征可提示稳定，但again的时间关系不清；
- family made the decision to transition to comfort measures only：C48写计划与家属讨论，未明确决定已完成；
- repeat wrist tap revealed a small amount of crystal-negative fluid：有重复tap/无晶体，但small amount未出现；
- coumadin adjusted for subtherapeutic INR：有剂量调整，但C48记录过elevated INR，未明确调整原因是subtherapeutic。

这类样本说明：**医生claim-level GT与当前C48可见证据不是同一个评价对象。**后处理命中医生GT，不代表C48已足以逐项论证完整claim。
## 5. 对λ研究主张的影响

038不推翻036的最强统计结论：

> 在完全相同的score和C48条件下，固定λ=2使最终label与医生claim-level GT的一致性显著提高。

但论文表述必须从“提升证据核验能力”收紧为：

> **提升固定评分条件下的决策层label agreement / decision utility。**

目前不能直接写：

- U2找到了更多正确证据；
- U2让模型更好理解了病历；
- 219条R都是有充分C48证据的真实核验救回；
- 最终Supported都配有与之相符的证据解释；
- 标签改对等于引用/证据忠实性得到改善。

更准确的三个评价对象应分开：

1. **决策标签**：已有036完整GT评价；
2. **实际输入证据充分性**：038只有自动化审计，尚无医生级gold；
3. **解释与最终标签一致性**：038明确发现后处理不同步，U2的346条冲突全部被reason审计判为contradictory。

因此，当前U2适合作为一个**decision-layer post-processing method**，而不是完整的evidence-grounded explanatory verifier。
## 6. 论文中怎么处理解释

当前版本不能把原reason直接展示在后处理后的final label下面而不加说明。建议明确：

- 原reason/checks属于pre-adjustment scoring Judge；
- final label属于post-hoc decision layer；
- 若两者不一致，当前研究只评价final label，不声称原reason是final label的解释；
- 真正部署时应重新生成/验证与final label一致的证据说明，或对无法建立一致证据的样本选择abstain/人工复核；这一步尚未由本研究验证。

简单地在看到U2=Supported后要求LLM“写一个支持理由”不能解决证据忠实性，因为那可能只是事后合理化。若未来增加解释重生成模块，必须单独评价证据引用、完整claim覆盖、label一致性和额外成本。

## 7. 审计边界

- 038证据审计是两种LLM的自动化盲审，不是医生重新标注。
- Qwen是不同模型；DeepSeek与原scoring同模型家族，两者不能当新的临床gold。
- 自动审计自身会漏掉稳定S，因此不能用“审计非S”直接证明C48医学上不支持。
- 038未回查完整EHR去补C48，这是有意的：本任务问的是036实际输入证据能否支持最终输出。
- 038使用reserved已消费后的结果做post-hoc一致性审计，不重新选择任何方法。
- 第二数据来源/外部医院泛化仍是另一个独立缺口，038没有解决。
## 8. 执行与核验

- 462个证据案例 × 2模型 = 924个证据审计请求；
- 346个U2解释冲突 × Qwen = 346个解释审计请求；
- 合计1270个HTTP200，未重跑任何HTTP200；
- 实际usage估算约12.052014元，038保护上限60元；
- 原始request/receipt完整保存；
- 初次本地引用校验曾因正则转义错误把真实quote误判invalid，旧错误汇总已改名保留；修正正则后只从原始HTTP200重新解析，没有重新调用模型；
- 执行者只读复核通过；独立审计待进行。

机器入口：planning_001/、analysis_001/、verification_001.json。spot-check见analysis_001/spotcheck_cases.csv。

## 9. 最终结论

**最重要的修正不是“λ无效”，而是明确λ究竟有效在哪一层。**036证明它能改善最终label与医生GT的一致性；038证明这种标签改善不能自动外推为证据和解释同步增强。

其中一部分R存在可以从C48重新建立的可追溯支持，另有大量R在盲审计中仍被认为只部分支持或证据不足。与此同时，当前post-hoc方法普遍存在final label与原reason不同步的问题。

因此论文应把decision boundary correction、evidence sufficiency和explanation faithfulness作为三个独立评价轴。对当前工作而言，前者已有较强患者级证据，后两者应作为已量化的系统边界，而不是被label accuracy掩盖。
