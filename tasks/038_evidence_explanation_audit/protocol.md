# 038：证据—标签—解释一致性审计

## 目的

036已经证明若只评价claim-level医生标签，离线后处理可改变最终S/NS/NA并改善部分指标；但原reason/checks不会随U2、Gate或标准后处理改写。038只审计这一缺口，不修改001–037任何预测或参数。

## 审计对象

1. 全量统计036 R0共同有效3571条中，各后处理最终标签与scoring原始verdict的分歧。
2. 重点语义审计所有“U2最终Supported但原scoring verdict非Supported”的样本。
3. 盲证据审计覆盖全部342条U0非S→U2 S翻转候选，并按固定hash从Score_verdict=U0=U2的稳定S/NS/NA各抽40条，共462条。
4. 证据审计输入只含原claim+C48 reference，不含GT、患者分组结果、U0/U2/Gate标签或原reason。审计后才连接GT和R/H/W。
5. 对全部462条用Qwen3.8-27b和DeepSeek-V4-Flash-0731分别做结构化证据核查；这是自动化双模型审计，不是医生gold。原scoring模型也是DeepSeek，因此DeepSeek审计不称独立模型证据。
6. 对346条解释分歧仅用Qwen判断“原reason/checks与最终U2=Supported是否语义一致”，不以此替代证据核查。

## 证据判据

对claim的所有实质要求逐项判断supported/contradicted/unaddressed/uncertain并引用C48中的现有编号和原文短引。只有要求覆盖完整、全部supported、引用可在实际reference逐字定位时，记为trace-supported。否则不得仅因医生GT=Supported把C48称为充分证据。

## 边界

- 038是reserved已经消费后的post-hoc审计，不用于重新选择λ、Gate、Std_M/V或其他方法。
- 模型审计结果只能衡量自动化证据一致性，不是新增医学金标准。
- 若标签与C48证据不一致，保留为发现，不补证据、不重写原reason来制造一致。
- API总费用沿长期授权，038单独保护上限60元；不重试任何HTTP200回答。
