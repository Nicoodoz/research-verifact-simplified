请在当前项目 `https://github.com/Nicoodoz/research-verifact` 中完成下一阶段任务：

# 092：任务适配的临床证据核验模型

本任务目标不是继续修改示例、prompt或PriorG，而是验证一个此前没有被充分完成的方向：

> **固定现有C48证据输入，直接利用VeriFact-BHC医生三分类标签训练能够读取claim与EHR原文的文本核验模型，并判断任务微调后的文本表示能否带来独立、可用于最终系统的性能增量。**

最终服务于毕业论文目标：在尽可能完整的数据口径上，与原VeriFact系统形成有竞争力的结果，优先争取PA、MCC整体更高，同时关注Macro-F1、NS/NA少数类识别和false-S。无需要求所有指标同时最优，但最终方案应有清楚的性能特点和可解释的技术贡献。

---

## 一、先复核历史，避免重复已有失败路线

开始前重点阅读：

- `AGENTS.md`
- `docs/PROJECT_STATUS.md`
- `docs/RESEARCH_EXECUTION.md`
- 091完整报告和论文稿
- 032 evidence relation correction
- 037 NS/NA decision
- 042、044、046、049
- 066、068、069
- 078、083、084、090

尤其确认：

1. 032已经使用DeBERTa对claim与C48原文做过片段/同note多粒度编码、注意力聚合和三分类残差学习；
2. 但032的DeBERTa文本编码器是冻结的，隐藏表示经过固定投影，最终模型主要学习小型聚合/残差头，并依赖旧LLM score；
3. 学习式证据选择、coverage packing、requirement/quote/relation结构、utility selector、GT教师选包等方向都已有大量实验，没有形成稳定收益；
4. 因此092不要重新把“多粒度选证＋关系图＋Gate＋示例＋新校准”全部堆回来。

本任务真正新增的核心变量是：

> **让文本编码器本身针对医生S/NS/NA标签进行任务学习，并让模型能够在不依赖旧LLM三类分数的情况下独立完成核验。**

如果检查后发现仓库实际上已有等价的encoder fine-tuning实验，则停止重复实现，先明确差异，再选择真正未测试的最小扩展。

---

## 二、数据策略

主任务使用**atomic claims**，尽可能覆盖当前可合法构造C48输入的全部患者和命题。

不要再为了保留所谓“完全未见测试集”而限制研发材料。可以充分使用项目已有标签进行训练、调参和模型选择。

但最终需要得到逐条可比较的全量预测，因此优先采用：

> **patient-grouped out-of-fold / cross-validation**

例如5折患者分组CV，保证每条最终预测来自没有用该患者训练的模型。这样全部患者都能参与训练，同时最终可以得到整个数据集的一套OOF预测，用于与原VeriFact同ID比较。

具体折数、分层方式和训练/验证划分可根据样本量和GPU资源合理决定，但患者不能在同一折的训练与预测两侧同时出现。

尽量复用已有C48、候选、reference和原作者预测缓存；缺失C48时优先用现有本地管线补齐。不要为了本任务重新开发retriever。

---

## 三、092的核心模型

### A. 公平的Frozen Encoder基线

先建立一个比032更直接的冻结文本模型基线：

- 输入：claim + C48原文；
- 对长证据按现有可靠实现切为多个claim-evidence窗口；
- 保留完整encoder hidden representation，不再使用032的固定32维随机投影作为唯一表示；
- encoder全部冻结；
- 使用一个简单可训练的evidence aggregation + 三分类head直接预测S/NS/NA；
- **不输入旧DeepSeek/Qwen label_scores，不加PriorG。**

这个模型用于回答：

> 仅靠固定预训练文本表示，能够达到什么水平？

### B. Fine-tuned Encoder主模型

保持A的输入、窗口和聚合结构尽量一致，只改变encoder是否参与训练。

允许根据显存选择：

- full fine-tuning；
- 解冻顶部若干层；
- LoRA / adapter等参数高效微调。

核心要求是：

> encoder的文本表示必须真正受到医生三分类监督更新。

