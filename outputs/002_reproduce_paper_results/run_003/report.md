# 002：论文核心结果复算与统一评价

本报告由 `run_003` 的实际计算结果生成。**已完成 release 预测重评分与评价代码建立；不等于重新生成 BHC、重新检索或重新运行九个 Judge。**

共复算 426 个模型/实验组合（主分析 378、预分析 48），处理 1,437,100 条实际预测。
正式论文可明确定位的点估计 72 项中，72 项与发表精度一致；CI 端点 72 项中，70 项一致。这里统计的是逐处数值比对项，包含正文与图重复引用的值。完整结果见 [paper_comparisons.csv](paper_comparisons.csv)，差异保留。

## 证据与复算范围

- **正式来源**：本地 `docs/sources/VeriFact.pdf`，NEJM AI 3(1), 2026；p6 Table 1、p7 Figure 3、pp6–8 正文。目标数值在计算前录入任务目录 `paper_targets.json`，Figure 3 已对照渲染原图。
- **官方数据定义**：v1.1.0 README 定义三类标签、9 个 Judge、主/预分析矩阵。本报告从原始 CSV/Parquet 重建命题队列及配置连接，并与 001 正式索引/缺失键核对。
- **作者实现证据**：[公开代码固定提交 f115d36](https://github.com/philipchung/verifact/tree/f115d36cb65fa2073fce0a10df56bb37f4cbcd50)。用于核实 bootstrap、排序、端点配置；未执行作者模型或分析脚本，也不把代码当作论文数值。
- **未确认**：正式 Supplementary Appendix 未取得；NEJM 附件访问返回 HTTP403。没有把预印本或推测值当作正式 Table S3。已复算相应 release 矩阵，但不能宣称所有补充表/曲线逐值复现。正文 p9 的四个模型增幅另按作者代码默认场景诊断，结果与解释边界见下文。

## 队列与评价定义

| 队列 | 全部 | valid only | 患者 |
| --- | ---: | ---: | ---: |
| llm / claim | 3,447 | 3,441 | 100 |
| llm / sentence | 998 | 998 | 100 |
| human / claim | 5,648 | 5,624 | 100 |
| human / sentence | 2,977 | 2,551 | 100 |

**论文复现口径**：保留 invalid，使用原始 `human_gt`；PA/AC1/MCC 均为三分类、命题等权。医生间 PA 是每条命题三个医生对的一致比例再取平均，不是三人一致率，也不是医生与最终 GT 的一致率。Table 1 的标签子集按最初三位医生中至少一位选择该标签定义，子集相互重叠。

PA 是 AI 与 GT 完全相同的比例。AC1 使用三类别名义权重与双方/三名医生的合并边际分布。MCC 使用三分类混淆矩阵公式；分母为零时返回 0（与 sklearn 一致），类别 precision/recall 无分母时为 null。固定标签顺序为 Supported、Not Supported、Not Addressed，混淆矩阵行是真值、列是预测。

论文 CI 使用 1000 次命题有放回抽样、95% percentile 区间、RandomState 种子 0..B−1；按固定作者代码，PA/AC1 先按 proposition_id 排序，MCC 保持 human_verdicts CSV 顺序。AC1 的 bootstrap 单次值按 irrCAC 默认保留 5 位小数。点估计由独立公式计算，并用指定版本库测试。

## 医生间一致性：实际复算

| 作者 / 粒度 | n | PA（95% CI） | AC1（95% CI） |
| --- | ---: | --- | --- |
| llm / claim | 3447 | 88.5% (87.6%–89.4%) | 0.876 (0.865–0.885) |
| llm / sentence | 998 | 84.7% (83.0%–86.7%) | 0.831 (0.811–0.854) |
| human / claim | 5648 | 73.3% (72.3%–74.2%) | 0.641 (0.626–0.654) |
| human / sentence | 2977 | 66.9% (65.6%–68.2%) | 0.527 (0.506–0.546) |

全部 16 个分层、各自 n/invalid 数及抽样成员见 `clinician_metrics.csv`、`clinician_subset_membership.csv`。001 已发现的三人各投一类实际为 467，论文流程写 478；此差异未通过修改标签消除。

## Figure 3 端点：LLM-written / atomic claim

以下均采用 rerank、absolute_time、仅目标住院、deduplicate=True。claim facts 的端点为 N=150，sentence facts 为 N=100；端点是图上标注位置，不代表每条曲线的最大值。

| Judge | EHR fact / N | n | PA | AC1 | MCC | 平均输入词数 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Gemma-3-12B | claim / 150 | 3447 | 92.2% | 0.918 | 0.136 | 3239.1 |
| Gemma-3-12B | sentence / 100 | 3447 | 91.6% | 0.912 | 0.093 | 3053.1 |
| Gemma-3-27B | claim / 150 | 3447 | 94.7% | 0.945 | 0.117 | 3239.1 |
| Gemma-3-27B | sentence / 100 | 3447 | 93.5% | 0.933 | 0.058 | 3053.1 |
| Llama-70B | claim / 150 | 3447 | 90.5% | 0.899 | 0.240 | 3239.1 |
| Llama-70B | sentence / 100 | 3447 | 88.8% | 0.880 | 0.218 | 3053.0 |
| Llama-8B | claim / 150 | 3447 | 79.3% | 0.769 | 0.082 | 3239.1 |
| Llama-8B | sentence / 100 | 3447 | 81.7% | 0.798 | 0.035 | 3053.0 |
| Qwen-3-30B-A3B-Instruct | claim / 150 | 3447 | 92.9% | 0.925 | 0.191 | 3239.1 |
| Qwen-3-30B-A3B-Instruct | sentence / 100 | 3447 | 93.0% | 0.927 | 0.171 | 3053.0 |
| Qwen-3-30B-A3B-Thinking | claim / 150 | 3447 | 83.1% | 0.812 | 0.250 | 3239.1 |
| Qwen-3-30B-A3B-Thinking | sentence / 100 | 3447 | 86.4% | 0.851 | 0.299 | 3053.0 |
| Qwen-3-32B | claim / 150 | 3447 | 90.2% | 0.896 | 0.203 | 3239.1 |
| Qwen-3-32B | sentence / 100 | 3447 | 91.8% | 0.913 | 0.189 | 3053.0 |
| R1-70B | claim / 150 | 3447 | 92.2% | 0.917 | 0.295 | 3239.1 |
| R1-70B | sentence / 100 | 3447 | 93.2% | 0.928 | 0.310 | 3053.1 |
| R1-8B | claim / 150 | 3447 | 88.2% | 0.873 | 0.146 | 3239.0 |
| R1-8B | sentence / 100 | 3447 | 86.7% | 0.857 | 0.104 | 3053.0 |

正文主配置 R1-70B + 100 sentence facts：PA **93.15%**，95% CI 92.34%–93.97%；MCC **0.3095**，95% CI 0.2451–0.3668。

**不能只看 PA 排名**：LLM claim 的 Supported 为 3,274/3,447，“始终预测 Supported”已有 **94.98% PA、MCC=0**，见 `trivial_baseline.csv`。主配置三类 recall 分别约 **96.49%、38.32%、16.67%**。正文所谓 R1-70B “最高 agreement”并非所有模型的 PA 最大值，Figure 3 自己也给出更高的 Gemma PA；应同时报告三类 recall/precision 和 MCC，但这不能替作者修正文义。

## 正文关键分层

| Judge | 作者 / 命题 | n | PA | AC1 | MCC |
| --- | --- | ---: | ---: | ---: | ---: |
| R1-70B | llm / claim | 3447 | 93.2% | 0.928 | 0.310 |
| R1-70B | llm / sentence | 998 | 92.7% | 0.924 | 0.051 |
| R1-70B | human / claim | 5648 | 73.3% | 0.644 | 0.477 |
| Qwen-3-30B-A3B-Thinking | llm / claim | 3447 | 86.4% | 0.851 | 0.299 |
| Qwen-3-30B-A3B-Thinking | llm / sentence | 998 | 84.9% | 0.834 | 0.233 |
| Qwen-3-30B-A3B-Thinking | human / claim | 5648 | 70.2% | 0.589 | 0.501 |

配置同上，均为 100 sentence facts。human sentence 没有发布 AI 预测，属于矩阵设计未覆盖，不能补出一个模型分数。全部主/预分析与 Top-N 结果见 `ai_metrics.csv`；各类 TP/FP/FN/TN、recall、precision、specificity、NPV、F1 见 `per_class_metrics.csv`。

## 差异、边界和实际处理

逐项差异如下（未静默过滤或调整种子来对齐）：

| 来源 / 分层 | 指标 | 论文 | 实际 |
| --- | --- | ---: | ---: |
| ai / R1-70B / llm / claim / sentence / 100 | mcc ci_lower | 0.24 | 0.245125 |
| ai / R1-70B / llm / claim / sentence / 100 | mcc ci_upper | 0.35 | 0.366813 |

对 R1-70B 主配置另用 sklearn 1.6.1 独立重算每一次 MCC bootstrap，得到相同区间；按作者脚本 5 改为 proposition_id 排序，以及显式 valid-only 口径的诊断见 `mcc_ci_diagnostics.csv`。这些预先列明的变体没有替换主结果，也没有搜索随机种子来匹配论文。当前无法确认正文 MCC 区间差异的原因。

### 预分析设置与 p9 模型增幅

预分析范围可从 release 确认：LLM claim、N=50、四个 Llama/R1 Judge × 两种 EHR fact。`preliminary_contrasts.csv` 保存单因素配对差值；`preliminary_summary.csv` 的八组合等权平均是本任务的描述性汇总，不冒充论文选参规则。该汇总下 rerank、absolute_time、current admission 的平均 PA 较高，但它们并非每个模型/粒度或每个指标都最高；尤其 current admission 的平均 MCC 为约 0.171，全部住院约 0.174。因此不应把正文概括理解成所有设置均严格占优。

作者脚本 9a 的默认场景为 LLM claim、100 sentence facts。四组模型正确/错误的配对表可以从实际预测复算：

| 候选 − 对照 | 论文增幅（百分点） | 精确 PA 差（百分点） | 两个单元格分别取一位小数后相减 |
| --- | ---: | ---: | ---: |
| Llama-70B − Llama-8B | 7.1 | 7.1076 | 7.1 |
| R1-70B − R1-8B | 6.5 | 6.4404 | 6.5 |
| R1-8B − Llama-8B | 5.1 | 5.0189 | 5.1 |
| R1-70B − Llama-70B | 4.3 | 4.3516 | 4.3 |

四个发表数字都能由“候选独有正确率”和“对照独有正确率”各自先按图表精度四舍五入再相减得到，作者代码也确实按这一精度显示单元格。**这提供了一种可检验的解释，但正式 Figure S11 未取得，不能确认作者实际采用了该计算过程。** 后续实验一律用未取整的精确指标相减，最后展示时才取整；不把论文的展示数字当作原始精度结果。

- **74 条缺失**：全部为 Qwen-3-30B-A3B-Thinking、human claim、claim facts N=100。论文复算显式采用 available 分母 5,574/5,648，保存 `missing_prediction_keys.csv`；其他模型完整，不将其分数假装成同样的分母。`common_available_metrics.csv` 对九个模型在固定共同 5,574 ID 上另算敏感性分析，成员另存。后续默认严格拒绝缺失预测。
- **456 条 invalid**：论文口径全保留，实际 AI 覆盖其中 30 条。`sensitivity_metrics.csv` 对每个配置单列 valid-only 结果，不把 valid-only 冒充原论文。
- **4 名患者时间元数据冲突**：保留全部原标签/预测/输入；另算去掉冲突患者命题的端点敏感性分析，标记在 `cohort_master.csv`。这只衡量这些样本对已有分数的影响，不能证明日期差异导致模型错误，也没有重新过滤 EHR。
- **2 条医生第二轮字段异常**：保持发布的 human_gt，并保留异常标记；均在 human sentence，当前 AI 矩阵无此组，不影响已有 AI 分数。医生 PA/AC1 仅使用第一轮三票。
- **Judge 输入不恒等**：`endpoint_input_comparisons.csv` 对各模型与 R1-70B 的同配置输入做 SHA-256 identity 对比，`ai_metrics.csv` 给出真实输入词数；不同 Judge 的比较是发布系统整体比较，不能直接归因为模型能力。exact text 不同不自动等于医学证据不同。词数严格采用 Python str.split，与作者方法一致；没有声称从图像复原横坐标精确原值。

## 后续研究统一口径

1. **同一实现**：baseline 和新方法都调用 `verifact_research.evaluation.evaluate`，命令入口 `scripts/evaluate_predictions.py`；不得另写一套指标。主评价三分类、proposition micro PA/AC1/MCC，并给出类别性能。
2. **冻结样本**：使用明确的 cohort CSV 与 SHA-256。建议后续主分析 valid-only，all-propositions 为敏感性分析；LLM claim 为主要复现队列，human claim 与 LLM sentence 分开报告。新拆分单元不能直接继承这些医生标签。
3. **固定 baseline 配置**：采用正文 R1-70B + 100 sentence facts、rerank、absolute_time、current admission、deduplicate=True；不按新方法测试结果逐次挑选 baseline。九个模型的相同 N100 sentence 配置均在 `research_baselines.json/csv` 按相同 valid-only 样本和患者 bootstrap 重评，可作为额外对照。
4. **完整性与公平比较**：默认缺失、重复、非法标签、范围外预测报错；明确记录覆盖和实际 ID。共同可用样本只能作为预先注明的敏感性分析。配对比较用同一患者 bootstrap 抽样，两方法必须覆盖同一队列。
5. **不确定性与数据泄漏**：后续研究使用 1,000 次患者 cluster bootstrap（100 名患者抽样，每名被抽中患者的全部命题随之重复），点估计仍是命题 micro。论文 item bootstrap 仅用于复现。当前仍是全数据描述性 benchmark，尚无训练/验证/测试划分；训练、调参与错误驱动方法开发前必须按 patient 分组冻结划分，避免同患者 BHC/EHR 或 sentence/claim 跨集合。

## 可复现入口与文件

在项目根目录、Conda `research-verifact` 环境运行：

```powershell
python -B scripts/reproduce_paper_results.py
python -B -m unittest discover -s tests -v
```

每次创建新 run，不覆盖历史结果。`manifest.json` 保存输入、代码、依赖、论文及输出 SHA-256；原始数据前后指纹检查结果在 manifest。任务说明和统一评价入口示例见 `tasks/002_reproduce_paper_results/README.md`。

`checks.json` 区分程序/关系检查、论文数值差异与未确认来源。已知数据缺陷仍保留；002 完成不会使 001 的 fail 变成 pass。
