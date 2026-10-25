# 008 相关工作：实际阅读范围与研究边界

这是支持 008 设计的定向原文阅读，不是系统综述。按 academic-paper-reading 的问题—方法—证据—局限核对；PDF 已保存并按页提取，未声称读完全部附录。价格/API 文档另见下载 manifest。

|工作|实际读到的原文|与本次最相关的发现|008 的区别和不能声称的创新|
|---|---|---|---|
|[Query2doc, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.585/)|PDF 1–5 页，方法、表 1/2、分析、结论|LLM 生成 pseudo-document 扩展 sparse/dense 查询；保留原查询重要；强蒸馏检索器上收益较小，域外结果并非全正，生成可能包含错误|008 不生成伪患者记录，用需求和短查询控制范围；在个人 EHR 中保留医生标注 claim，并对较强共享检索器比较。不能把 LLM 扩展查询本身当新贡献|
|[Query Rewriting for Retrieval-Augmented Large Language Models, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.322/)|PDF 1–6、8 页，框架、训练、检索实现、提示表、检索分析|Rewrite-Retrieve-Read 已让模型思考所需知识并生成查询；也训练 T5/PPO rewriter。Bing 检索的 answer hit 与最终 QA 正确率增幅不一致|008 是零训练、临床 claim 核验；源上下文不可信，需控制额外限定/反证漏检。本文已有“需要找什么”的基本思想，不能声称首创|
|[RARR, ACL 2023](https://aclanthology.org/2023.acl-long.910/)|PDF 2–5 页，任务定义、研究/修订阶段、提示实例、覆盖式证据报告|CQGen 生成覆盖需核验方面的问题、检索/选择证据，再检查和修订原生成文本；证据归属不自动等于真实性|008 不编辑目标，不使用源文字自证，只在同患者 EHR 找证据；是否丢失状态/事件以及少数标签的代价要实测。本次未据未读结果页引用效果数字|
|[Step-by-Step Fact Verification System for Medical Claims, NAACL 2025](https://aclanthology.org/2025.naacl-short.68/)|PDF 1–4 页，方法、数据、表 1 及部分讨论|已在 SciFact、HealthFC、CoVERT 上生成后续问题，使用网页或模型内部知识，并比较谓词辅助设置；实验排除 NEI，只评 Supported/Refuted，且基线与下游模型并不完全相同|临床/医学领域使用规划也非空白。008 面向个人 EHR 而非一般健康常识，保留 NA 与不充分支持、原医生标签和共享下游组件；不能引用其 F1 增幅证明本方法在 EHR 可行|
|[FIRE, Findings NAACL 2025](https://aclanthology.org/2025.findings-naacl.158/)|PDF 1–3 页，摘要、框架、相关工作；未精读完整结果/附录|针对 atomic claim 交替决定回答或继续搜索，允许依据内部知识停止检索；已有固定查询数和成本效率的讨论|008 是一次性规划、不是迭代智能体；所有 144 个实际计划均生成两条查询，未实现自适应少查。个人 EHR 的患者事实不能靠一般模型知识替代记录|

方法依据：BGE-M3 官方 [模型卡](https://huggingface.co/BAAI/bge-m3) 说明支持 dense/sparse/multi-vector，且查询无需额外 instruction；硅基流动 embedding endpoint 本次仅提供 dense。共享 BM25+dense 及共享 claim reranker，是为检验收益是否仅来自词面基线过弱，仍不是对所有强检索器的结论。

本项目真正待回答的问题是：在不重新标注原命题、也没有医生 evidence gold 的条件下，生成式规划能否带来可回查的证据收益，且不以隐式改变目标范围为代价。若只有缩写展开收益、只有少数案例，或候选改善被选择阶段/判断误差抵消，应如实缩小论文主张。005/006 的来源与标签讨论仍适用，不把上下文后的更窄命题自动视作原医生标签的目标。
