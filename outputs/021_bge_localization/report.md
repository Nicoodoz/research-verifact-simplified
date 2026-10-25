# 021：BGE 本地化与 API 版冻结等价性检查

## 1. 结论

**两个 BGE 模型均已成功本地化；但相对 020 的 API BGE 链路，严格冻结等价性 FAIL。**

021 复用 020 的 remaining-development 10 名患者、879 条 claim、2057 个 embedding 文本与冻结 API embedding/rerank 输出，不产生任何新的付费 API 调用。40 名 reserved test 未使用，也没有读取 GT、Judge 标签或 PA/MCC 来选择本地实现。

事前严格门槛是：879/879 条 claim 的最终有序 selected_ids 与最终 reference 字符串均必须和 020 API 版完全一致。最终仅 565/879 条 reference 完全一致，因此不能把本地版静默视作 020 的同一冻结实现。

## 2. 本地实现

### Embedding

- 模型：BAAI/bge-m3
- HF commit：5617a9f61b028005a4858fdac845db406aefb181
- 权重：pytorch_model.bin
- 官方 LFS SHA-256：b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38
- 实现：CLS pooling + L2 normalize
- 最终用于等价检查的 precision：FP32
- 2057 条冻结文本全部完成
- FP32 运行：约 46.31 s；CUDA max allocated 约 2272.85 MiB

### Reranker

- 模型：BAAI/bge-reranker-v2-m3
- HF commit：953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
- 权重：model.safetensors
- 官方 LFS SHA-256：d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286
- precision：FP16
- batch size：32
- max_length：512
- 020 冻结 pair 实测最大长度：319 tokens，因此 512 不截断任何 pair
- 879 条 claim、49,246 个本地 pair 全部完成
- 运行约 515.68 s；CUDA max allocated 约 1317.81 MiB

GPU：NVIDIA GeForce RTX 3060 Laptop GPU 6GB。

## 3. Embedding 数值与候选结构

最终 FP32 本地向量对 API 向量：

- cosine mean：0.99993414
- cosine median：0.99994103
- cosine P01：0.99978129
- cosine min：0.99944489
- API / local 平均 L2 norm 均约为 1

尽管逐向量 cosine 非常高，排序边界仍会受到微小数值差异影响：

- B48 有序完全一致：0/879
- B48 集合完全一致：621/879
- B48 平均 Jaccard：0.987217
- C48 有序完全一致：7/879
- C48 集合完全一致：675/879
- C48 平均 Jaccard：0.990260

这说明“向量几乎相同”不能直接推出“候选排序完全相同”。

## 4. Precision 诊断

FP16 embedding 先行诊断得到：

- cosine mean：0.99993303
- B48 集合完全一致：617/879
- C48 集合完全一致：666/879
- C48 平均 Jaccard：0.989708

FP32：

- cosine mean：0.99993414
- B48 集合完全一致：621/879
- C48 集合完全一致：675/879
- C48 平均 Jaccard：0.990260

因此在不读取 GT / Judge 性能的前提下，以 API 输出结构相似度作为纯工程诊断，FP32 略优，最终 embedding 等价检查采用 FP32。该选择不是按 PA/MCC 调参。

## 5. Reranker 等价性

在 020 API 冻结候选上的 49,193 个共同 pair：

- 完整排序完全一致：0/879
- 平均 Spearman：0.996601
- 最低 Spearman：0.959819
- Top-16 有序完全一致：79/879
- Top-16 集合平均重合：0.977673
- API relevance score vs sigmoid(local raw logit) Pearson：0.999221
- MAE：0.001370

这说明本地 reranker 与 API reranker 的模型行为高度接近，且 API relevance score 与本地 raw logit 的 sigmoid 变换高度对应；但微小数值差异足以改变部分排序。

固定 API C48，仅替换 reranker 时：

- selected_ids 完全一致：594/879
- final reference 完全一致：594/879

因此严格不等价并不只是 embedding 造成，reranker 服务实现本身也存在可观察差异。

## 6. 端到端本地 BGE 链路

FP32 local embedding → 原 BM25/C48 → FP16 local reranker → 原 select_evidence：

- selected_ids 有序完全一致：565/879
- selected_ids 集合完全一致：565/879
- selected-ID 平均 Jaccard：0.925449
- final reference 完全一致：565/879

严格门槛要求 879/879，因此：

**frozen-equivalent = FAIL。**

## 7. 应如何解释

021证明的是两件不同的事：

1. **本地化可行**：RTX 3060 Laptop 6GB 可以稳定完成 BGE-M3 embedding 和 bge-reranker-v2-m3 rerank；模型权重、输入和输出均可冻结复现。
2. **不能声称与 API 逐样本等价**：即使 embedding cosine 和 reranker ranking correlation 都非常高，最终 C48 reference 仍有 314/879 条发生变化。

因此，020 的科学结果仍属于其原 API-BGE 实现条件。021 不重写 020，也不把 020 的 PA/MCC 自动继承给本地实现。

如果后续 reserved test 改用本地 BGE，应在进 reserved test 之前把本地模型 commit、precision、tokenization、候选规则与 selection 全部冻结，并把本地 BGE 作为新的实现条件建立同期 baseline；不能同时声称“还是原 020 实现”。

## 8. 范围与完整性

- 新付费 API：0
- reserved test：未使用
- GT / Judge 性能用于实现选择：否
- 020 冻结输入哈希：未改变
- 项目 .gitignore：未修改
- 模型权重：仅本机 .git/info/exclude 排除，不进入 Git
- 两个模型官方 LFS SHA-256：均匹配

机器可读汇总：comparison_summary.json  
逐 claim 比较：claim_comparison.csv  
自校验：verification_001.json  
协议：protocol_001.md
