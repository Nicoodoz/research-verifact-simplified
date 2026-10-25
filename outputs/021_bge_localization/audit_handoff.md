# 021 独立审计交接

021 已执行完成并通过执行者离线自校验；**尚未进行独立审计**。

## 审计核心问题

1. 021 是否确实只复用了 020 冻结的 remaining-development 10 名患者 / 879 条 claim，而没有使用 reserved 40 人。
2. 两个 Hugging Face 权重是否绑定到登记的固定 commit，且本地文件 SHA-256 与官方 LFS SHA 一致。
3. BGE-M3 本地实现是否为 CLS pooling + L2 normalize，最终等价性条件使用 FP32；precision 选择是否仅依据 API 输出结构相似度，而未读取 GT / Judge 性能。
4. reranker 是否对冻结 pair 使用同一 query/document 文本；max_length=512 是否因全部 pair 最大319 tokens而不产生截断。
5. comparison_summary.json 与 claim_comparison.csv 是否能够从冻结输入和本地输出离线复算。
6. 严格 gate 是否按事前 protocol_001.md 执行：只有 879/879 ordered selected_ids 与 879/879 exact reference 同时满足才 PASS。
7. 最终 565/879 exact reference 是否应判 strict frozen equivalence FAIL；不得用高 cosine / 高 Spearman 替代该 gate。
8. 021 是否没有新付费 API、没有 GT/Judge 正确率驱动实现选择、没有改写020结果。
9. 模型权重是否只通过本机 .git/info/exclude 排除，项目 .gitignore 未修改。

## 关键结果

- Embedding API vs local FP32 cosine mean：0.99993414。
- C48 集合完全一致：675/879；平均 Jaccard：0.990260。
- Reranker API候选平均 Spearman：0.996601。
- API relevance score vs sigmoid(local raw logit) Pearson：0.999221。
- 固定 API C48、仅换本地 reranker：594/879 final reference 完全一致。
- embedding + reranker 全本地：565/879 final reference 完全一致。
- strict frozen equivalence：FAIL。

## 正式入口

- protocol_001.md：事前等价定义。
- registration_001.json：模型commit、020输入哈希和环境登记。
- report.md：中文主报告。
- comparison_summary.json：机器汇总。
- claim_comparison.csv：879条逐claim比较。
- precision_diagnostic_001.json：FP16/FP32 embedding工程诊断。
- verification_001.json：执行者离线收尾自校验。
- CURRENT.md / CURRENT.md.json：当前状态。
- execution_closure.json：执行关闭状态。
- tasks/021_bge_localization/README.md：正式重放入口与诊断脚本边界。

执行者自校验 PASS 不等于独立审计 PASS。
