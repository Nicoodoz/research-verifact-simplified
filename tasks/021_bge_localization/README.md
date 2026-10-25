# 021 BGE 本地化与冻结等价性检查

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/021_bge_localization/report.md)。 独立结论查[审计末尾](../../reviews/021_bge_localization.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

021 将 020 中通过硅基流动 API 使用的两个 BGE 模型迁移到本地 GPU，并在不调用新收费 API、不使用 GT/Judge 正确率、不使用 reserved test 的条件下，复用 020 冻结输入做全量 API→本地等价性检查。

正式协议：outputs/021_bge_localization/protocol_001.md  
正式报告：outputs/021_bge_localization/report.md  
当前状态：outputs/021_bge_localization/CURRENT.md

## 最终本地条件

- Embedding：BAAI/bge-m3
  - HF revision: 5617a9f61b028005a4858fdac845db406aefb181
  - FP32
  - CLS pooling
  - L2 normalize
- Reranker：BAAI/bge-reranker-v2-m3
  - HF revision: 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
  - FP16
  - batch 32
  - max_length 512；020冻结pair实测最大319 tokens
- GPU：RTX 3060 Laptop GPU 6GB

模型权重位于 .local_models/021/，只通过本机 .git/info/exclude 排除，不纳入 Git。项目 .gitignore 未修改。

## 正式重放顺序

在项目根目录运行：

1. 本地 embedding：
   E:\miniconda3\envs\research\python.exe -X utf8 tasks\021_bge_localization\run_embedding_fp32_021.py

2. 重建 FP32 embedding 候选：
   E:\miniconda3\envs\research-verifact\python.exe -X utf8 tasks\021_bge_localization\prepare_candidates_variant021.py --vectors local_vectors_fp32.npy --tag fp32

3. 构建 reranker pair：
   E:\miniconda3\envs\research-verifact\python.exe -X utf8 tasks\021_bge_localization\prepare_pairs_variant021.py --tag fp32

4. 本地 reranker：
   E:\miniconda3\envs\research\python.exe -X utf8 tasks\021_bge_localization\run_rerank_checkpoint021.py --tag fp32emb_fp16rr_b32 --pairs rerank_pair_ids_fp32.jsonl --dtype fp16 --batch 32 --max-length 512

5. 最终等价性分析：
   E:\miniconda3\envs\research-verifact\python.exe -X utf8 tasks\021_bge_localization\analyze_variant021.py

6. 收尾自校验：
   E:\miniconda3\envs\research-verifact\python.exe -X utf8 tasks\021_bge_localization\verify021.py

## 正式结论

两个模型均可本地运行，但严格 frozen-equivalent gate 未通过：

- 固定 API C48，仅替换本地 reranker：594/879 final reference 完全一致。
- embedding + reranker 全本地：565/879 final reference 完全一致。
- 严格门槛要求 879/879，因此 FAIL。

这不改写 020 的科学结果。若未来 reserved test 使用本地 BGE，应把本地链路视为新的实现条件，并建立对应的同期 baseline。

## 诊断/历史脚本

以下文件保留执行演变，但不是最终正式重放入口：

- run_embedding021.py：FP16 embedding 诊断。
- prepare_rerank021.py：早期 FP16 embedding 候选/配对构建。
- run_rerank021.py：早期固定 batch 版本。
- run_rerank_variant021.py：早期无 checkpoint 版本，执行中止后由 checkpoint 版本替代。
- analyze021.py：早期硬编码 FP16 路径分析草稿，未作为最终报告生成器。
- sanity021.py：小样本 GPU/输出 sanity check。
- compare_rerank_partial021.py、compare_partial_reference021.py：执行中的盲结构诊断。
- download_weight021.py：Hugging Face 大权重分段断点下载工具；最终权重由用户下载并经官方 LFS SHA-256 验证。

不要把这些诊断版本的中间结果当作额外独立实验样本。
