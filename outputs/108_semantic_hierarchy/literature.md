# 108：语义层级与专用池化的原文依据及反证

**文献支持把它作为受控适配假设来检验，不支持“拆成两步自然更好”。** 概率分解本身不增加信息；真正可能有增量的是两种关系使用不同表示、监督路径和归纳偏置。107已经提供NS改善、NA受损的直接反证。本文只使用公开论文与本地已完成报告，不读取后续40名确认患者，不把临床原文发往网页或外部API。

按academic-paper-reading技能核对原文的问题、公式、实验和边界，保留11项压缩笔记；不扩展为泛综述。阅读日期：2026-10-28；项目事实基于实际main `fcebf6ffb7f99f4a5b5cb2294d0fb151fc51dc60` 后的本轮工作区。

## 1. 应用问题与研究意义

当前需要同时区分“有无可判定的相关信息”和“有信息时是否一致”。这个解释有临床直觉，但项目GT针对完整参考EHR，不能把“当前窗口没找到信息”直接解释为医生NA，也不能假定S/NS只取决于某一个窗口。目标仍是原GT下的三分类核验，不另造证据充分性gold。

## 2. 相关工作与具体空白

|原论文及一手来源|核对位置与原文实际支持|不能迁移成的结论|
|---|---|---|
|Eibe Frank、Stefan Kramer，*Ensembles of Nested Dichotomies for Multi-Class Problems*，ICML 2004。[作者所在大学原文](https://ml.cms.waikato.ac.nz/publications/2004/frank-kramer-dichotomies.pdf)，[会议目录](https://icml.cc/Conferences/2004/proceedings.html)|§2按内部节点条件概率的路径乘积恢复多类概率；§3平均不同树；§4在21个UCI数据集、C4.5及logistic回归上比较，多数主比较使用20棵树。|主阳性来自具体基学习器和多树ensemble，不是“任意单棵语义树必胜flat”，也没有验证临床NA含义。|
|Maximilian Ilse、Jakub Tomczak、Max Welling，*Attention-based Deep Multiple Instance Learning*，ICML 2018，PMLR80:2127–2136。[PMLR原文](https://proceedings.mlr.press/v80/ilse18a/ilse18a.pdf)|§2.1的bag标签与未知instance标签分开；§2.4 Eq.(7)–(9)是可训练加权池化；§4.1 Table1经典MIL上主要是相当表现，§4.2及§4.3验证MNIST-bags和组织病理图像。|非普遍优于mean/max，也没有证明临床证据窗口满足其经典MIL假设；注意力权重不是instance分类概率。|
|Pepa Atanasova、Jakob Grue Simonsen、Christina Lioma、Isabelle Augenstein，*Fact Checking with Insufficient Evidence*，TACL10:746–763，2022。[ACL原文](https://aclanthology.org/2022.tacl-1.43.pdf)|§4删减证据并人工检查；§5结合删减增强、tri-training及对比学习；§6 Table4报告三数据集结果，§6.3明确主要veracity比较使用gold evidence，§6.4另查错误检索证据。|它支持单独研究信息缺口，不证明两个二分类头或专用池化有效；其oracle证据和增强监督不能视为108已经拥有。|

## 3. 目标、要求与挑战

108的可检验假设应是：在相同输入、患者角色和监督预算下，显式分开两种关系能否减少NS/NA混淆，并改善MCC/false-S且保留合理PA。不能把内部二分类准确率或attention可视化当作外部三分类收益。需要面对的具体反例是：相关但时间、主体或范围不匹配的窗口；只提供部分命题要素的窗口；多个窗口联合才能成立的命题；检索遗漏了完整EHR中的关键信息。

## 4. 问题形式化：分解是恒等式

以下是本项目的数学整理，不是新增算法或论文的额外定理。设三类概率为`(pS,pNS,pNA)`，定义：

```text
q = P(addressed | x) = pS + pNS
r = P(S | addressed, x) = pS / (pS + pNS)
pS = q*r; pNS = q*(1-r); pNA = 1-q
```

除`q=0`时条件概率可任取外，两者一一对应；所有三类分布都能这样表示。因此分解不提供新证据，不保证更好的可分性。若所有输入被压缩成同一个不足的向量，两个头也无法恢复压缩时丢失的信息。有限函数族下，两种参数化的可表达边界和优化行为可以不同，这是待实验的归纳偏置，不是信息增加。

令`a=1[GT不是NA]`，`b=1[GT是S]`，则每条三类NLL恰为`BCE(a,q) + a*BCE(b,r)`。两个loss都按原batch全N平均时才保留这个等价关系。若条件头只在addressed子集中独立取mean后相加，会额外放大其权重`N/N_addressed`；必须按冻结设计交代，不能把收益全归因于语义层级。

## 5. 方法设计：专用池化何时可能有用

**阅读者推断：** 设相同窗口表示为`h_i`，两分支分别学习`z_address=Σα_i h_i`和`z_consistency=Σβ_i h_i`。它可能减少一种共享池化同时承担“覆盖信息”和“支持/矛盾关系”的冲突，前提是原窗口表示已含区分这些关系的信息，训练患者中有足够变化，且两路不会只学习标签频率或长度。仅复制同一个池化向量、改头名，不等于两阶段语义表示。

代价是更多自由参数、不同有效监督量和更高过拟合风险。均匀权重、两路几乎相同的权重，或分类增量只来自bias变化，都不能支持“学到了专用证据选择”的机制解释；权重不同也仍不足以证明机制。不存在从Ilse的二元bag结果直接推出本项目两路池化更优的保证。[Ilse等，§2.4与§4](https://proceedings.mlr.press/v80/ilse18a/ilse18a.pdf)

## 6. 理论边界：不要混入硬门控

联合概率后取三类argmax，与先按0.5路由再二分不同。例如`q=.60,r=.51`时，`(pS,pNS,pNA)=(.306,.294,.400)`；联合argmax为NA，先判addressed再判S却输出S。后者会改变决策规则并产生门控误差，不能作为同一概率模型的无损实现。若冻结方案使用联合argmax，就不能在结果后改为阈值路由挽救成绩。

路径乘概率只需条件概率链式法则；不应进一步宣称两个学习器的估计误差相互独立，或概率必然校准。Frank/Kramer的树结构与ensemble结果也没有提供这种临床保证。[Frank与Kramer，§2–§4](https://ml.cms.waikato.ac.nz/publications/2004/frank-kramer-dichotomies.pdf)

## 7. 实验设置：监督粒度必须守住

一个claim和实际合法窗口集合组成一个bag，保留原claim GT；不得将GT复制到每个窗口。真S的bag可以包含多数无关窗口，真NS的bag也可以包含局部支持信息，而真实NA依赖完整参考范围，不由一段窗口独立认证。训练集派生的addressed二元标签仍是原GT的函数，不能称为新增医生窗口标注。

经典MIL的“至少一个正instance则bag为正”与本任务未必一致：时间关系、合取命题及跨窗口要素可能要求联合判断。可借鉴池化操作，不应声称完整继承该实例标签假设。[Ilse等，§2.1 Eq.(1)–(2)](https://proceedings.mlr.press/v80/ilse18a/ilse18a.pdf) 检索缺口也不能直接改原GT；Atanasova是通过删减和专门诊断研究此问题，不能用它为本项目自动改标背书。[Atanasova等，§4–§6](https://aclanthology.org/2022.tacl-1.43.pdf)

## 8. 本地结果与反证优先级

[107最终报告](../107_support_aux/final_report.md)给出直接警告：自然NS召回23.08%→50.00%，NA75.47%→47.17%；自然15个正确NA损失中14个转NS。压力NS34%→58%，NA82%→60%，11个正确NA损失中10个转NS。这是固定本轮预测中的NS/NA交换，不能仅用“少判S”解释，也不能据此认定108必然解决该问题。

[092报告](../092_task_adapted_verifier/report.md)也限制过度否定：相同聚合头下更新encoder顶部一层曾较Frozen提高MCC0.0722、PA3.60个百分点，但NS仍弱。故CPU冻结特征上的负结果不能普遍否定单层encoder适配；同样，092的阳性不能保证108层级有效。新研究必须承认监督、证据和训练条件的差异，不能直接横向作差。

## 9. 术语与证据账本

|术语|本轮可用含义|不可替代的对象|
|---|---|---|
|addressed派生标签|原三类GT中S/NS合并后的claim级目标|实际窗口的独立gold充分性|
|注意力权重|固定模型中归一化的池化系数|证据正确概率、医生gold evidence或因果解释|
|NS/NA分离|最终三分类中两类可区分性|某一个二分类loss更低|
|CPU真实筛查|已有表示和冻结患者划分上的实际训练/评价|真实encoder反向和最终临床收益|

“注意力不是gold”还可直接由不可辨识性看出：若两个窗口表示相同，在它们之间任意转移权重都不改变池化向量及分类输出，却会改变可视化。即便权重稳定，也需要额外证据才能解释其临床正确性；本轮没有这种窗口GT。[Ilse等原文§2.4仅将权重解释为instance评分的proxy](https://proceedings.mlr.press/v80/ilse18a/ilse18a.pdf)

## 10. 可复核性与当前go/no-go意义

三篇论文没有任何一篇能单独作为部署或扩大108的依据。当前更有价值的反证是：层级概率与flat表达并无信息优势；专用池化实际是否改变表示；条件loss是否无意重加权；NS收益是否再次由正确NA让出；指标改善是否只是S/NS/NA预测倾向迁移。应从真实CPU结果与后续已授权最小GPU检查回答，而非补读更多论文后推测。

如果CPU缓存方案不成立，可在本轮已经授权的**hier_pool最多45分钟/2元probe**边界内检验encoder适配，不能用“CPU负不代表encoder负”无限延长。该反证不擅自改变root冻结的训练/评价门槛。没有完整必要评价就只能称实现/可行性或初步信号；不自动进入确认40人、不调阈值或增加模块。

## 11. 一句话结论

108可辩护的研究价值只能来自同条件实验中更好的NS/NA关系区分与整体得失；二元分解的代数形式、两张attention图和训练loss下降都不能充当这一结论。
