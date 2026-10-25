# 066：Oracle Headroom Decomposition

## 目标

固定后处理为当前最稳的 T-S + Frozen PriorG，不再优化后处理。

把剩余性能空间拆成：
1. Evidence / 前处理 headroom；
2. Reasoning / LLM推理 headroom；
3. 两者结合的 headroom。

本任务是development内部上限诊断，不是可部署方法，也不是新测试集。
## 基准

使用053的240条自然development样本。

基准为053冻结的 T-S + PriorG：
- 201/240 correct；
- PA 83.75%；
- MCC 0.5607；
- false-S 8；
- S/NS/NA recall 88.72/50.00/67.74%。

T-S无效3条沿053原固定fallback处理；证据oracle主分析仅针对当前基准错误case，不改已经正确case，因此不会用oracle制造保护样本harm。
## A. Reasoning headroom

不改当前reference。

### A1 Observed multi-reasoner oracle
在共同有效claim上复用已经存在的同reference输出：
- DeepSeek non-thinking raw；
- DeepSeek thinking raw；
- Qwen U0；
- Frozen PriorG最终标签。

若任一现有reasoner/decision答对，则oracle记为可由“当前证据下更好的推理/选择”解决。

这是经验下限，不代表真正完美推理。

### A2 Residual
统计所有现有reasoner都错的claim及GT类别，作为当前证据下最难残余。
## B. Evidence headroom

只针对053 Frozen PriorG当前错误的39条claim，已正确201条保持原预测。

构造三个证据条件，最终全部使用同一个 T-S thinking-high scoring Judge + 同一个 Frozen PriorG：

### E1 C48-Focus
不访问C48以外证据。
Qwen只根据claim生成verification requirements，再从完整031 C48候选中选择3–8个最能完整核验claim的原始passage。

### E2 Full-EHR Focus
在同住院031 eligible EHR中：
- 原claim dense；
- 原claim BM25；
- requirement/query BM25；
- RRF融合；
取C48外top24，与C48共同交给同一composer。
最终仍只给DeepSeek原始EHR passage。

### E3 GT-aware Oracle Evidence
仅用于上限诊断。

selector额外知道医生GT标签，但最终DeepSeek绝不知道GT。

对不同GT：
- GT=S：选择最直接、最完整支持完整claim的原始证据，同时保留会改变限定条件的重要反证；
- GT=NS：选择最直接表明claim被部分支持、矛盾、事件未完成、限定不成立的证据；
- GT=NA：选择最相关的记录以确认主题边界，但不得伪造“缺失即反证”；若eligible EHR无法直接证明NA，可选择最相关上下文或返回无法构造决定性包。

所有选中passage必须来自031 frozen eligible corpus并逐ID回查。
## Evidence Oracle定义

对每个基准错误case：
- baseline PriorG；
- E1 PriorG；
- E2 PriorG；
- E3 PriorG。

若任一证据条件使 T-S+PriorG 与GT一致，则记为evidence-oracle可修复。

系统级Evidence Oracle：
- 原来201个正确case保持原预测；
- 39个错误中能被任一Evidence条件修复的改为GT；
- 其余保持baseline。

同时分别报告E1、E2、E3单独可修复数，避免把oracle组合冒充方法成绩。
## C. Combined headroom

在053共同有效池上做claim级并集：

若：
- 当前reference下Observed reasoning oracle可答对；或
- Evidence Oracle下T-S+PriorG可答对，

则combined oracle记为可修复。

其余仍错。

这是“现有可观测reasoning多样性 + evidence oracle”的经验combined headroom，不等于数学完美系统。
## 评价

报告：
- correct / PA / MCC / false-S；
- S/NS/NA recall；
- 当前39错中各oracle救回多少；
- 修复错误按GT类别；
- Reasoning-only / Evidence-only / Both-overlap / Neither四格；
- E1/E2/E3各自贡献；
- C48外证据是否必要；
- GT-aware selector返回无法构造决定性证据的数量。

重点回答：
1. 前处理剩余headroom有多大？
2. 推理剩余headroom有多大？
3. 两层是否高度重叠？
4. 哪层更值得作为后续主攻方向？
## 完整性与边界

- 053 GT只允许进入E3 oracle selector与最终离线评价，不进入E1/E2或T-S Judge。
- E3不是方法候选，不能报告为可部署性能。
- E1/E2仍是GT-blind前端候选，但本任务只用于headroom诊断，不据此直接定新主方法。
- 所有Judge固定thinking-high scoring；Frozen PriorG参数完全复用053。
- 不使用reserved。
- HTTP200不按答案内容重跑。
- 预算hard cap 20元。
- 不自动commit/push。