优先复用032已经下载和跑通的DeBERTa-v3 NLI模型及环境；如果存在明显更合适、容易获得的临床/医学encoder，可以最多增加一个模型作为辅助对照，但不要展开大规模backbone搜索。

### C. 分类目标

首版以普通S/NS/NA三分类为主。

考虑类别不平衡时，可以有限比较：

- 普通cross-entropy；
- 一种合理的class-balanced / weighted objective。

不要一开始同时加入复杂层次Gate、多个辅助任务、reason监督和手工规则。

如果普通三分类已经能回答问题，就不要为了让模型“看起来更高级”额外增加结构。

---

## 四、允许有限调参，但不要无限版本搜索

这次不采用过去那种一个小screen失败就马上永久放弃整个方向的方式，但也不能无限试版本。

可以做一个规模受控的搜索，例如围绕：

- encoder冻结 / 部分解冻 / PEFT；
- 1–2种aggregation方式；
- 普通CE / 1种类别平衡loss；
- learning rate、epoch、dropout等必要训练参数。

总的模型族保持有限。

调参目标以最终分类性能为主，优先级：

1. MCC和PA；
2. Macro-F1；
3. NS/NA recall与F1；
4. false-S；
5. 稳定性和成本。

不要设置“false-S只要增加1条就自动失败”之类过严门槛。

如果一个模型明显提高PA/MCC，只增加很少false-S，应保留为候选；反过来，如果略损失PA但显著提高MCC、少数类和false-S，也可作为风险型候选。

最终选择应看综合Pareto，而不是单一指标。

---

## 五、必须包含的强基线

最终主要比较至少包括：

1. **原VeriFact作者系统**：同一命题ID上的发布预测；
2. **当前系统B**：C48 + T-S + Frozen PriorG；
3. **完整F4 + Frozen PriorG**：在有可比预测的范围中保留，不因“只是4个示例”而删除；
4. **092 Frozen Encoder**；
5. **092 Fine-tuned Encoder**。

如果B/F4没有覆盖最终全量ID，不必一开始花大量API强行补齐。

优先：

- 用已有共同范围做直接比较；
- 新文本模型与原VeriFact做全量OOF比较；
- 再根据结果决定是否值得补跑B/F4的更大范围。

注意F4只是性能基线，不作为092主要创新。

---

## 六、如果微调模型确实有独立信息，可额外测试一次融合

只有在Fine-tuned Encoder满足以下任一条件后，才允许做一个简单融合实验：

- 单独PA/MCC接近或超过当前强基线；
- 少数类或false-S明显更好；
- 与B/F4存在明显互补错误。

届时可以测试：

> **Generative Judge + Discriminative Verifier**

例如将Fine-tuned Encoder logits与当前T-S输出做一次简单、固定的late fusion / residual fusion。

这个融合可以使用医生标签训练，但不要重新演变成029—033那种大量Gate、threshold、患者subset搜索。

目标是判断训练后的文本模型能否为现有LLM系统提供真正新增的信息。

若融合成功，论文最终系统可以写成：

> C48 evidence construction + generative reasoning judge + task-adapted discriminative verifier

这样主要技术贡献来自文本核验模型，而不是PriorG本身。

如果独立模型没有可用信号，则不做融合救结果。

---

## 七、需要重点回答的研究问题

092最终报告必须明确回答：

### RQ1
对相同C48证据，**真正微调文本encoder**相对冻结encoder是否提高：

- PA
- MCC
- Macro-F1
- S/NS/NA recall与F1
- false-S

这是本任务最核心的因果比较。

### RQ2
微调的收益主要来自什么类别？

重点看：

- 当前系统误拒的真S能否恢复；
- NS与NA是否更容易区分；
- 是否减少或增加false-S；
- human与LLM文本是否表现不同。

### RQ3
Fine-tuned Encoder相对原VeriFact和当前B/F4处于什么位置？

不要求所有指标第一。

寻找可以形成论文特点的结果，例如：

- PA、MCC均高于原VeriFact；
- PA接近但MCC/Macro-F1明显更高；
- 少数类识别更强；
- false-S显著更低；
- 输入或部署成本更低。

