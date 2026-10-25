# 046：Requirement-Aware Retrieval Screen

## 核心结论

046完成第一批16条development诊断病例的六路检索/证据呈现筛选。最终Judge固定DeepSeek，GT未进入任何新API请求。

| 路线 | 正确/16 | rescue | harm | 净变化 | 改reference |
|---|---:|---:|---:|---:|---:|
| Base E0 | 8 | — | — | — | 0 |
| R1 自由语义补证 | 9 | 2 | 1 | +1 | 12 |
| R2 requirement-aware补证 | 9 | 2 | 1 | +1 | 13 |
| R3 R1证据短原文窗 | 10 | 2 | 0 | +2 | 12 |
| R4 关系集合选证 | 9 | 1 | 0 | +1 | 12 |
| R5 R1＋相邻上下文 | 9 | 2 | 1 | +1 | 12 |
| R6 缺口扩检＋语义重排 | 8 | 1 | 1 | 0 | 3 |

4条固定原DeepSeek同输入repeat全部保持原标签。

R3/R1两条主要rescue经过原文回查后，关键事实本来已经存在于E0。因此本轮不能把R3的2 rescue写成“找回两条缺失证据”。更准确的结论是：缩短并聚焦少量相关原文，可能改变Judge对已经可见信息的使用，同时减少无关上下文造成的误伤。

## 1. 队列与共同约束

16条全部来自已经使用过的development患者，共8名患者，reserved overlap=0。

组成：
- 6条retrieval-sensitive错误：044里base判错、简单rank追加曾改对；
- 2条judge-error control：045中同一C48直接换Qwen Judge能改对；
- 8条base正确保护样本。

因此base恰好8/16正确是设计结果，不是自然准确率。

“retrieval-sensitive”只是历史下游反应锚点，不等于已经有人类标注证明这些案例一定缺失证据。046后面的机制回查正说明这个区别非常重要。

共同规则：
- E0全部保留，不删除原证据；
- 新增最多约1500字符、最多3段；
- 最终Judge固定DeepSeek-V4-Flash-0731；
- 不把Qwen生成的摘要或判断作为患者证据；
- 没改变reference时直接复用044 base输出。

## 2. 六路结果

R1自由语义补证：Qwen直接阅读claim、E0以及D48中未入选的原文候选，从中选最多3段。12/16改变reference，2 rescue / 1 harm。

R2 requirement-aware补证：Qwen先拆出claim实际要求核验的事实、时间、事件状态、限定和关系，再从同一D48候选选择补充证据。13/16改变reference，2 rescue / 1 harm。比R1更积极，但没有获得更高净收益。

R3短原文窗：不重新选证，复用R1选出的同一候选passage，只追加其中与claim最相关的连续原文句窗，减少整段噪声。12/16改变reference，2 rescue / 0 harm，为本批raw verdict数值最好的一路。

R4关系集合：Qwen把选择单位改为2–3段互补集合，强调前后状态、计划到执行、时间变化、数值变化和关系。12/16改变reference，1 rescue / 0 harm。

R5局部上下文恢复：复用R1选中passage，并尝试加入同note紧邻paragraph span。12/16改变reference，2 rescue / 1 harm；R5与R1在16条上的最终标签完全相同，因此本批没有看到相邻span恢复带来的独立标签价值。

R6缺口扩检＋语义重排：Qwen根据claim和E0生成最多2条缺口查询；在目标住院031 eligible corpus做BM25高召回，取E0外top12，再由第二次Qwen选择最多3段，最后交同一个DeepSeek。只有5/16生成扩检query，3/16真正追加证据，结果1 rescue / 1 harm，净0。

## 3. R3为什么避免了R1的harm

保护样本：“The patient completed their last chemotherapy course in September.”

医生GT=Not Addressed，base也正确判NA。

R1加入的完整passage包含大量肿瘤治疗背景，以及“本次住院未积极接受治疗”等信息。DeepSeek随后从NA变为NS，造成harm；但这些材料并没有回答“最后一次疗程是否在September完成”。

R3使用同一批R1选证，但短窗只保留局部原文，没有把整段治疗史和“当前未治疗”一起带进来；最终仍保持正确NA。

R1与R3在16条中只有这1条标签不同，而差异正好是这个harm被避免。

这个案例支持：在已有较大E0的前提下，增量证据的信息密度可能比整段上下文更重要。但不能从单例推导普遍最优窗口长度。

## 4. 两个R3 rescue不能写成“找回缺失事实”

R3救回的两条与R1相同。

第一条：Patient was admitted to the NSURG service.

