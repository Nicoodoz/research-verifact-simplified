# 041：Evidence-gated Explanation Synchronization

041不是“看到最终标签后让LLM编一段同意它的理由”。它是一个确定性的证据门控解释层，只处理post-hoc标签与原解释不同步的问题。

## 输入与规则

- 原始036 scoring verdict/reason/checks；
- U2最终标签；
- 039对U2翻转的证据归因与严格可追溯support trace；
- 040冻结的路线决策。

对最终U2=Supported：

1. 若原scoring verdict本来就是Supported：保留原reason，标记pre-existing aligned explanation。
2. 若最终S来自post-hoc改判：
   - 039为A：可生成C48-grounded synchronized explanation；
   - 039为B：仅在040允许retrieval-augmented模式时，可生成“expanded-EHR-grounded”解释，并明确证据来自C48之外；
   - 039为C/D/U：不得生成支持理由，输出EXPLANATION_ABSTAIN / evidence mismatch。
3. 036中4条非U2-flip但Score_verdict!=U0=U2=Supported的样本未进入039，默认abstain，不用事后补写理由。

## 解释生成

不新增LLM调用。解释由039已验证的material requirements、relation和逐字quote确定性渲染，避免标签条件化后再次幻觉式合理化。

## 评价

- final-S explanation coverage；
- 342个U2翻转上的coverage；
- R/H/W分别被解释/拒绝数量；
- false-justification：H/W中仍被证据门控放行并生成Supported解释的数量；
- explained-flip GT precision：有解释的翻转中GT=Supported比例；
- C48-only与A+B（full-EHR augmented）两个工作点都报告，不用reserved结果再挑一个winner。

041是post-hoc系统一致性分析，不回写036最终方法，也不声称已完成医生级解释忠实性验证。
