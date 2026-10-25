# 002_reproduce_paper_results：结果入口

当前新实验的暂定实用链路见[009入口](../009_retrieval_baselines/README.md)：C48、保留A48对照；本页保留002的发布预测及全benchmark统计，不替代同期开发比较。

任务已完成（2026-09-13）。优先阅读 **[正式中文报告](run_003/report.md)**；统一评价协议、字段含义和命令见 [任务说明](../../tasks/002_reproduce_paper_results/README.md)。

本任务复算官方 release 已有预测，建立了 baseline 和新方法共用的评价代码。没有重新运行九个 Judge 或生成/检索系统，也没有开展新方法实验、训练或创建患者划分。

## 主要结果

- 覆盖 9 个模型、174 个 rater、54 行实验矩阵，展开为 **426 个模型/实验组合**（378 个主分析、48 个预分析），重评分 **1,437,100 条预测**。
- 正式 Table 1、Figure 3 和正文可定位的 **72 项点估计全部匹配发表精度**；72 个 CI 端点中 70 个匹配。比对项含图与正文重复引用，不代表 72 个独立实验。
- R1-70B + 100 sentence facts，LLM-written atomic claims，保留 invalid：**PA 93.1535%，AC1 0.927966，MCC 0.309543**。
- 该配置的 MCC 95% CI 复算为 **[0.245125, 0.366813]**，论文为 **[0.24, 0.35]**。独立 sklearn、另一种作者代码排序及 valid-only 诊断均保留，未确认差异原因。
- 正式 Supplementary Appendix 未取得，不能声称 Table S3 等补充结果全部逐值复现。p9 四组模型增幅的精确净差与发表展示值有细微差别；按作者图中单元格各自取整后相减能得到发表值，但这只是有代码依据的解释线索，未被正式附录确认。

## 发布预测的历史参照 baseline 与统一评价

公共入口为 [evaluate_predictions.py](../../scripts/evaluate_predictions.py)，核心函数为 `verifact_research.evaluation.evaluate`。原 baseline 与新方法必须使用同一实现、明确队列和同一评价参数。

本页历史参照配置是 R1-70B、sentence facts N100、rerank、absolute_time、current admission、deduplicate=True。默认研究口径为 valid-only、严格要求完整预测、三分类 micro PA/AC1/MCC、1,000 次患者 cluster bootstrap；all-propositions 和论文 item bootstrap 单独保留。

| 队列 | valid-only n | PA | AC1 | MCC | MCC 患者 bootstrap 95% CI |
| --- | ---: | ---: | ---: | ---: | --- |
| LLM-written / claim（主队列） | 3,441 | 93.1415% | 0.927855 | 0.305697 | [0.209621, 0.404732] |
| Human-written / claim | 5,624 | 73.3642% | 0.645662 | 0.478276 | [0.457933, 0.498683] |
| LLM-written / sentence | 998 | 92.6854% | 0.923939 | 0.050771 | [−0.013401, 0.133319] |

以上来自 [research_baselines.csv](run_003/research_baselines.csv)。九个 Judge 在相同 N100 sentence 配置下均已按该口径重评，保存 27 组结果和各类指标；完整 JSON 见 [research_baselines.json](run_003/research_baselines.json)。实际 R1-70B 预测与明确队列已导出，公共入口用法见任务说明。

**这些仍是全 benchmark 描述性结果，002 完成时尚无患者划分。** 后续 003 已冻结探索／开发／保留测试患者，见 [003 入口](../003_error_analysis/README.md)；不能把这里的全量结果称为新方法的未接触测试成绩。历史 run 和 manifest 未回写。

## 001 问题如何处理

原值全部保留，没有改标签、补预测或重写 EHR。

| 问题 | 本次处理及结果 |
| --- | --- |
| 74 条缺失预测 | 显式 available 分母 5,574/5,648，导出全部键；九模型另在共同 5,574 IDs 上重算。固定完整队列上的 PA 最坏/最好界另列，不能当 CI。 |
| missing 与 invalid 交叉 | 74 条缺失中有 1 条 invalid；valid-only 时仍缺 **73 条**，实际 5,551/5,624，不能靠排除 invalid 消除缺失。缺失 GT 为 Supported 60（其中 invalid 1）、Not Supported 14、Not Addressed 0。 |
| 456 条 invalid | 论文复现保留，实际 AI 覆盖其中 30 条；全配置另算 valid-only，不把两种口径混在一起。 |
| 时间元数据冲突 | 保留 cohort 标记与原始预测，端点另做排除敏感性分析；不推断它们导致错误，不重过滤 EHR。 |
| 2 条医生第二轮字段矛盾 | 保留 human_gt 和异常标记；位于无 AI 结果的 human sentence，不影响当前 AI 分数。 |
| 相同参数但 reference 不同 | 比较真实输入 SHA-256 和词数；不同 Judge 是发布系统整体对比，不能据此孤立推断模型能力。 |

