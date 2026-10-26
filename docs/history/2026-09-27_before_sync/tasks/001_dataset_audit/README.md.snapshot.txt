# 001_dataset_audit：VeriFact-BHC v1.1.0 数据基础审计

## 目的和范围

为后续 baseline、错误分析、训练和实验设计建立可回查的数据基础。检查实际 release 的文件、字段、缺失、重复、主外键、标签分布、患者/住院覆盖、既有模型预测范围及官方说明差异。本任务不进行新方法实验、模型调用或重新医学标注。

输入为 `data/00_raw/verifact-bhc/1.1.0/` 与 `docs/sources/VeriFact.pdf`。原始目录只读；开头和结尾全量计算 SHA-256 确认运行期间内容未变。读取 CSV 时保留原始字符串和空值，不修改源文件。ID 的整数形式规范化仅用于派生索引；原来的 `123.0` 等外观仍可在原表回查。

## 环境与执行

使用根目录 `environment.yml` 定义的 Conda 环境。直接依赖固定为 DuckDB 1.5.5、pypdf 6.18.1 和 fonttools 4.65.0；fonttools 用于解析论文中嵌入的 CFF 字体编码。测试使用 Python 标准库 unittest。

```powershell
conda env update -f environment.yml
conda activate research-verifact
python -B scripts/audit_dataset.py
python -B -m unittest discover -s tests -v
```

不需要 GPU、外部模型 API 或访问网络。运行代码不依赖其他 Conda 环境中的包。首次安装依赖需要软件包源可用。

默认输出到下一个空闲的 `outputs/001_dataset_audit/run_XXX/`。指定目录示例：

```powershell
python -B scripts/audit_dataset.py --run-name run_review
```

已存在的 run 目录会被拒绝，不能覆盖历史输出。`--release`、`--paper`、`--output-root` 均支持相对项目根目录的路径；`--memory-limit` 默认 `2GB`，DuckDB 使用两线程且禁止磁盘临时溢写。程序会拒绝把输出写入 `data/00_raw` 或输入 release 内。

## 实现位置

入口是 `scripts/audit_dataset.py`。可复用逻辑位于 `src/verifact_research/audit/`：

- `common.py`：CSV 读取、ID 处理、多数票、内容哈希、字段画像及安全输出。
- `release.py`：文件校验清单、归档内容、患者 PDF 和论文证据位置。
- `cohort.py`：命题、医生标签、有效性、完整 BHC、原文位置、住院和 EHR。
- `ai.py`：Parquet 字段画像、完整性、预期实验组合重建、缺失预测与模型上下文可比性。
- `report.py`：从机器结果生成中文报告，避免手工抄写统计数字。
- `runner.py`：运行组织、输入输出指纹、检查状态和异常记录。

## 输出与字段约定

每个完整执行的 run 包含（包括发现数据检查失败的 run）：

- `report.md`：人读中文报告；区分已验证、官方定义、待确认。
- `audit.json`：主要统计、各表完整字段画像、原始说明证据、声明对照与检查。`schema_version=1.0`。
- `checks.json`：检查 ID、status、observed、expected、evidence。
- `manifest.json`：输入、论文、代码、配置与输出 SHA-256，实际依赖版本、Git 头与脏状态、命令、运行时间和状态。
- `run.log`：阶段日志；发生运行异常时也保留 traceback 与 manifest，不伪造完整报告。
- `file_inventory.csv`、`archive_members.csv`、`pdf_inventory.csv`：文件/归档/PDF 结构清单，不将归档展开到磁盘。
- `proposition_index.csv`：完整命题 ID、规范化患者/住院 ID、来源类型、文档键、GT、invalid、票数、文本/块哈希及唯一逐字位置。没有复制全部临床正文。
- `document_index.csv`：每份 BHC 的来源、字符数、来源块数、两类命题数和 sentence 覆盖情况。
- `patient_index.csv`、`ehr_note_index.csv`：患者范围、目标/其他住院记录及 note 元数据。EHR 的 `scope` 按 HADM_ID 定义，不冒充作者检索器的具体时间过滤实现。
- `label_distribution.csv`：全部及有效命题的三分类 GT 分布、医生一致性与定位统计。
- `annotation_anomalies.csv`、`validity_anomalies.csv`、`temporal_anomalies.csv`：标注链条、有效性逻辑、时间边界异常。
- `second_round_anomalies.csv`：第二轮医生个体票、决策字段和最终标签之间的矛盾，保留完整命题键及原值。
- `admission_metadata_conflicts.csv`、`admission_conflict_summary.csv`：propositions 与 admissions 之间的时间冲突，保留两边原值与影响命题。
- `duplicate_proposition_text_groups.csv`：重复文本的 SHA-256 和完整命题 ID，不把文本相同当作行重复。
- `model_metadata.csv`、`rater_configurations.csv`、`experiment_matrix.csv`：方便后续读取的小型元数据表。
- `expected_model_configurations.csv`：按照官方 matrix 适用范围展开的 model × matrix 组合。
- `model_configuration_coverage.csv`、`missing_verdict_keys.csv`、`unexpected_verdict_keys.csv`：逐组合与逐预测键的预期/实际比较。
- `model_coverage.csv`、`ai_stratum_coverage.csv`、`ai_label_distribution.csv`：模型、命题组和预测标签覆盖。
- `empty_reasons.csv`：空理由的完整预测键。
- `context_consistency.csv`：同一 proposition、相同检索参数、不同 Judge 的精确 payload 一致性汇总。
- `reference_admission_headers.csv`：从所有 reference 前 400 字符提取 header，并按 rater 的格式分类；仅对 absolute_time 的 ISO 日期分别与命题表和 admissions 对照。relative_time、score 的日期比较不适用，matches 字段为空；不会把 `Now` 误当日期冲突。
- `context_difference_examples.csv`：按稳定排序选择的前 100 个不一致配置组，仅用于回查，不作为抽样估计。
- `reference_reuse_distribution.csv`：一个精确 payload 被几个预测复用的分布。

