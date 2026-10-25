# 039：完整eligible EHR高召回归因审计

## 核心结论

038以后最关键的问题是：U2改对的219条R，到底是“C48已有证据但Judge太严”，还是“完整EHR有证据但C48漏掉”，还是“医生GT与当前可见证据本来就存在scope差异”。

039对全部342条U0非S→U2 S翻转，以及固定hash的120条稳定S/NS/NA对照，重新从036同一目标住院的完整eligible EHR corpus做高召回搜索。搜索完全GT盲；每条claim的扩展query只看claim本身，证据审计只看claim、原C48和新增EHR passage。

**219条R中：A=66、B=55、C=94、D=1、审计无效=3。**也就是说，121/219（55.25%）在自动审计中能建立完整支持，其中约一半是C48已经足够，另一半需要C48外证据；但仍有94条被审计为只有部分支持或存在冲突。这个结果不支持把λ故事简化成单一“Judge边界太严”或单一“检索漏召回”。

## 1. A/B/C/D定义

- **A — C48 sufficient**：036实际C48已经能完整支持claim。
- **B — full-EHR search sufficient, C48 missed**：C48不足，但从完整eligible EHR高召回搜索补充的外部passage后可以建立完整支持。
- **C — partial/conflicting**：存在相关证据，但claim至少一个实质要求只部分支持、被矛盾或未覆盖。
- **D — no clear support / uncertain**：高召回搜索后仍找不到清楚支持，或关系无法可靠确定。
- **U — invalid audit**：HTTP200存在，但结构化审计输出无效；不当成D。

这些类别是自动化机制审计，不是新的医生gold。

## 2. “完整EHR”在本任务里指什么

本任务沿用036事前固定的证据语料边界：已知患者、目标住院日历范围内的EHR note，排除discharge summary，按原paragraph span切片。它覆盖该条件下的全部eligible passages，但不是患者终身所有记录。

每条claim：
1. Qwen只基于claim生成1–4个保守搜索query；
2. 复用036已经取得的BGE embedding，计算该患者完整corpus上的dense排序；
3. 对原claim和扩展query计算完整BM25排序；
4. RRF融合后取原C48之外最高的32个passage；
5. 将原C48与这些新增passage一起交给Qwen做逐要求证据审计。

因此这是“遍历完整corpus后选高排名证据给审计器”，不是把上千段完整EHR一次性塞进LLM。D只能解释为本高召回审计没有找到清楚支持。

## 3. 主结果

| 组别 | N | A C48足够 | B C48外补足 | C 部分/冲突 | D 未找到清楚支持 | U无效 | A+B |
|---|---:|---:|---:|---:|---:|---:|---:|
| **R：GT=S，U2改对** | **219** | **66** | **55** | **94** | **1** | **3** | **121 (55.25%)** |
| H：原U0正确non-S，被U2改错 | 42 | 6 | 6 | 29 | 0 | 1 | 12 (28.57%) |
| W：原U0已错non-S，又被改S | 81 | 11 | 9 | 49 | 9 | 3 | 20 (24.69%) |
| 稳定S对照 | 40 | 26 | 8 | 6 | 0 | 0 | 34 (85.00%) |
| 稳定NS对照 | 40 | 7 | 1 | 32 | 0 | 0 | 8 (20.00%) |
| 稳定NA对照 | 40 | 1 | 2 | 18 | 19 | 0 | 3 (7.50%) |

若只看有效R（216条），A=30.56%，B=25.46%，A+B=56.02%，C+D=43.98%。

稳定S对照的A+B达到85%，明显高于R；稳定NS/NA则明显更低，说明审计器并非完全失去区分力。但H/W仍有32/123（26.02%）被自动审计认为存在完整支持，所以这个自动证据判断不能直接当安全gate或医生裁决。

## 4. 机制解释

### A：确有一批更像决策边界过严

固定抽查里包括：

- atorvastatin从20 mg到80 mg，C48已直接表现住院中加量；
- “placed on vanco”对应C48中明确的vancomycin给药/经验性抗生素方案；
- 初始呼吸衰竭鉴别中有“dCHF vs PNA vs COPD”；
- 一些claim的同义关系或弱措辞在C48中已经很明确，但原Judge要求更显式的原文重述。

这些样本支持原来的“Supported decision boundary过严”假设，但只占R的一部分。

### B：也有相当一批是检索覆盖问题

55条R需要C48外passage才能建立完整支持。例如转ICU事实、repeat angiogram结论、后续ventilator/trach collar状态等，需要额外note才能完成时间或事实关系。

### C：最大单类仍是“部分/冲突”

94条R在扩展搜索后仍被审计为部分支持或有冲突。典型问题包括：

- claim写“closely monitored”，证据只说“continue to trend”；
- “end stage dementia”有dementia和严重功能障碍，但没有end stage这个限定；
- “vital signs normal throughout hospitalization”与部分异常数值冲突；
- “electrolytes were repleted”只有replete计划/医嘱，没有足够执行证据；
- “transferred to rehabilitation program”与实际home/home PT计划冲突。

这类结果最重要，因为它说明医生GT=S和当前“完整命题逐项由输入EHR支持”的标准并不总是等价。

## 5. 对λ故事的修正

039以后，λ最稳妥的结论仍是：

> 固定Supported边界调整提高了最终label与医生claim-level GT的一致性。

但机制不能再写成单因果“大多数R只是Judge太保守”。更符合证据的是：R是混合来源，一部分来自C48已有信息下的保守判定，一部分来自C48检索覆盖不足，还有很大一部分暴露出命题限定词、时间关系或评价scope与当前证据对象之间的差异。

## 6. H/W为什么重要

如果“找到完整支持”能完美区分正确和错误U2翻转，那么H/W应该几乎不会通过证据审计。但实际H为12/42，W为20/81，合计32/123=26.02%。

这可能来自自动审计误判，也可能来自医生GT与当前证据scope本身存在分歧。无论哪种原因，都说明不能把039证据审计直接变成“有证据就放行U2”的安全修复器。

## 7. 执行、费用和有效性

- 462条claim-only query expansion，462/462结构有效；
- 462条扩展EHR证据审计，455条结构有效、7条无效；
- 共924个HTTP200，不重跑HTTP200；
- 实际usage估算17.291343元，低于039保护上限60元；
- query输入只含proposition；
- evidence audit输入只含proposition、原C48和新增EHR passage；
- GT、U0/U2、R/H/W、原reason均不进入API请求；
- 执行者只读核验PASS；独立审计待进行。

## 8. 结论

039没有把038暴露的问题“洗掉”，但把问题拆清楚了。**R中约30%更像C48已有证据下的decision-boundary问题，约25%更像retrieval coverage问题，约43%仍是partial/conflicting evidence。**因此后续不能单独继续调λ，也不能简单加大检索就宣称完整核验能力被修复。

机器结果位于analysis_001目录；核验见verification_001.json。
