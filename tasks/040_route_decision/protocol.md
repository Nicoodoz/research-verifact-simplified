# 040：039后研究路线决策

040是零API的决策任务，输入只使用039冻结后的A/B/C/D归因，不再搜索新特征或调λ。

## 事前决策规则

以219条R为主要对象，A/B/C/D按039定义。无效审计单列，不把它算作无证据。

1. 若A占有效R至少50%：支持“decision-boundary dominant”。后续解释同步优先只用原C48。
2. 否则，若A+B占有效R至少50%且B>A：支持“retrieval + decision mixed / retrieval-dominant”。后续解释同步允许使用039新增EHR证据，但必须明确这已不是原036 C48输出。
3. 若A+B占有效R低于50%：支持“evidence/scope mismatch dominant”。λ只能定位为label decision utility；不开发默认解释重写器。041只能做evidence-gated selective explanation / abstention演示。
4. H/W中A+B比例作为false-justification风险：若明显非零，041必须报告对错误U2翻转的错误证据放行，不以“解释一致率”单独选方法。

## 边界

040不修改036/039结果，不产生新的winner，不使用reserved结果调新的分类参数。041是否继续不取决于“分数好不好看”，而是按上面规则决定其功能形态：C48-only、retrieval-augmented或selective-abstention。