值得后续关注：主配置 Supported/Not Supported/Not Addressed 的 recall 约 **96.49% / 38.32% / 16.67%**。始终预测 Supported 就能在 LLM claim 上取得 **94.98% PA、MCC=0**，因此 PA 必须结合 MCC 和少数类性能解释。

## 文件入口

| 用途 | 文件 |
| --- | --- |
| 人读报告 | [report.md](run_003/report.md) |
| 机器汇总 | [summary.json](run_003/summary.json) |
| 全配置指标与实际输入长度 | [ai_metrics.csv](run_003/ai_metrics.csv) |
| 完整指标与类别性能 | [ai_metrics.json](run_003/ai_metrics.json) · [per_class_metrics.csv](run_003/per_class_metrics.csv) |
| 论文逐项比较 | [paper_comparisons.csv](run_003/paper_comparisons.csv) |
| 队列与异常标记 | [cohort_master.csv](run_003/cohort_master.csv) · [cohorts.json](run_003/cohorts.json) |
| 缺失明细、共同队列结果 | [missing_prediction_keys.csv](run_003/missing_prediction_keys.csv) · [common_available_metrics.csv](run_003/common_available_metrics.csv) |
| invalid / 时间 / 医生一致性分层 | [sensitivity_metrics.csv](run_003/sensitivity_metrics.csv) |
| CI 独立核验 | [mcc_ci_diagnostics.csv](run_003/mcc_ci_diagnostics.csv) |
| 检查与指纹 | [checks.json](run_003/checks.json) · [manifest.json](run_003/manifest.json) |
| 重复运行及公共入口验证 | [verification_final.json](verification_final.json) · [30 项测试记录](verification_final.tests.txt) |

完整文件说明见任务 README。正式 run 有 39 个文件，其中 37 个机器结果文件；本次输出未复制患者临床正文和完整 reference。

当前重跑限制：全量复算脚本的仓库外 `--output-root` 路径展示问题尚未修复，使用默认或仓库内目录；公共评价 CLI 不受影响。详情见 [任务说明](../../tasks/002_reproduce_paper_results/README.md) 与 [审计记录](../../reviews/002_reproduce_paper_results.md)。

## 验证与历史

- `run_002` 与 `run_003` 使用相同分析实现、目标值、环境及原始数据；**37 个机器结果逐字节一致**，报告仅 run 编号不同。
- 30 项测试通过；公共 CLI 的论文口径与研究口径结果分别与全量 runner **逐字段相同**；相同方法的 paired comparison 差值与 CI 全为 0。
- 25 个原始文件前后未改，与 001 正式运行和官方 SHA256SUMS 匹配；已下载作者代码的内容哈希也已核对。
- 正式检查为 **163 pass、4 warning、1 unverified**。warning 包含 74 条缺失、2 条第二轮流程异常以及 MCC 两个 CI 端点差异；附录缺失为 unverified。002 不覆盖或改写 001 的检查结论。

| 记录 | 说明 |
| --- | --- |
| `run_001` | 首轮完整复算；已发现 MCC 区间差异，尚未纳入后续诊断、全队列 PA 界与最终验证。保留原输出。 |
| `run_002` | 最终分析实现的完整运行。 |
| `run_003` | 同实现重复运行，正式阅读入口。 |
| `evaluations/run_001` | 首次公共入口回放使用默认 strict missing 策略；指标相同，但策略字段与论文 available 策略不同，完整对象比较未通过。不是评分错误。 |
| `evaluations/run_002` | 显式使用论文 available 策略后，完整结果通过回放比对。 |
| `evaluations/run_003` | valid-only 患者 bootstrap 及同方法 paired comparison 回放通过。 |
| `verification.tests.txt` | 首次回放校验之前的测试记录，保留。最终验证使用 `verification_final.json` 和配套测试日志。 |

任务完成后更新 README、AGENTS 和任务文档，不回写运行时 manifest；文档哈希代表运行当时的快照。代码和评价结果的重复性由最终验证记录支持。
