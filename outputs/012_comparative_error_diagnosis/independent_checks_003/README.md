# 012末轮三例定向独立核查

范围：N501、N526、N578三组完整输出（O含reasoning_chain与final）、claim/parent/医生票、两套reference相关正反块；N526的C reference全部14块。另直接核对患者93640对应原note及已存009索引/排名/分数。没有新患者、API或新实验；没有修改主代码、报告或历史材料。本记录不等于全任务审计PASS。

## N501：同样的已做CT信息在两套reference里

GT S，O/V NS，C S。C块10是8月18日“Abdominal CT scan this afternoon after receiving blood”，块11给出CT结果；发布块73、76已经分别保留相同两项信息，块77/78另有“bleed from ?source, f/u CT”。原note473836的[546,603)与[677,710)确认检查/结果连续存在；8月19日note473940/474001也确有f/u CT。

O的完整解释认为未明确是follow-up；V明确看到了f/u CT，仍认为推荐/既往/确切下单状态不清。C把当日腹CT实施推作follow-up且判S。**不能说C新找回了发布reference没有的CT证据。** 同样的关键字面材料已提供，是“已实施、已下单、follow-up”支持关系门槛及其他输入内容/组织差异的实例；没有单变量干预，不能唯一归因Judge或包装。C中的晚期“if becomes unstable CT + contrast”另属条件计划，不能和已做腹CT合并成无条件下单。

## N578：两套reference都明确连着low U/O、Lasix与extubation

GT S，O/C S，V NS。C块3/4的“Renal: low U/O, lasix given to improve diuresis for [possible] extubation”在原note470749 [7772,7843)、470821 [7854,7916)成立。发布块42已有同一句无possible版本，块41有possible版本尾部（其块本身未带low U/O）。因此**不能将C−V改善解释为C独有的low UOP治疗证据**。

V完整输出明确承认41/42将low UOP与Lasix联系起来，但认为首要目的是diuresis/extubation，其他低UOP事件又使用补液或无处理，最后NS。C认为其他Lasix/低UOP事件不否定该次联系而S。此处“单次关系是否成立”和“是否primary/consistent indication”的范围不同可直接从输出观察。原O主要据一般diuresis功能推断low UOP，不应把其S视为对特定事件关系的医学证明。

原claim没有日期，parent处在8月19日前后，而上述直接记录是8月5日；不能据GT一致宣称恢复了parent的同一事件。也不应由执行者自行裁定利尿、低尿量与拔管目标的医学因果。已有原文支持两种目的并列/包含关系的讨论，不是新的临床GT。

## N526：确有晚期记录缺口，但“全程连续”仍不成立为直接观察

GT S，O/V S，C NS。C reference最后日期是8月17日，并有4个简短临床/计费套语尾段：块5“spent: 37 min / Patient is critically ill”，块11–13类似time spent/critically ill。它们**不是严格意义的空字符串**，但没有该claim需要的心率信息；其占位能直接观察，不能未经对照便宣称删去就改善。

发布reference从7月26日延续到9月1日，99块“HR: 110 (92 - 110) bpm / Heart rhythm: ST”，另有8月23日105 (76–107)、8月24日102 (81–103)等区间，也有tachycardia improved。因此可说晚期仍有心动过速记录或反复出现，**不能说全部住院时刻持续心动过速、从无正常心率**。同样，区间有正常值也不自动判定“developed ... throughout his hospital course”这一措辞的正式标签应改；其持续vs多时点发生解释仍需保留。

独立链路定位：9月1日原note476451/476489均有上述HR片段，已进索引，原始HR锚点[927,949)，所在片段[638,1249)。两份副本在保存BM25排名79/80、dense前80未见、融合列表140/142；**均不在C48候选，无该片段保存rerank分数，也未进入最终reference**。故这条晚期锚点的具体损失位置在候选入选前，不是已见reranker后被字符预算丢弃。不能因C有套语占位，就把这条9月1日材料的缺失单独归因最终打包；只改最终打包也无法直接恢复一个根本没进C48的片段。

C完整输出要求continuous/unremitting、present at all times；V解释为反复/从入院至临近出院。因此证据时间覆盖和措辞解释同时变化，未做补回实验，尚不能判断哪一个对标签变化贡献更大。

## 可复查材料

- `raw_checks.json`：三例原note锚点、上下文、索引位置与保存链路；缺失分数保留null。
- `check_raw.py`：直接只读原患者EHR及已有日志的重建脚本，不导入012诊断实现。
- `source_hashes.json`：原EHR、009语料、012材料包与该脚本指纹。
- `view_related.py`：本次用于显示相关完整reference块的阅读辅助；关键词筛选不用于推定证据充分或原EHR不存在。
