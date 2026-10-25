# 017相关研究与贡献边界

核对日期：2026-09-16。这里只定位直接相关的方法，不声称完成系统综述。

| 研究 | 已有关系 | 017的具体区别／限制 |
|---|---|---|
| [FER: From Relevance to Utility](https://arxiv.org/html/2310.11675v2) | 用verifier反馈指导fact-verification证据选择；所查v2方法有gold evidence分类损失和相对gold evidence的utility差 | 017没有passage gold，只能用医生claim verdict评价固定Judge下的有限证据替换；不是首次提出utility |
| [REPLUG](https://aclanthology.org/2024.naacl-long.463/) | 冻结黑盒LM也可以为可训练检索器提供下游监督 | 017用三类医生verdict的correctness差，而非LM生成概率；仅低容量pairwise ranker，不改retriever权重 |
| [W-RAG](https://arxiv.org/abs/2408.08444) | 从下游OpenQA取得弱监督、学习有助于问答的检索结果，减少人工passage标签依赖 | 缺少evidence-level标注不是017独有。017需证明临床个人EHR、医生claim标签和patient-disjoint泛化下的价值 |
| [CUE-R预印本](https://arxiv.org/abs/2604.05467) | 以证据移除／替换等干预测量检索使用与结果utility，强调超越最终答案单一分数 | counterfactual evidence utility也非全新。017仍须区分Judge重复波动、rescue、harm和候选范围，不将正确标签称为医学evidence gold |

因此，可能成立的贡献是这组**具体限制下的实证方法或否定证据**：无evidence标注、只有clinician claim verdict；GT盲的有限完整段替换；保留baseline大部分证据；相同输入重复；低容量且patient-disjoint训练／选择；冻结后新患者确认。

仅出现几个rescue、拟合训练患者或较高oracle上限，均不足形成已验证方法贡献。若headroom、患者外选择或最终确认失败，应保留真实负结果，不把未来改进写成本轮已实现成果。