base=NS，R3=S，GT=S。回查E0发现，原reference本来就已经包含NSURG以及neurosurgery (primary)等信息。R1/R3新增的主要片段反复写“Admitted to SICU following EVD placement”。

因此标签改S不能简单归因为“新找回NSURG事实”。更可能是追加相关病程片段后，Judge重新权衡了原本已经存在的neurosurgery-primary信息。

第二条：The moderate pulmonary artery systolic hypertension suggests a primary pulmonary process.

base=NS，R3=S，GT=S。原E0在追加前已经同时包含pulmonary artery systolic和primary pulmonary process。R1选择同一Echo note的其他片段，R3保留短窗，最终DeepSeek改S。

因此这同样更像证据重复强调或注意力重分配，不是candidate recall修复。

如果只看2 rescue / 0 harm，会误把R3写成检索召回成功。更准确的定位是：R3是当前最有信号的evidence focusing / presentation方案，而不是已经验证的missing-evidence retrieval方案。

## 5. R2与R6的独有rescue也要谨慎

R2独有的一条是“The patient was eventually cleared for discharge.”，GT=Not Addressed。base从NS改成R2的NA，形成分类rescue。

但新增passage正文只有“Recent chest tube removal”等信息，并没有直接说明是否clear for discharge。该改判与GT一致，但新增证据并非明确解决claim核心关系，因此不能当作高质量检索成功例。

R6独有的一条是“A CT of the head was performed after the procedure to evaluate drain placement.”，GT=Not Supported。base=NA，R6=NS。

新增passage包含EVD管理和“Imaging: CT, CT-A, MRI [5-26] stable”，属于相关时间/影像上下文，但没有直接写“用于评估drain placement”。它可能帮助Judge理解时间关系，也可能只是改变了缺失/反证边界。因此R6这一例也不是“找到直接矛盾证据”的干净例子。

R4没有harm，但唯一rescue就是上述肺动脉高压案例，没有产生独有成功。

## 6. 其他信号、成本与完整性

R1/R2/R5的同一个harm都是“last chemotherapy course in September”保护样本；R6也伤了这条。说明这个case对“加入相关但不能回答核心限定的信息”非常敏感。

最终reason/check对新增证据的显式引用数量：
- R1：6/16；
- R2：7/16；
- R3：6/16；
- R4：6/16；
- R5：6/16；
- R6：3/16。

“被引用”只表示DeepSeek使用了新增编号，不证明该证据足以支持GT。

固定DeepSeek-U2在这个诊断小组上没有因这些检索方法变得更好：base U2为13/16，R3仍13/16，其余多为11–12/16，R6为13/16。因此主机制终点仍应看固定Judge自己的raw verdict和reason。

API：
- stage1：68次；
- R6语义rerank：5次；
- 去重后的最终DeepSeek：45次；
- 合计118次HTTP200；
- Qwen 69次，DeepSeek 49次；
- parser 117 valid，1个R1 selector返回截断JSON，保留invalid并按none处理，不重跑；
- usage估算总费用：¥2.244342 / ¥8。

96个逻辑条件中64个改变reference；完整DeepSeek body去重后只有45个新终判调用。执行者离线核验PASS，独立审计未执行。

## 7. 第一批研究决策

按“最多保留2路”的原则，本批不建议把R1/R2/R4/R5/R6直接扩大。

- R1：不单独晋级。有signal，但存在整段噪声harm；R3在同一选择基础上更安全。
- R2：不单独晋级。更积极但没有优于R1，独有rescue机制不够干净。
- R4：暂不晋级。1/0安全，但没有独有rescue，未证明关系集合带来新增价值。
- R5：停止。与R1标签完全一致，没有独立收益。
- R6：停止当前版本。1/1，语义rerank仍未解决扩检收益。
- R3：唯一保留候选，但应定位为evidence focusing，而不是retrieval recall。

更重要的是，046暴露了下一批的样本选择问题：“历史上加点证据能改对”不足以定义真正的retrieval miss。

本批6条所谓retrieval-sensitive病例中，至少两个主要rescue的关键事实原本就在E0。后续如果继续研究“找回缺失证据”，应先建立development上的true missing-evidence diagnostic set：要求能追溯到“目标信息不在E0，但存在于D48或eligible EHR”的具体原文，而不是只根据Judge标签变化选样。

这一步可以利用既有development trace和原文回查建立机制集，不需要医生重新大规模标注；但必须明确它不是新的医学gold benchmark。

主要入口：
- analysis_summary.json
- route_summary.csv
- transitions.csv
- factor_R1_R3_R5.csv
- verification_001.json