### RQ4
训练后的文本模型是否提供现有LLM score之外的新信息？

如果进行了融合，报告：

- 独立修对；
- 独立误伤；
- 哪些病例只有文本模型正确；
- 是否真正改善最终系统，而不是重新调一个类别偏置。

---

## 八、前处理暂时保持固定

092不要新开发：

- coverage-aware packer；
- requirement-aware retriever；
- utility selector；
- dynamic demonstration；
- relation Gate；
- rationale classifier；
- 新PriorG；
- P90/P91等新压缩版本。

这些已有大量历史实验。

当前C48可以作为论文已有前处理模块，其现有优势主要定位为：

> 在明显减少输入长度和Judge成本的情况下维持较好的核验性能。

092的主要新增贡献集中于**模型核验阶段**。

如果092完成后发现新模型的主要错误高度集中在一个清楚的证据问题，例如时间状态、跨片段事件或否定范围，再把该问题留给093做针对性的前处理创新。

不要在092内同时解决所有问题。

---

## 九、最终全量评价

当模型结构确定后，尽量生成覆盖全部可用atomic claims的patient-grouped OOF预测。

统一报告：

- correct / N
- PA
- MCC
- Gwet AC1
- Macro-F1
- 每类precision / recall / F1
- confusion matrix
- false-S count
- false-S / true non-S
- false discovery among predicted S
- human / LLM分层
- 每患者表现分布

如果模型提供概率，再补：

- NLL
- Brier
- ECE

但概率指标不是本任务主目标。

与原VeriFact必须按相同ID重新计算，不直接拿论文摘要数字比较。

最终结果重点寻找：

> “总体分类表现 + 少数类能力 + false-support风险”形成的综合优势。

---

## 十、工程与资源

优先本地GPU训练，充分复用032环境、模型缓存和数据构造代码。

允许重构032相关代码，但不要修改历史任务输出。

大型checkpoint、缓存和临床原文继续放在已有ignored目录，不提交Git；Git中保存：

- 训练代码；
- 配置；
- 模型结构；
- 数据ID与划分；
- 指标；
- 模型/权重hash；
- 必要轻量adapter（如果仓库策略允许）。

本任务原则上不需要大量收费Judge API。

若确实需要补C48/BGE或少量同期LLM对照，先估算费用；没有额外用户授权时，新增收费API总额控制在约30元以内。不要为了用完预算调用API。

---

## 十一、停止与继续规则

### 若Fine-tuned Encoder明显优于Frozen Encoder

继续完成：

- 全量OOF；
- 与原VeriFact/B/F4比较；
- 必要的一个简单融合；
- 主要消融；
- 论文方法与结果更新。

### 若Fine-tuned Encoder只比Frozen略好，但与现有系统有明显互补

允许完成一次简单融合，判断是否能提升最终系统。

### 若Fine-tuned Encoder：

- 与Frozen几乎无差别；
- 或PA/MCC明显低于现有强基线；
- 或仅靠极大增加false-S获得PA；
- 且不存在明显互补价值；

则停止该路线，不继续堆多粒度selector、relation head或大规模backbone搜索。

阴性结果同样完整报告，下一步重新考虑其他创新方向。

---

## 十二、交付

创建`092_*`正式任务和输出目录。

至少交付：

1. `report.md`：中文主报告；
2. 完整模型架构和训练说明；
3. Frozen vs Fine-tuned核心消融；
4. 全量/最大覆盖OOF预测；
5. 与原VeriFact、B、F4的统一比较表；
6. confusion matrix、类别指标和false-S分析；
7. 代表性rescue/harm病例分析；
8. 训练成本、推理成本和模型大小；
9. 复现脚本、配置、模型hash；
10. 若结果足够强，更新091中文论文稿的Methods、Results、Abstract和Conclusion。

论文表述优先围绕真正做出的模型工作：

> 使用患者EHR证据直接监督任务适配的文本核验模型，并研究其与生成式LLM Judge的互补性。

不要把贡献写成“重新调PriorG”或“多加几个example”。

完成后自行检查、commit并push，停止，不自动启动093。