空异常文件也保留表头。派生布尔值在 CSV 中写为 `True/False`，缺失派生位置为空；JSON 使用原生布尔与 null。CSV 所有字段画像保留 empty 与 whitespace-only 的区别；Parquet 另区分真正 NULL。

`document_key=subject_id:hadm_id:author_type` 是本任务派生键，只有在“一键对应唯一 BHC”检查通过时可直接使用。原文定位用原始 Unicode 字符索引，从 0 开始，end 不包含右端；多处匹配不强行指定位置，改写 claim 不生成推测性 span。

## 自动检查与测试

`pass` 表示检查通过；`warning` 表示实际异常/官方描述差异；`unverified` 表示当前资料不足；结构完整性 `fail` 或运行异常使程序以非零状态退出。缺失预测、空理由和正文时间边界等异常会报告，不填补、不删除，也不硬编码为“正常”。

关键标注流程字段互相矛盾同样触发 fail。检测到数据检查失败时，程序仍输出完整报告与机器结果，manifest 标为 `failed_checks`；这与无法完成审计的运行异常 `error` 不同。审计任务可以完成并明确交付数据缺陷，不通过降低检查要求消除失败。

患者/admission 身份连接错误属于结构性 fail；两张表重复保存的日期不一致单独作为 warning，报告保留双方值和影响范围。这样不会把日期分歧与外键损坏混为一谈，也不会通过自动改值消除原始差异。

测试涵盖：精确 ID 规范化及错误输入、三人各投一类、多处原文匹配、空值定义、清单重复和危险路径、输出不覆盖/不进入 raw、主键重复、rater 与 matrix 分层区别、缺失人工标注不可静默丢弃、人工 GT 及最终有效性逻辑被篡改后能检测。另用小型合成 Parquet 验证缺失预测、不同 Judge 上下文和空理由的检测，并防止将 relative_time/score 格式误报为绝对日期冲突。测试仅用合成数据。

正式审计对真实数据全量执行主外键、冗余元数据一致性、多数票/裁决关系、有效性 OR、来源定位、目标出院小结排除、模型/rater 对应、预期预测反连接和所有 reference 文本 SHA-256 检查。

## 证据范围和解释边界

本地官方 README 的统计声明与论文第 1、2、4、5、6 页相关描述分别记录。原始数据统计独立计算；论文中的“478 条三人完全不一致”不被用作计算公式或填补目标。若实际结果不同，原样报告。

哈希核验不证明临床真实性。PDF 成员和页数核验不证明其临床正文与 CSV 等价。reference 是模型输入，不是医生证据金标准；不同 reference_id 只证明精确文本不同，不直接证明医学内容不同。生成调用和源 Feather artifact 不属于本地 release，无法从成品验证全部生成过程与原始模型产物指纹。

## 完成状态

**已完成（2026-09-12）**：实现、15 项合成数据测试、真实 release 全量审计及重复性复查均已完成。

正式阅读入口为 [run_006 报告](../../outputs/001_dataset_audit/run_006/report.md)，与 `run_005` 的 32 个机器结果文件逐字节一致。完整验证记录见 [verification.json](../../outputs/001_dataset_audit/verification.json)。

94 项数据检查中，84 项通过、7 项需关注、2 项未验证、1 项失败。失败项为两条医生第二轮字段矛盾；已保留完整原值和发布的 human_gt。正式运行状态为 `failed_checks`，审计已完整执行，未通过改值消除异常。

后续使用范围和异常清单统一参见 [输出索引](../../outputs/001_dataset_audit/README.md)。001 本身没有开展 baseline 或建立患者划分；后续 [002](../002_reproduce_paper_results/README.md) 已完成发布预测重评分和统一评价，[003](../003_error_analysis/README.md) 已完成错误分析并冻结 20/40/40 患者分组。后续 [004](../004_event_alignment_pilot/README.md) 已完成首次三臂提示词 pilot 及修订独立复核；模型训练尚未开展，最终论文方法仍未确定。历史调试运行仅为过程记录，每次运行保留独立目录。
