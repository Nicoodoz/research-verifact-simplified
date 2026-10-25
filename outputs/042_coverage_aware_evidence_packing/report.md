# 042：Coverage-aware Evidence Packing

## 核心结论

042按事先冻结的规则完成development screen，并触发停止条件：**SoftNote和CovMMR都没有达到进入confirmation患者验证的门槛，因此不采用任何新selector，也不触碰696条confirmation样本。**

这个结果意味着039定位到的“候选已找到、最终packing丢掉信息”是真实的工程现象，但**不能推出“把同note限制放开”或“增加覆盖/多样性”就会改善最终Judge**。在同一48候选、同一rerank分数、同一8000字符预算下，这两个具体修复都没有形成净下游收益。

042没有改变部署链路，也没有使用reserved40调规则。

## 1. 为什么做042

039在reserved post-hoc机制审计中发现一批R样本需要C48之外的证据才能由Qwen建立完整支持。随后离线追踪显示，很多被引用的外部passage实际上已经进入旧C48候选池，却在最终packing阶段因每note上限、字符预算或去重规则没有进入Judge输入。

因此042没有重新训练retriever，也没有加query planner，而是检验更窄的问题：

> 在完全不增加部署API环节的条件下，仅改变48候选到最终8000字符reference的本地选段规则，能否让原DeepSeek scoring Judge表现更好、同时减少U2标签与原Judge reason/verdict的结构冲突？
## 2. 数据与冻结边界

使用已经消费过的031 development材料，不使用reserved40做方法选择。

- expansion：12名患者、998条claim，其中705条具有031原生48候选和冻结rerank回执；
- confirmation：12名不同患者、1148条claim，其中696条具有相同原生链路；
- 旧历史缓存C48而没有031原生rerank trace的样本，本任务第一版直接排除，不做异质重建。

在连接GT之前，先对全部1401条eligible claim重放旧selector，**1401/1401旧reference与031当时实际送给Judge的reference逐字一致**。随后从705条expansion eligible里按患者/作者分层后固定hash抽240条作为screen。

screen抽样没有按GT或039错误类型选取。连接GT后，其类别构成为S=184、NS=16、NA=40；因此这个screen用于严格配对筛选，不应当成development自然类别比例的新总体估计。

## 3. 三个条件

**Baseline**完全复现原C48：rerank降序贪心、精确重复去除、每note最多2段、最多16段、8000正文字符。

**SoftNote**只删除“每note最多2段”这一硬限制，其余不变。

**CovMMR**保留相同48候选、rerank、16段和8000字符预算，以固定的本地集合效用进行选择：70% rerank-rank relevance、20% claim-token新增覆盖、10% passage novelty，并对同note第三段及以后施加固定软惩罚。最高rerank段固定先入选。所有权重在本轮GT连接前写入protocol，没有看039 reserved结果调参。

部署时三个条件的API链完全相同；差异只发生在本地packing函数。

## 4. Screen结果

| 条件 | reference改变 | Score verdict PA | U0 PA | U2正确/240 | U2 PA | U2 MCC | U2 false-S | U2 vs原verdict冲突 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | — | 76.67% | 77.50% | 205 | 85.42% | 0.6476 | 6 | 24 |
| SoftNote | 144/240 | 76.67% | 78.33% | 203 | 84.58% | 0.6233 | 9 | 23 |
| CovMMR | 174/240 | 75.83% | 77.08% | 205 | 85.42% | 0.6423 | 8 | 28 |

三种条件都基本用满相同预算：平均正文字符Baseline 7893.6、SoftNote 7880.1、CovMMR 7895.4；平均选段数分别12.15、12.25、12.29。因此结果不是简单由“给模型更多文字”造成。

相对Baseline的U2逐条变化：
- SoftNote改变16条U2标签，5条改对、7条改错，净正确−2；
- CovMMR改变19条U2标签，8条改对、8条改错，净正确0。

SoftNote在U0上多2条正确，但经过固定λ=2后反而少2条正确；CovMMR保持U2正确数不变，但false-S和标签—原verdict冲突都增加。

## 5. 预注册停止门槛

screen门槛要求：U2净正确至少+5/240、false-S最多增加3、任一作者净正确不得低于−2，并且U2最终标签与scoring verdict的冲突数不得增加。

SoftNote：
- 净正确 **−2**；
- false-S **+3**；
- human **−4**、llm **+2**；
- mismatch **−1**。
因此因净收益和human子组失败。

CovMMR：
- 净正确 **0**；
- false-S **+2**；
- human **−2**、llm **+2**；
- mismatch **+4**。
因此因净收益和reason/verdict结构冲突失败。

**没有winner。** 按冻结协议，042没有执行696条confirmation，也没有回到039那55条reserved案例挑参数或展示“追回率”。

## 6. 对当前系统意味着什么

042没有证明packing问题不存在。它证明的是一个更窄也更重要的事实：

> **“关键passage在候选池里但没进最终C48”不等价于“把更多这类passage塞回reference就会让Judge变好”。**

最终reference是一个集合。放进新的片段同时会挤出旧片段、改变信息权重、重复结构和模型注意分配；所以单段层面的“看起来有用”不能直接当作集合层面的utility。

这也解释了为什么039的post-hoc定位不能直接变成一个修复器。039告诉我们有retrieval/packing headroom；042进一步显示，当前两个简单集合策略不足以把这种headroom稳定转化成医生GT一致性。

## 7. 对reason—label问题的直接回答

042原本也希望减少U2后处理标签和原scoring Judge解释之间的结构冲突。

Baseline screen中，这种冲突为24/240。SoftNote降到23，只少1条，却同时损失2条U2正确并增加3条false-S；CovMMR升到28。

因此这两个selector**没有解决当前最关键的reason—label对应问题**。不能为了减少一条结构冲突而接受SoftNote，也不能把CovMMR包装成解释改进。

现阶段最诚实的系统状态仍然是：
- 标签层保留已验证的C48 + scoring Judge + 固定U2结果；
- post-hoc标签改变后，旧reason不能自动视为final label解释；
- 041的C48-only evidence-gated explanation abstention仍是防止直接展示矛盾reason的补救层，而不是检索已经修复后的自然解释。

## 8. 执行与核验

- 240条screen，3条件共720个逻辑条件；
- 因相同reference共享请求，实际DeepSeek scoring请求537个；
- 537/537均HTTP200且结构有效，无HTTP200选优重跑；
- usage估算费用 **¥6.667488 / ¥45**；
- API请求只包含proposition与对应reference，不包含GT、039类别、U2旧标签或旧reason；
- 1401条eligible旧C48全部逐字重建通过；
- 执行者核验PASS；
- **独立审计未执行**。

机器结果位于 planning_001、screen_analysis_001 和 verification_001.json。由于预注册停止门槛失败，没有 confirmation_001。

## 9. 限制

本screen是方法筛选而非最终泛化评价：240条由患者/作者平衡hash规则抽取，但GT连接后可见Supported占比较高。所有方法使用同期同一模型和严格配对，不过没有为每个不同reference做重复调用，因此接近零的小差异仍可能包含服务生成波动。

停止结论只约束本任务事前冻结的SoftNote和CovMMR两个具体实现，不证明所有coverage-aware packing都无效，也不证明039定位出的packing损失是伪问题。更准确的结论是：**当前没有足够development证据支持用这两个实现替换冻结C48。**
