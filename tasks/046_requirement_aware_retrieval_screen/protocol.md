# 046：Requirement-Aware Retrieval Screen

## 目标

固定最终DeepSeek Judge，只比较检索/证据选择。允许Qwen参与检索控制，但Qwen输出的摘要、判断或“支持/反驳”结论不能作为患者证据；最终Judge只看原始EHR文本。

第一批只做16条development诊断病例。目的是六路筛选，不估计总体性能；第一批结束后停止，不自动扩大。总收费API保护上限8元。

## 队列

使用044 evaluation development病例，reserved overlap必须为0。

固定组成：
- 6条“retrieval-sensitive”错误：044中base错误、简单rank追加曾改对；仅作为已有selection-headroom锚点，不把rank成绩算作046方法成绩。
- 2条“judge-error control”：045中同一C48换Qwen Judge可改对，检验检索方法是否错误地把Judge问题当检索问题。
- 8条base正确保护对照：S/NS/NA尽量覆盖，human/LLM和患者尽量分散。
- 同一患者最多3条。

队列在任何046新API调用前冻结。
## 共同输入约束

D48 = 031原C48候选池；E0 = 044实际base reference。

所有R1–R6都：
- 保留E0，绝不删除原reference；
- 只追加可追溯原EHR文本；
- 新增正文预算约1500字符；
- 最多3个新增片段；
- 与E0正文精确重复的候选不算新增；
- 最终Judge固定deepseek-v4-flash-0731、原044 scoring prompt/schema/temperature；
- GT不进入任何选择器、planner、reranker或Judge请求。

如果某方法未改变最终reference，直接复用044 base Judge输出，不重复付费。

## 六路

R1 Free semantic add：
Qwen直接阅读claim、E0和D48未入选候选，最多选3个passage ID；允许none。它不做最终三分类。

R2 Requirement-aware add：
Qwen先列出claim需要核验的事实/时间/关系/确定性，再从同一D48未入选候选中选择能补充这些要素的passage；支持、反驳和澄清均可选。
R3 Short-window：
不新调用selector。复用R1选中的同一passage，但程序只追加其中与claim词项最相关的连续原文句窗，保留相邻句和否定/条件；用于隔离“整段噪声”效应。

R4 Relation-set：
Qwen把选择单位改成互补证据集合，优先寻找能共同判断时间变化、计划→执行、前后状态、数值变化或因果/限定关系的2–3段原文；允许none。

R5 Local context recovery：
不新调用selector。复用R1选中passage，并从同note相邻031 paragraph span恢复最多一段局部上下文；仅当相邻span紧接原span且仍在新增预算内时加入。用于隔离片段切割/结构缺失。

R6 Gap expansion + semantic rerank：
Qwen只看claim与E0，提出最多2条中性检索query和缺口描述；程序在目标住院031 eligible corpus上做BM25高召回，取E0外top12；再由第二次Qwen从这些召回结果中选择最多3段原文。最终仍由同一DeepSeek判断。
## 评价

以医生GT判断raw DeepSeek verdict：
- rescue：base错→方法对；
- harm：base对→方法错；
- net = rescue - harm。
同时离线计算固定DeepSeek U0/U2，仅作辅助；不把Qwen分数套λ。

第一批主要看：
1. rescue是否多于harm；
2. 成功是否分布在多个claim/患者；
3. false-S是否明显增加；
4. 新reason是否实际使用新增证据；
5. 方法是否按设计触发，而不是几乎全none；
6. 成本与新增token。

R1/R3/R5的比较用于区分“选什么证据”与“证据粒度/上下文恢复”；R2/R4/R6是主要新检索机制。

第一批晋级不要求显著性。明显0 rescue、或harm≥rescue且没有清楚机制价值的路线停止。最多保留2路进入后续任务/批次。

## 完整性

HTTP200不因结果重跑；无receipt未知请求不自动重发。所有请求body、选择、原文映射和回执写入046目录。执行者核验与独立审计分开。
