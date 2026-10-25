# 012 定向独立核查记录

本记录由与主执行线程分开的核查线程形成，不是整个012的独立审计结论，不宣布审计PASS，也不提供新的医学GT。先自行读取既有材料，再与主执行线程交换发现。已核对7例的原发布完整reasoning_chain及final、010 V/C完整输出、claim/parent和原医生评论；证据阅读范围是两套reference中与诊断主题对应的完整块，不声称7例所有reference块均由本线程全文深读。N086/N395另直接查原始EHR与009索引/排名/分数/丢弃记录。未调用API、未使用新患者。

## 独立机器核查

`check_alignment.py`没有导入012实现，直接按010冻结cohort连接release原表、010 canonical assignments/jobs、normalized输出及HTTP200原回执，逐项对比012材料。650命题一对一、1,300完整请求/收到的完整输出对应成立；195错误并集与455三组共同正确、分作者三种比较方向计数均重建一致。原发布650条reasoning_final_answer中可解码的最终verdict与发布列均一致。本范围未发现连接、输出处理或计数差异。

完整计数见`machine_result.json`，650个最终JSON位置见`original_final_checks.jsonl`，读取材料指纹见`source_hashes.json`。机器标签组合不能产生因果归因；原系统没有完整请求/上游候选日志，不能将010 body或C48轨迹当成原系统轨迹。

## N086：否定词真实切断，同时仍存在替代支持材料

claim是“admitted with symptoms of nausea”，GT S；O/V为NS，C为S。C的块1、8保留HPI中“increased SOB, N/V, and fatigue”。发布块15同样有该HPI，块5则是“s/p transaminitis: No nausea, no abdominal pain.”。O完整输出承认N/V，却以“No nausea”压过入院HPI；V也如此。

原note375697的[12108,12117)是“No nausea”。C块11从12111开始，实际成了“nausea, no abdominal pain”；前一块停在12110且以“No”结尾。该后块BM25第4、dense第13、C候选第8、rerank第1，进入最终reference；前块dense第52，未进入C48。C完整输出明确说later physician note documents nausea，并称无反证，与原文否定不符。切分破损位置可以直接确认，C得分改善不能全部当作语义改善，也不能证明标签是由破损造成，因为独立HPI支持仍在。未做补回否定词的干预。

另需保留时间元数据边界：该note CHARTDATE为2127-05-21，CHARTTIME是2127-05-20 15:41，description为Admission Note。因此“later”是C输出中的表述，不能由显示日期独立证明它是后续临床事件。

## N095：原医生明确留下NS/NA解释边界

claim为potassium supplements，GT NS；O/V NA，C NS。C块5有“Rec\nd 20meq kcl for low K+, also rec\nd lasix 100mg iv”。O/V输入相应主题块只给K值，未保留该KCl行动句；C确实获得了更直接的相关材料，但输出将其解释为recommendation而非administration。

不能据执行者对Rec'd的释义推翻原医生：原三票NS/NA/S，第二轮NS/S，adjudicated_comment为“Open to interpretation of what low K+ means; Patient has K 3.8. Either Not Supported or Not Addressed.”，comment4明确“Recommendation to administer KCL, but not performed + no instance of hypokalemia”。C与最终GT一致不等于解释获得了新的医学证明；O/V与最终GT不一致也不能描述为确定的临床错误。保留标签、记录医生评论和缩写/行动状态不确定性。

## N139：证据已经包含恢复过程，当前输出扩大稳定时间范围

GT S，O S，V/C NS。两套reference都有早期低压和后续“BP has returned to baseline”；C块10还有“VSS”。O将改善/回到基线视为支持。C完整输出明确要求“stability throughout the admission”，claim未写throughout；V强调所有阶段的低压波动。parent处于继续改善、待转出/出院的语境，但它没有进入Judge，不能静默改窄正式核验目标。

这是同套发布reference下原/现后端解释范围改变的直接实例，适合检验无明确全程限定时如何处理早期异常与后续恢复。不是已证明单一prompt原因，也不能要求任何正常晚期值一概支持“stable”。

