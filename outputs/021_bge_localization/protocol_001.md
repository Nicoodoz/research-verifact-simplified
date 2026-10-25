# 021：BGE 本地化与 API→本地冻结等价性检查

状态：收费前/结果前冻结协议。021不调用任何新的付费API，不使用40名reserved test，不读取GT或Judge性能结果来选择本地实现。

## 目标

将020链路中的两个硅基流动BGE服务本地化：
- embedding：`Pro/BAAI/bge-m3` → Hugging Face `BAAI/bge-m3`
- reranker：`Pro/BAAI/bge-reranker-v2-m3` → Hugging Face `BAAI/bge-reranker-v2-m3`

复用020 remaining-development 10名患者879条claim、2057个embedding文本、879个rerank请求和已冻结API回执，仅比较BGE层及最终C48 reference。

## 环境隔离

- VeriFact冻结分析仍使用 `research-verifact` 环境，不安装Torch。
- 本地BGE推理由既有Conda `research` 环境执行：PyTorch 2.8.0+cu128、Transformers 4.56.1、SentenceTransformers 5.1.0。
- 模型权重保存于仓库内本机排除目录 `.local_models/021/`；只写 `.git/info/exclude`，不修改项目 `.gitignore`。

## 冻结实现原则

embedding使用官方HF模型的dense向量，L2归一化，1024维；不添加query instruction。默认CUDA FP16，tokenizer截断规则由模型配置决定，批量大小仅作为内存/速度参数，不改变单条输出语义。

reranker使用官方HF cross-encoder，对020完全相同的 `query + document` 对评分；排序只依赖raw logit的单调次序。若API返回分数经过sigmoid等单调变换，数值尺度差异不视为排序不等价。

不根据GT或Judge标签调模型、prompt、chunk、候选容量、RRF、C48规则或selection规则。

## 比较层次

1. **Embedding数值诊断**：2057个API向量 vs 本地向量的逐条cosine、L2 norm、最大绝对差；只作诊断。
2. **Dense/C48结构**：用本地向量重建020相同HybridIndex，比较879条claim的dense Top-48及C48候选有序列表。
3. **Reranker隔离比较**：对020 API冻结的union候选运行本地reranker，比较每条claim的完整排序、Top-16/Top-k重合和rank correlation。
4. **端到端本地重建**：本地embedding→相同BM25/C48→本地reranker→相同select_evidence，比较879条claim的selected passage IDs与最终reference。

## 等价判定（结果前冻结）

**frozen-equivalent PASS 仅在以下全部成立时：**
- 879/879条claim的最终 `selected_ids` 与020 API版完全一致（有序列表精确相等）；
- 879/879条claim的最终 `reference` 字符串SHA-256完全一致；
- 没有修改020冻结输入、候选规则、selection规则或API历史文件。

任何一条最终reference不同，都不称“冻结等价”。可以另外报告near-equivalence诊断，但若未来切到本地BGE，应视为新的实现条件并重新建立同期baseline，而不是静默继承020。

## 允许的工程诊断

若默认FP16实现不满足最终等价，可在**不读取GT/Judge结果**前提下：
- 检查模型HF revision、tokenization、pooling、归一化和precision；
- 以API向量/排序本身为工程参照定位实现差异；
- 记录所有尝试，不删除失败版本。

不得通过患者标签、PA/MCC或Judge正确率选择实现。

## 输出

`outputs/021_bge_localization/` 保存模型revision、环境、API绑定哈希、本地向量/分数摘要、逐claim结构比较、最终报告和可重复命令。模型权重不纳入Git。
