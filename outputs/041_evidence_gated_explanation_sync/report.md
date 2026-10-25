# 041：Evidence-gated Explanation Synchronization

## 核心结论

041没有做“看见final label后让LLM补一段同意它的理由”。它把039已经验证过的逐要求证据和逐字quote作为唯一解释来源：只有证据审计严格通过的post-hoc Supported改判才生成同步解释，其余明确abstain。

这个模块能消除“明明final=S，却挂着一段Not Supported理由”的直接展示错误，但代价是大量改判无法获得解释，而且证据门控本身仍会错误放行一部分GT为non-S的H/W。

因此041更像**选择性解释层**，不是把038问题彻底修好的默认系统。

## 1. 两个工作点

| 指标 | C48-only | Expanded A+B |
|---|---:|---:|
| U0→U2 S翻转 N | 342 | 342 |
| 获得新证据解释 | 83 | 153 |
| 翻转解释覆盖率 | 24.27% | 44.74% |
| R总数 | 219 | 219 |
| R获得解释 | 66 | 121 |
| R解释覆盖率 | 30.14% | 55.25% |
| H/W总数 | 123 | 123 |
| H/W被错误放行并生成S解释 | 17 | 32 |
| H/W false-justification率 | 13.82% | 26.02% |
| 有解释翻转中的GT=S比例 | 79.52% | 79.08% |

Expanded工作点把R解释覆盖从30.1%提高到55.3%，但H/W false-justification也从13.8%增加到26.0%，而有解释样本的GT precision几乎不变。**扩大证据搜索提高了覆盖，不提高自动证据门控对“正确改判 vs 错误改判”的区分能力。**

## 2. 放回完整3571条reserved主分析会怎样

U2最终Supported共2647条。若原scoring verdict已经等于最终U2标签，041不改原reason；只有发生post-hoc标签变化时才要求新证据解释或abstain。

- C48-only：2384/2647（90.06%）的final-S具有“原标签未变的原解释”或新的严格证据解释；
- Expanded：2454/2647（92.71%）达到这个结构性可展示状态。

这里的90%/92.7%**不是经过人工验证的解释忠实率**。其中大量是“原verdict与final label相同，所以保留原reason”，没有逐条重新做语义/医学忠实性审计。

所有final label发生变化的样本共382条：

- C48-only只为83条（21.73%）生成新的证据解释；
- Expanded为153条（40.05%）生成新的证据解释；
- 其余changed样本全部abstain，不再把旧reason伪装成final label解释。

036中还有4条final-S mismatch不是U0→U2翻转、未进入039；041按事前规则直接abstain。36条final non-S的标签变化也没有做专门证据审计，因此同样abstain。

## 3. 为什么不用LLM自由重写理由

对允许解释的A/B样本，041直接从038/039已经通过严格引用校验的requirement和quote确定性渲染。例如每个claim要求后面只列出实际C48或新增EHR passage中的逐字短引。

这样做故意避免一种危险流程：先把final label改成Supported，再提示模型“请解释为什么Supported”。后者很容易得到语言上自洽但证据上事后合理化的文本。

041不会修改任何U2标签，也不会把abstain样本重新判回NS/NA；它只决定“这个post-hoc标签目前是否有足够的自动化可追溯证据，可以展示一个同步解释”。

## 4. 这个模块解决了什么、没解决什么

解决的是输出结构问题：对于它真正放行的样本，展示给用户的解释不再来自一个相反的原verdict，而来自严格引用的证据trace。

没有解决的是临床正确性问题。Expanded模式仍对32/123个H/W错误U2翻转生成了Supported解释；即便C48-only也有17/123。因此“解释有证据”仍不能替代医生GT，更不能作为临床安全认证。

这也是为什么040没有把041选成新的默认主方法。

## 5. 论文定位

041适合作为038问题之后的“系统一致性补救实验”：它证明解释同步不能靠自由重写，而需要证据门控；同时也展示了门控的coverage–false-justification trade-off。

论文不应写成“我们修复了解释忠实性”。更准确的是：

> Evidence-gated synchronization can prevent unsupported post-hoc labels from automatically receiving a contradictory or fabricated explanation, but selective coverage and false justification remain substantial.

## 6. 执行边界

- 0 API、0新增费用；
- 不修改036/039任何标签或证据审计结果；
- 解释由严格trace中的逐字quote确定性渲染；
- C48-only与Expanded两个工作点全部报告，不根据reserved结果挑winner；
- 本任务仍是post-hoc分析，不能回写为036事前冻结系统。

机器输出：outputs.csv、metrics.csv、status.json。第一次离线运行因读取038字段名写错，旧输出已单独保留为buggy_field目录；修正后未调用任何API。
