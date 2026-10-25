# 003_error_analysis：结果入口

本页描述003当时的探索工作。至009，40名开发患者中的前24名已用于方法/案例分析，剩余16名；保留测试不用于方法选择。当前研究优先级见[009入口](../009_retrieval_baselines/README.md)。

任务已完成，用户已确认结项（2026-09-13）。后续独立定向复核 PASS，H03 原阻塞项关闭，见 [审计末尾追加记录](../../reviews/003_error_analysis.md)；未新增医生裁决。现行报告保留生成时的“尚未独立复核”历史措辞，不代表当前状态。**[正式中文报告](run_001/review_004/report.md)** 提供发现、逐例依据、未解决问题及两个小实验假设。

20 名探索患者、40 名后续开发患者、40 名保留测试患者已经冻结。探索组含 1,817 条有效 atomic claims；本轮分析 24 个案例，LLM-written 和 human-written 各 9 个错误、3 个正确对照。没有运行新模型、重判 GT 或查看保留组的临床案例。

003 提出的优先假设是：已有证据是否被正确对应到事件，以及是否足以支持完整命题。该假设已完成 [004 首次 pilot](../004_event_alignment_pilot/README.md)，结果方向不一致且检查结构遵守有限，不支持直接扩大当前版本；原第二个小实验未按003原方案单独执行；相关问题已在005–009继续分析，不是当前自动待办。H03 已撤回“遗漏时间”的归因，单列为时长支持边界；H04 补充术语／检查对应及输入中已存在的异常信息。L04、L08 的完整输出同样已提到限定条件，不能统一归因为漏看。报告把这些观察与原因假设分开，保留无法解释的案例，不能据小样本估计总体失败机制比例。

| 用途 | 文件 |
| --- | --- |
| 正式报告与案例导航 | [run_001/review_004/report.md](run_001/review_004/report.md) |
| 24 例中文阅读与原文锚点 | `run_001/review_004/cases/` |
| 机器阅读记录、72 处 EHR/reference 摘录及 53 处模型输出摘录 | [reviews.json](run_001/review_004/reviews.json) |
| 逐模型阅读范围与原始输出字段核对 | [output_review.json](run_001/review_004/output_review.json) |
| 病例清单、分析标签、可回查键 | [case_index.csv](run_001/review_004/case_index.csv) |
| 实际输入对照与汇总 | [reference_comparison.json](run_001/review_004/reference_comparison.json) · [summary.json](run_001/review_004/summary.json) |
| 完整探索队列点估计 | [metrics.json](run_001/metrics.json)；队列和预测 CSV 在同目录 |
| 冻结患者分组 | [patient_groups.json](patient_groups.json) |
| 本地解释记录源文件 | [review_notes.json](review_notes.json)、[report_template.md](report_template.md) |
| 提取与证据验证 | [提取 manifest](run_001/manifest.json) · [review checks](run_001/review_004/checks.json) |
| 重复运行及最终检查 | [verification_003/verification.json](verification_003/verification.json) |
| 修订专项检查与历史文件指纹 | [correction_validation.json](verification_003/correction_validation.json) · [pre_revision_sha256.json](verification_003/pre_revision_sha256.json) |
| 任务与复查代码 | [任务说明](../../tasks/003_error_analysis/README.md) |

本次复用的两份提取含 38 个相同材料文件；修订报告的 34 个报告/机器文件重复生成后逐字节相同。42 项测试通过，其中本次新增 5 项检查模型输出完整展示、来源身份、引用篡改和最终回答字段差异。共核对 125 处摘录；这些检查不构成独立临床裁决。正式审计 001 的历史异常仍保留，003 完成不代表这些问题被修复。模型之间输入不一定相同、医生缺少统一 gold evidence、部分命题有歧义等限制在报告中单列。

`run_001/review_001` 是初稿；`review_002` 补齐摘录行边界；`review_003` 是原独立审计对象。`run_001/review_004` 为现行修订报告，`run_002/review_003` 为其重复生成结果。原审计意见、修订自查与结项状态见 [审计记录](../../reviews/003_error_analysis.md)。历史 run、manifest 和 verification 均保持运行时快照，其中旧的本地保存说明及 Git 忽略检查记录不再作为现行约定。
