# 044：Incremental Evidence Recovery

## 目标

043表明：对一批post-hoc困难案例，保留原C48并追加真正有用的证据，可以让原DeepSeek Judge自己改判并同步生成新reason。044把这个oracle机制转成development上的可部署方法实验。

核心问题：

> 在不知道GT、没有039事后oracle、且不增加线上Judge调用次数的情况下，能否从原48候选中自动选择少量增量证据，保留原C48并追加后，让Judge的标签与reason一起改善？

部署链保持不变：
EHR → 原BM25/dense → 原48候选 → 原BGE rerank → 原C48 packing → 本地增量选择器 → 一次DeepSeek scoring Judge → 固定U2。

选择器不调用LLM、不读取GT、不读取Judge第一次回答；部署时仍只有一次Judge调用。允许“不追加”。

## 数据边界

只使用031已经消费过的development材料开发044；reserved40和043的55条案例不进入训练、阈值或winner选择。

限定为031中具有原生48候选及rerank回执的样本：
- expansion eligible 705条，来自10名有有效trace的患者；
- confirmation eligible 696条，来自另一组患者。

Expansion患者按 sha256("044/split/v1:"+sid) 固定排序：
前7名用于utility训练池，后3名用于内部screen；患者完全隔离。
训练池中再按患者/作者均衡固定hash抽240条，API请求冻结后才连接GT。
Screen使用后3名患者全部192条。
Confirmation仅在screen门槛通过后启用，且不用于重新调模型。
## 固定增量候选

所有方法都先保留原C48，绝不删除原reference内容。只允许从原C48的48候选中、但未进入最终reference的passage追加，额外预算最多1500正文字符、最多3段。

与原C48已有相同正文的候选一律不作为新增信息追加，避免利用重复强调制造改判。

每条claim预先构造三个append option：

1. **simple**：按原BGE rerank从高到低追加。
2. **near_miss**：优先追加原packing因 max_per_note 或 character_cap 被跳过的高rerank passage；不足时按rerank补齐。
3. **novel**：本地固定效用排序，兼顾rerank、claim词汇覆盖与相对原C48文本新颖性；不使用GT。

三者使用相同1500字符/3段上限。

## Utility监督

训练阶段对240条固定训练claim分别运行：
- A：原C48；
- simple；
- near_miss；
- novel。

每个append option的监督目标为相对A的医生GT正确性变化：
+1 = A错、append后对；
0 = 正确性不变；
-1 = A对、append后错。

该监督仅用于development训练。部署时模型看不到GT或Judge输出。

轻量模型固定为 StandardScaler + multinomial LogisticRegression（L2，C=1，class_weight=balanced，random_state=0）。
输入仅允许推理前可见特征：append类型、段数/字符数、原rerank相对名次、claim-token重叠、相对原C48的新颖度、增量token覆盖、是否来自新note/date/category、数字匹配及claim时间词标记。

对每个append option计算：

utility = P(+1) - P(-1)。

若三个option的最大utility <= 0，则选择“不追加”；否则选择最高utility，固定tie-break为 simple > near_miss > novel。没有额外阈值搜索。

## Screen门槛

在192条患者隔离screen上同期比较：
- A原C48；
- SimpleAppend；
- LearnedUtility（可不追加）。

LearnedUtility才是允许进入confirmation的主候选。门槛全部满足才继续：
- DeepSeek原始score verdict净正确数 ≥ +4；
- U2净正确数 ≥ -2；
- score-verdict false-S增加 ≤ 3；
- human和llm任一作者净正确数不得 < -2；
- U2 final-vs-score-verdict结构冲突数不得增加；
- LearnedUtility选择追加的比例不得 > 70%。

SimpleAppend只作为“多给材料是否已经足够”的容量对照，不作为044最终winner。

## Confirmation

若LearnedUtility过screen门槛，模型与所有规则冻结后在696条confirmation eligible上评价。

对选择“不追加”的claim，LearnedUtility与baseline输入完全相同，配对差值定义为0，不产生额外API调用。
对选择追加的claim，只调用同期A与LearnedUtility两次DeepSeek，得到严格配对差值。
另固定hash抽最多120条“不追加”claim做同期baseline重复稳定性诊断，但不参与方法差值。
主终点：
- score-verdict净正确、false-S、三类召回与患者级方向；
- U2净正确及 U2-vs-score-verdict mismatch；
- 对输入改变claim的 reason 语义一致性、grounding 与完整claim coverage；
- 额外输入token/字符与实际费用。

对于confirmation中输入改变的claim，另用GT盲Qwen审计DeepSeek的verdict/reason/checks，报告：
- label-reason semantic alignment；
- grounding；
- 对完整claim的coverage；
- 新增证据是否material。

联合质量指标必须明确分母：GT标签判对且reason被自动审计为 consistent + grounded + complete 的比例。它不是医生解释gold。

如果screen失败，044停止，不执行confirmation，也不事后调权重、预算或阈值挽救。

## 解释边界与成本

044是development上的方法开发/患者隔离内部确认，不是新的外部验证。043仅提供研究动机，不提供任何训练样本。

额外1500字符意味着Judge输入token可能增加，但不增加部署时API调用环节或Judge调用次数。

单任务收费API保护上限80元。成功HTTP200不因结果重跑；格式无效保留。执行者自检与独立审计分开。
