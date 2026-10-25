# 002_reproduce_paper_results

> **现行导航（2026-09-27，项目已完成092）：**  [本任务成果入口](../../outputs/002_reproduce_paper_results/README.md)。 独立结论查[审计末尾](../../reviews/002_reproduce_paper_results.md)，不能把下方早期“待审”当最新状态。 [项目现状](../../docs/PROJECT_STATUS.md) · [任务索引](../../docs/TASK_INDEX.md) · [现行环境](../../docs/RUN_ENVIRONMENT.md)。下方正文保留原任务形成时状态、授权和命令；其中“当前/暂停/待运行/预算/不推送”仅适用于当时，不是当前待办。旧导航指纹复查使用[历史快照说明](../../docs/REPRODUCIBILITY.md#更早任务的严格重放)。

## 原任务阶段说明（历史）

本页固定002复算与长期评价口径；R1-70B是发布预测的历史参照。当前新实验暂用C48并保留A48对照，见[009入口](../../outputs/009_retrieval_baselines/README.md)。评价实现仍用002，不能把不同任务或模型的绝对分数当同期收益。

## 目标

以正式论文 `docs/sources/VeriFact.pdf`、VeriFact-BHC v1.1.0 和 001 的正式审计结果为依据，独立复算论文的核心实验结果，建立原作者 baseline 与后续新方法共用的评价实现。

## 范围与证据

- 复算医生间一致性、已有 VeriFact 预测与最终医生 GT 的一致性，以及模型、作者类型、命题粒度、事实粒度和检索配置分层。
- 核心指标为 Percent Agreement、Gwet's AC1、MCC；记录混淆矩阵、各类别性能、样本分母及置信区间口径。
- 先记录论文中的目标值，再从实际数据独立计算。正式论文、官方数据说明、固定版本作者代码、当前复算结果分别标记；无法获取或无法确认的来源明确记录。
- 作者公开代码只作为解释实验口径的证据，不直接运行其模型、检索服务或分析脚本。
- 原始数据和 001 的历史结果只读。所有筛选、缺失预测、invalid、标注流程异常、日期冲突均显式记录，不补标签或预测。

## 评价代码的长期约定

新方法和 baseline 使用同一套标签映射、指标函数及评价入口。预测通过 proposition_id 与固定样本清单、发布的 human_gt 对应；缺失、重复、非法标签和范围外预测不能静默丢弃。论文复现口径与后续公平比较口径由显式配置区分，并保存各自实际样本清单。

## 实现与运行

从项目根目录、Conda `research-verifact`（Python 3.11）环境运行：

```powershell
conda env update -f environment.yml
conda activate research-verifact
python -B scripts/reproduce_paper_results.py
python -B -m unittest discover -s tests -v
```

脚本每次建立新的 `outputs/002_reproduce_paper_results/run_XXX/`。不覆盖已有 run，不运行模型或调用推理 API；主要工作是读取发布预测、指标计算和 1,000 次 bootstrap。`--bootstrap` 可供开发时缩小迭代数，正式报告使用默认 1000；低迭代运行不能称为完成了论文 CI 复现。

核心代码：

| 文件 | 职责 |
| --- | --- |
| `src/verifact_research/evaluation/metrics.py` | 三分类 PA、AC1、MCC、混淆矩阵及各类性能；命题/患者 bootstrap |
| `src/verifact_research/evaluation/core.py` | 所有方法共用的严格 ID 对齐、评价和配对比较 |
| `src/verifact_research/evaluation/release.py` | 从原始 release 独立构建队列、配置和窄列预测；核对 001 |
| `src/verifact_research/evaluation/reproduction.py` | 本任务全量复算、筛选清单、结果与 manifest |
| `src/verifact_research/evaluation/diagnostics.py` | 预分析对比、模型增幅、实际数据上的独立库校验 |
| `src/verifact_research/evaluation/report.py` | 从计算结果生成中文报告 |
| `src/verifact_research/evaluation/cli.py` | 原 baseline / 新方法的公共 CSV 评价入口 |
| `scripts/verify_reproduction.py` | 两次完整运行逐字节核对、测试记录、公共 CLI 回放 |

审计包仅复用通用读取、完整性、ID 规范化等工具，不从 001 的汇总数字生成本次指标。命题与 GT、validity、matrix、rater、verdict、reference 均从官方文件读取；001 用于独立交叉检查及边界追踪。

## 统一评价协议

所有指标使用固定标签顺序 `Supported`、`Not Supported`、`Not Addressed`。PA 存储为 0–1 比例，报告展示百分比；AC1/MCC 不乘 100。混淆矩阵**行是 GT，列是预测**。各类零分母比例返回 JSON null / CSV 空值，不能当成 0；MCC 零分母按 sklearn 1.6.1 返回 0，并记录标记。

| 项目 | 论文复现 | 后续研究默认 |
| --- | --- | --- |
| GT | 发布的 human_gt，不重判 | 相同 |
| 标签空间 | 名义三分类 | 相同，三类性能必须报告 |
| invalid | 保留，另算 valid-only 敏感性分析 | valid-only 主分析，all 另报 |
| 点估计 | 每条 proposition 等权（micro） | 相同 |
| 队列 | release 各 author/proposition 分层 | 固定 cohort CSV，记录 SHA-256 和患者划分 |
| 缺失预测 | 显式 available；记录全部缺失键、分母和覆盖 | 默认报错；不得为某个方法自行缩小测试集 |
| CI | `paper_item`：命题 bootstrap，1000 次 | `research_patient`：患者 cluster bootstrap，1000 次 |
| 随机数 | `numpy.RandomState(i)`，i=0..999 | 相同种子定义；抽样对象不同 |
| 发布预测的历史参照baseline | 每个已发布配置分别重评分 | 正文 R1-70B、sentence facts N100、rerank、absolute_time、current admission、deduplicate=True |

后续主队列采用 LLM-written atomic claims（valid-only 3,441 条）；human-written atomic claims（5,624 条）及 LLM-written sentences（998 条）分别作为扩展评价。这里固定的是全 benchmark 描述性口径，**002 完成时尚未建立患者划分**。后续 003 已冻结探索／开发／保留测试分组，当前实验应复用 [003 的冻结清单与约定](../003_error_analysis/README.md)，不能让同患者的 BHC、EHR、sentence/claim 出现在不同集合；002 历史结果仍代表全 benchmark。

新任务若需要不同科学口径，应在其配置和队列中显式登记，并对新方法和 baseline 同步重评。不能为了匹配论文分数，修改标签、隐式忽略非法预测或另写指标。

`paper_item` 按固定作者实现区分排序：PA/AC1 先按 proposition_id 排序，MCC 使用输入 cohort 的行序；本任务提供的 cohort 保留 human_verdicts CSV 顺序。AC1 的单次 bootstrap 值按 irrCAC 默认五位小数处理。论文未明确写出排序，因此这些属于**公开实现证据**。排序会改变给定随机种子的有限次 CI，但不会改变点估计。

患者 bootstrap 抽取的是患者，抽到同一患者多次就完整重复其命题；点估计仍按 proposition 等权，并非患者分数的简单平均。方法差值采用同一批患者抽样（paired bootstrap），方向为候选方法减 baseline。

`cohorts.json` 中的 `sha256`、metrics 中的 `expected_cohort_sha256` / `evaluated_cohort_sha256` 指有序 `[proposition_id, subject_id, human_gt]` 序列的规范 JSON 哈希，用于检查评价对象和排序。CSV 文件全部字节的 SHA-256 另记在 manifest 中，两者不可混用。

## 公共入口用法

正式结果 run 编号以 [输出索引](../../outputs/002_reproduce_paper_results/README.md) 为准。以下以 `run_003` 为例。

重新评价已有 R1-70B baseline（研究默认指标口径、全 benchmark 队列；不是保留测试组的正式比较）：

```powershell
python -B scripts/evaluate_predictions.py --method-name R1-70B --cohort outputs/002_reproduce_paper_results/run_003/cohorts/llm_claim_valid_only.csv --predictions outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_llm_claim_valid_only.csv
```

重现论文口径时，使用 all cohort 和 all predictions，并明确参数：

```powershell
python -B scripts/evaluate_predictions.py --method-name R1-70B-paper --cohort outputs/002_reproduce_paper_results/run_003/cohorts/llm_claim_all.csv --predictions outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_llm_claim_all.csv --validity all --profile paper_item --missing available
```

评价新方法时，按 003 冻结分组构建实际开发／测试 cohort，同时选取同一 cohort 的 baseline 预测；再将 `--predictions` 指向新方法输出 CSV。不能仅替换预测文件而沿用上面全 benchmark 的样本范围。要求至少包含 `proposition_id,verdict` 两列，标签使用上述完整英文值。可参考已导出的真实 baseline 预测格式。ID 应与所选 cohort 完全一致；输出整份临床文档时，须先解决与既有标注 proposition 的评价对应关系。

若同时提供 `--baseline-predictions`，公共入口会输出 paired patient bootstrap 差值及 95% CI；要求两方法完整覆盖同一个 cohort。`--output-root` 可指定新研究任务自己的输出目录。默认写入 `outputs/002_reproduce_paper_results/evaluations/run_XXX/`，保留 cohort、标准化 predictions、metrics、manifest；不覆盖。

入口会从原始 release 再核对 cohort 的 patient、admission、作者类型、粒度、GT、invalid，拒绝替换 GT、未知 ID 和非法筛选。`--missing available` 只能显式用于探索性缺失分析，同时输出缺失 ID、实际分母、固定完整队列上 PA 的最好/最坏界；不能作为模型间正式比较的默认值。

## 输出结构

| 文件/目录 | 内容 |
| --- | --- |
| `report.md`, `summary.json` | 中文报告和机器汇总 |
| `manifest.json`, `checks.json` | 原始/来源/代码/输出指纹、依赖与检查状态 |
| `cohort_master.csv`, `cohorts.json`, `cohorts/` | GT、筛选/异常标记及明确队列 ID、分布和哈希 |
| `ai_metrics.csv/json` | 426 个实验组合；PA/AC1/MCC、CI、分母、混淆矩阵和 reference 长度（CSV）；完整各类指标（JSON） |
| `per_class_metrics.csv` | 1,278 个配置×类别的计数和 recall/precision/F1/specificity/NPV 点估计；未宣称复现补充表的逐类 CI |
| `clinician_metrics.csv`, `clinician_subset_membership.csv` | Table 1 的 16 个分层及其精确成员 |
| `paper_comparisons.csv/json` | 计算前记录的正式目标逐项比对；差异及未确认范围 |
| `missing_prediction_keys.csv` | 74 条缺失键，与 001 独立结果核对 |
| `common_available_metrics.csv`, `common_available_membership.csv` | 缺失配置下九模型共同 5,574 个 ID 的显式敏感性分析 |
| `sensitivity_metrics.csv` | 全配置 valid-only；端点上的时间异常排除和第一轮医生一致性分层 |
| `endpoint_input_comparisons.csv` | 端点同配置对 R1-70B 的精确 reference identity 对比 |
| `preliminary_contrasts.csv`, `preliminary_summary.csv` | N50 单因素检索/时间格式/住院范围对比；等权汇总不代表论文选参算法 |
| `model_size_reasoning_contrasts.csv` | p9 四组模型增幅的精确配对计数与展示取整诊断 |
| `mcc_ci_diagnostics.csv` | R1-70B 主配置的排序/validity 诊断与独立 sklearn、irrCAC 校验 |
| `research_baselines.csv/json` | 九模型 N100 sentence facts，三组队列，共 27 组 valid-only 患者 bootstrap baseline |
| `baseline_predictions/` | R1-70B 三组队列的 all / valid-only 实际预测，可直接用于公共入口 |
| `trivial_baseline.csv` | 始终预测 Supported 的对照，帮助判断类别失衡影响 |

本次输出未复制临床正文和完整检索 payload。按 ID 可回查原始文件；reference 不被当作医生 gold evidence。实际 reference 词数采用 Python `str.split()` 独立扫描，原始文本不写入中间文件。

## 验证、版本与证据限制

- 002 完成时的 30 项测试覆盖 001 逻辑及本次指标、真实库交叉验证、命题/患者抽样、配对差值、缺失、重复、非法标签和 GT 篡改防护。
- 实际 R1-70B 数据额外用 sklearn 1.6.1 独立重算每一次 MCC bootstrap，用 irrCAC 0.4.3 检查 AC1，不仅验证合成样例。
- 重复运行校验命令：

```powershell
python -B scripts/verify_reproduction.py --first outputs/002_reproduce_paper_results/run_002 --second outputs/002_reproduce_paper_results/run_003 --output outputs/002_reproduce_paper_results/verification_new.json
```

校验文件已存在时需更换文件名；不会覆盖旧验证。校验同时用公共 CLI 重评分 baseline，要求两种 profile 与全量 runner 的完整结果逐字段相同，并检查相同方法的配对差值及 CI 全为 0。

原始文件在运行前后逐文件哈希；必须匹配官方 SHA256SUMS 以及 001 正式运行使用的字节。固定作者代码也核对下载清单的 SHA256。已知数据问题和论文数值差异保留为 warning/unverified；程序错误、关系破坏、文件完整性失败返回非零。正常完成但数值存在差异时 manifest 为 `completed_with_differences`，不把已知差异误当程序崩溃。

已知实现限制：全量 `reproduce_paper_results.py` 使用仓库外的 `--output-root` 时，路径展示的 `run.relative_to(ROOT)` 会报错，目前未修复。重跑本任务请使用默认输出目录或仓库内目录；公共 `evaluate_predictions.py` 不受这一问题影响。此限制来自 [002 审计记录](../../reviews/002_reproduce_paper_results.md)，不影响已有正式结果。

核心版本固定于 `environment.yml`；irrCAC 0.4.3 要求 scipy 1.12.0，因此按其依赖使用该版本。作者代码位于 `docs/sources/verifact_upstream_f115d36cb65f/`，连同原 LICENSE 和下载清单保存。`scripts/fetch_reproduction_sources.py` 仅在该固定资料目录尚不存在时下载，不是日常重跑依赖；正式复算不联网。

正式附录未取得，不宣称完成 Table S3 等所有补充结果的逐值复现。论文区间差异和 p9 展示精度诊断明确区分验证与推测；详见报告。源码/文档更新不回写历史 run 和 manifest。

## 当前状态

已完成（2026-09-13）。正式结果为 `run_003`，与 `run_002` 的 37 个机器文件逐字节相同；30 项测试和公共 CLI 两种口径的回放验证均通过。最终校验记录见 [verification_final.json](../../outputs/002_reproduce_paper_results/verification_final.json)。具体复现差异和未确认事项见报告，不表示所有论文数字及补充材料均已复现。