## N182：局部关系已保留，不能全归为结构缺失

GT S，三组均NS。C块9完整连续保留“Ineffective Coping / Anxious MI diagnosis / MEDICATION LIST REVIEWED WITH PT / ... Emotional support, CONTINUE TEACHING”。发布块89/90、96/97也保留相关条目但跨块；V完整输出承认teaching yet要求specific education solely for anxiety。原输出称没有education，C也在承认medication review后否定针对焦虑的教育。

观察支持“已有相关行动和章节关系，仍存在关系/支持充分性解释分歧”；C9本身已有局部结构，是对“只要恢复标题/邻接即可解决”的反例。仍不能由CONTINUE TEACHING直接裁定已完成某项特定焦虑教育，计划/实际行动及教育范围需保留不确定；不能根据某个输出没有提词证明内部未考虑。

## N188：最终GT与来源事件解释不能混为一项标准

GT S，O S，V/C NA。两套reference给外院1月30日CTA无aortic dissection及之后cath/stent叙述；O完整输出明确以CTA作为支持，虽然承认没有之后final angiography记录。V/C则区分术前CTA与final angiography。parent明确处于LCx支架后的“Final angiography”语境。

原医生第二轮S/S，comment4直接引用“CT r/o dissection/PE”与“CTA was negative for PE or dissection”。因此可以指出parent事件与引用证据并不明确相同，但不能把O当作已经证实的临床错配、把V/C当作已证实医学更正确。这里适合展示原标签一致性与来源语境理解两种目标的边界。关键词/相关块检查未找到完整final cath报告不等于原EHR不存在，原语料缺失位置仍未知。

## N388：判断“the focus”的范围改变，不能无限放松支持标准

GT NS，O S，V/C NS。两套reference都包含肺部监测、肺部处理，同时也记录出血/疼痛/心律等优先事项。O据存在肺部管理就判S；V/C认为claim把“one of several concurrent focuses”说成“the focus”，当前判断更符合最终GT。

这与N139共同提示范围解释会双向影响得分。不能将下一步设计成“一律去掉严格限定”或“只要有一条支持就S”；关系是否主导/唯一和普通事件确曾发生需要分开。没有医生新增裁决证明the focus必然等于exclusive focus；病例只表明当前文本解释与GT的一致方向。

## N395：关键consult候选已被找到，最终打包未保留

GT S，O/V S，C NA。发布块11为“F/u Ortho re: fx”，块32明确“Consults: General surgery, Neuro surgery, Ortho, Plastics”，还可看到块95“per ortho”。C完整reference主要是orthopedic injuries与APS/pain service，没有这些同样明确的骨科consult条目。V援引11/32；C区分伤情与实际骨科会诊。O解释本身较笼统，但不能忽略它实际reference已有明确会诊材料。

直接原文与索引核查：原note564621、564631的[4589,4646)均是上述Consults语句，其所在片段分别dense17/18、BM25 25/24、C候选23/25、rerank22/21，真实分数0.0631312/0.0631686。两者最后均被记录为character_cap舍弃。因此该显式材料的损失确认发生在排序后的预算选择，不能写成未召回、融合挤出或reranker未见。另3份原note中的F/u Ortho替代线索已在索引，但不在保存前80排名或C48候选；不能用它们缺席来覆盖已经有consult候选的事实。未做补回干预，不能断言补回就一定提高最终预测。

## 对主结论的限缩建议

可优先提出两个可检验问题：一是claim未要求全程/唯一时，当前判断后端是否自行扩大时间/支持范围（同时保留N388类过宽S反例）；二是明确关系证据已到候选后怎样避免被大量同主题片段挤出（N395）。这不是证明两个新方案有效。N086提示基础否定/边界完整性仍应作为平台质量控制；不能因011组合未获净收益而接受真实反义切分，也不应直接用它证明包装的论文贡献。所有这些方向仍须固定条件与同期重复验证。
