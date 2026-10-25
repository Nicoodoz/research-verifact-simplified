# 039：完整EHR高召回归因审计

## 目标

038发现U2边界翻转的label改善不能自动解释为证据核验增强。039不优化任何方法，只追查“证据去哪了”：对038全部342条U0非S→U2 S翻转，以及固定hash稳定S/NS/NA各40条对照，从036同一患者、同一目标住院、排除discharge summary的完整eligible EHR语料中做高召回搜索，再进行GT盲证据审计。

## 归因类别

A — C48 sufficient：实际036 C48已足以完整支持claim。
B — full-EHR search sufficient, C48 missed：C48不足，但从完整eligible EHR高召回搜索补充的外部passage后可建立完整支持。
C — partial/conflicting：存在相关证据，但claim至少一个实质要求只部分支持、矛盾或缺失。
D — no clear support / uncertain：高召回搜索后仍找不到清楚支持，或关系无法可靠确定。

A/B/C/D是自动化研究审计标签，不是医生gold。

## 搜索设计

1. 冻结038的462条blind cohort，不按039结果换样本。
2. 每条claim先由Qwen仅基于claim本身生成最多4个保守搜索query和material requirements；不看GT、U0/U2、原reason或EHR。
3. 复用036已经完成的BGE embedding，不新增embedding调用；对该患者完整eligible corpus计算原claim的完整dense排序、原claim BM25排序，并对扩展query计算BM25排序。
4. 多排序RRF融合后，保留C48之外最多80个最高排名passage，连同原C48一起交给Qwen证据审计。
5. 审计必须逐项检查claim要求，给出relation与可逐字回查的passage引用。HTTP200不因答案/格式重试。

## 研究边界

- 039发生在reserved40消费之后，是post-hoc mechanism attribution，不用于重选λ、Gate、Std_M/V或其他参数。
- “完整EHR”在本任务中指036预先定义的target-admission eligible EHR corpus：目标住院日期范围内、排除discharge summary的原始note段落。它不是患者终身全部记录，也不等于医生标注时一定看到的全部材料。
- 高召回搜索遍历完整eligible corpus的BM25/dense分数，但最终LLM审计只看到原C48和融合排名最高的最多80个额外passage；因此D只能解释为“本审计未找到清楚支持”，不能证明完整EHR绝对不存在证据。
- 039单任务API保护上限60元；长期授权范围内直接执行。
