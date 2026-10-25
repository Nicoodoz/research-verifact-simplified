# 021 当前状态

**状态：执行与自校验完成，待独立审计。**

021 已将 020 链路中的 BGE-M3 embedding 与 bge-reranker-v2-m3 reranker 本地化到 RTX 3060 Laptop 6GB，并在 020 冻结的 10 名 development 患者、879 条 claim 上完成 API 版 vs 本地版全量等价性检查。

核心结果：
- BGE-M3 本地 FP32 vs API embedding：2057 个向量 cosine mean 0.99993414。
- C48 候选集合完全一致 675/879，平均 Jaccard 0.990260。
- 本地 reranker 在 API 候选上的平均 Spearman 0.996601；API relevance score 与 sigmoid(local logit) Pearson 0.999221。
- 固定 API C48、仅替换本地 reranker：final reference 完全一致 594/879。
- embedding + reranker 全本地：final reference 完全一致 565/879。

021 的事前严格门槛要求 879/879 条 claim 的 ordered selected_ids 和 reference 均完全一致，因此 **strict frozen equivalence = FAIL**。

这不表示本地模型不可用。它表示本地实现与 API 实现高度接近，但不是逐样本完全相同的冻结实现。020 的 PA/MCC 结果仍属于原 API-BGE 条件，不能自动继承到本地链路。

范围：
- 新付费 API：0
- reserved 40 人：未使用
- GT / Judge 性能用于实现选择：否
- 020 冻结输入哈希：未改变
- 模型权重 SHA-256：与固定 HF commit 的官方 LFS 记录一致
- 项目 .gitignore：未修改；权重只在本机 .git/info/exclude 中排除

若未来 reserved test 使用本地 BGE，应先把本地模型 commit、precision、tokenization、候选与 selection 规则冻结，并建立对应同期 baseline；不能把它称为 020 API-BGE 的无差别替代。

正式入口：
- 主报告：report.md
- 机器汇总：comparison_summary.json
- 逐 claim：claim_comparison.csv
- 自校验：verification_001.json
- 协议：protocol_001.md

本页属于执行者收尾，不是独立审计 PASS。
