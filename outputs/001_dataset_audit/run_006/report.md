> 阅读镜像：已省略6行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。

# VeriFact-BHC v1.1.0 数据审计报告

运行：`run_006`。任务：`001_dataset_audit`。所有统计均由本次运行从本地 release 独立计算；没有运行新模型、重新标注或修改原始数据。

**审计状态：通过 84 项，需关注 7 项，未验证 2 项，失败 1 项。**

证据标记：**[已验证]** 来自实际文件及自动检查；**[官方定义]** 来自本地官方 README 或论文；**[待确认]** 表示当前文件不足以验证。定义正确不等于实现过程或临床事实已经被验证。

本次需优先关注：第二轮医生投票与决策字段的矛盾、命题表与 admissions 表的时间冲突、实际缺失预测、human sentence 未进入 AI 实验矩阵、同参数下 Judge 输入并非总相同，以及论文/README 的描述差异。详见第 3、5—8 节；本报告不自动修正这些原始数据差异。审计完成表示已检查并记录问题，不代表所有数据检查通过。

## 1. 数据实际包含什么

**[已验证]** release 中有 25 个文件；SHA256SUMS 列出的 24 个文件全部逐字节计算了 SHA-256。清单自身单独记录哈希，不能自我包含。开始与结束再次读取全部输入并比较哈希，结果见 `release.raw_unchanged` 检查。

| 对象 | 数量 |
| --- | --- |
| 患者 | 100 |
| 目标住院 | 100 |
| 完整 BHC | 200 |
| proposition | 13070 |
| 参考 EHR note | 4787 |
| 参考 EHR 中不同 admission | 125 |
| VeriFact verdict 行 | 1437100 |
| 不同 reference payload | 400597 |
| Judge model | 9 |
| rater configuration | 174 |
| experiment matrix 行 | 54 |
| 允许的 model × matrix 行组合 | 426 |

CSV/GZIP 文件按原始字符串读取，不把空字符串、数字形式的 ID 或 `False` 自动改成缺失。CSV 数字外观如 `183959.0` 的标识仅在连接索引中转为整数形式；原表未重写。Parquet 的真正 NULL 与空字符串分别计数。所有字段的类型、缺失、不同值数量和文本长度见第 10 节及 `audit.json.schemas`。

## 2. 各层对象与连接关系

```text
patient subject_id
  ├─ target admission hadm_id（admissions）
  ├─ reference EHR notes（含该患者的其他住院，note 以 ROW_ID 标识）
  └─ human / LLM BHC 各一份
       └─ parent_text_chunk（来源原文块）
            └─ sentence / claim 两套 propositions（proposition_id）
                 ├─ clinician votes → human_gt
                 ├─ proposition validity（与事实支持标签不同）
                 └─ AI verdict（proposition_id + rater_alias）
                      ├─ rater_alias → model + retrieval configuration
                      └─ reference_id → 精确模型输入 reference
```

**[已验证]** 三个 proposition CSV 的 ID 集、文本、作者类型和命题类型逐行核对；主表的 `proposition_id` 唯一。AI verdict 以 `(proposition_id, rater_alias)` 为键，引用命题、rater、model 和 reference 四张表。所有关系的实际通过/失败状态列在 `checks.json`，异常不能靠 inner join 静默丢弃。

`human-written` 是 BHC 作者类型；`human_gt` 是核验后的最终医生标签；两者不可混用。`proposition_type` 是待核验对象粒度，`fact_type` 是 EHR 检索证据粒度。`row_id` 是 BHC 来源记录的元信息，不能当作 proposition ID 或证据外键；LLM 行该字段可能为空。原始表没有正式 document ID，`document_index.csv` 的 `subject:hadm:author` 是本任务生成的索引，且已检查每个索引对应唯一 BHC。

实际 source row ID 覆盖为 `{'human': {'nonempty_propositions': 8625, 'unique_nonempty': 100}, 'llm': {'nonempty_propositions': 0, 'unique_nonempty': 0}}`，其中 nonempty_propositions 是非空行数，unique_nonempty 是不同非空值数。

本 release 未提供逐条医生认可的 gold evidence note ID/span，也未提供统一的 claim→sentence 外键。模型的 reference 是检索结果，不是医生标准证据。

## 3. 命题、医生 ground truth 与有效性

**[已验证]** 四组命题分布如下，`invalid` 使用最终字段而非 draft。

| BHC 作者 | 命题类型 | 总数 | S | NS | NA | invalid |
| --- | --- | --- | --- | --- | --- | --- |
| human | claim | 5648 | 3779 | 589 | 1280 | 24 |
| human | sentence | 2977 | 1617 | 429 | 931 | 426 |
| llm | claim | 3447 | 3274 | 107 | 66 | 6 |
| llm | sentence | 998 | 947 | 31 | 20 | 0 |

S=`Supported`，NS=`Not Supported`，NA=`Not Addressed`。**[官方定义]** S 要求 EHR 充分支持，NS 包含不充分支持或矛盾，NA 表示未涉及；这些标签基于可用 EHR，不能当作患者真实世界中事件发生与否的绝对证明。

**[已验证]** 保留 `invalid=False` 时的标签分布如下。审计同时给出两种口径，不替后续实验隐式过滤。

| BHC 作者 | 命题类型 | 有效 S | 有效 NS | 有效 NA |
| --- | --- | --- | --- | --- |
| human | claim | 3766 | 586 | 1272 |
| human | sentence | 1495 | 395 | 661 |
| llm | claim | 3269 | 107 | 65 |
| llm | sentence | 947 | 31 | 20 |

总体 S=9617，NS=1156，NA=2297。各组类别不均衡程度不同；后续不能只报告总体一致率，也不能把 13,070 行视作独立患者样本。

### 3.1 医生标签怎样形成

**[已验证]** 第一轮共有 25 位不同医生代号，每条 3 票；三票一致 8743 条，两票一致 3860 条，三人各投一类 467 条。最后一类的 `round1_num_raters_agree` 存为 0，不是 1。

本审计独立重算多数票、同意人数，并检验最终标签：有多数票时 `human_gt=round1_majority_vote`；三人各投一类时以实际保存的 `adjudicated_verdict` 核对。后续医生代号为 Z1, Z2；`adjudicated_verdict` 非空 467 行。第二轮决策计数：`{'': 12603, 'Disagree': 231, 'Agree': 236}`。这描述实际字段填法，不把“字段名含 adjudicated”自动解释为所有这些行都经历了同一种第三轮流程。

**[官方定义]** 论文第 4 页说明：第一轮无多数票的命题交给两名新医生；两人一致则采纳，不一致则通过讨论及第三名医生形成最终共识。

**[已验证／实际异常]** 按保存的 `verdict4/5` 重算，第二轮两票相同 234 条、不同 233 条。以下 2 条未能通过“个体票—第二轮决策—最终标签”一致性检查，完整键见 `second_round_anomalies.csv`：

| 命题 ID | 作者 | 类型 | 医生 4 | 医生 5 | 第二轮字段 | 最终裁决 | human_gt |
| --- | --- | --- | --- | --- | --- | --- | --- |

最终标签与裁决字段一致，并不能消除中间流程记录的矛盾。**[待确认]** 当前文件无法说明这些字段为何不同，也不能据此重判其临床标签。本任务保留发布的 human_gt，同时让关键流程检查返回 fail，避免后续把全部标注链条视为已验证无异常。

| 评论字段 | 非空行数 |
| --- | --- |
| comment1 | 0 |
| comment2 | 0 |
| comment3 | 6 |
| comment4 | 427 |
| comment5 | 8 |
| adjudicated_comment | 231 |

评论不是每条都有；没有完整、统一的医生理由 ground truth。`uncertain_flag`、个体票和评论可用于后续分析标注分歧。

下表是每条命题的 3 个医生配对中标签相同的比例，再在组内平均，**不是三人全体一致的比例**：

| 作者 | 类型 | 配对一致率 | 三票一致行数 | 至少一票 uncertain 的行数 |
| --- | --- | --- | --- | --- |
| human | claim | 0.7329 | 3501 | 436 |
| human | sentence | 0.6695 | 1587 | 585 |
| llm | claim | 0.8853 | 2877 | 105 |
| llm | sentence | 0.8470 | 778 | 34 |

### 3.2 有效性与命题质量

**[已验证]** `invalid=True` 共 456 条，且等于最终 imperative/interrogative/incomplete/vague 四字段的 OR；四种原因可重叠，不能直接相加作为无效总数。最终与 draft 的差异已计算：`{'imperative': 449, 'interrogative': 59, 'incomplete': 2023, 'vague': 5130}`。

| 字段 | True 行数 |
| --- | --- |
| invalid | 456 |
| imperative | 43 |
| interrogative | 42 |
| incomplete | 354 |
| vague | 119 |
| imperative_draft | 486 |
| interrogative_draft | 89 |
| incomplete_draft | 2377 |
| vague_draft | 5249 |

无效命题仍保留医生标签，也未被 AI 结果统一排除，见第 6 节。若后续训练/评价只取有效命题，必须显式保存筛选规则及分母；不能直接与未过滤口径混比。

## 4. BHC、来源块、重复与原文定位

**[已验证]** 200 份 BHC 对应 1311 个按文档区分的来源块。`parent_text_chunk` 均检查是否为 BHC 的逐字子串；sentence 是否能逐字匹配、claim 是否改写以及多次匹配数如下：

| 作者 | 类型 | 找不到逐字匹配 | 唯一匹配 | 多处匹配 |
| --- | --- | --- | --- | --- |
| human | claim | 5553 | 95 | 0 |
| human | sentence | 0 | 2901 | 76 |
| llm | claim | 3410 | 37 | 0 |
| llm | sentence | 0 | 998 | 0 |

所有位置使用原始 Unicode 字符索引（从 0 开始，右端不含），不是 token 或字节偏移。`unique_text_start/end_exclusive` 仅对唯一匹配给值；多处匹配不强行选择第一处。对 sentence 做了全部匹配位置并集的非空白字符覆盖检查，但这不等于已解决重复句子的正确定位。没有为改写的 claim 发明精确 span。

命题文本只有 12650 种，出现 420 个重复文本额外行；跨患者重复文本组为 190。文本不是连接主键。同一句可能在两种粒度、两份文档或不同患者中出现。`duplicate_proposition_text_groups.csv` 给出哈希、涉及人数和完整 ID 列表，方便分清重复记录与合法重复陈述。

**[官方定义/待确认]** 正文将 BHC 分解概括为分句或原子命题提取；实际表保存了中间来源块。仅从 release 的成品不能重现作者生成时的全部切分调用、随机性或证明切分忠实无损。重新定义命题不会自动继承原命题的医生标签。

## 5. 患者、admission、参考 EHR 与时间

**[已验证]** `admissions.csv.gz` 包含 100 个目标住院；参考 EHR 覆盖 125 个 admission。其中目标住院 note 3848 条，其他住院 note 939 条；17 名患者有其他住院记录。其他 admission ID 共 25 个，列于 `audit.json`；其完整 ADMISSIONS 行不在这个 release 的 admissions 表中。

因此，以 `HADM_ID` 将 EHR inner join 到 admissions 会丢失其他住院记录。患者级证据池先按 `SUBJECT_ID` 关联；需要本次住院范围时，再按预先声明的规则筛选。

### 5.1 两张表的住院时间并不完全一致

**[已验证]** 患者和 admission 身份连接单独检查；重复保存的时间字段另作比较。发现以下实际冲突，原始两套值均保留在派生索引中，没有覆盖或默认修复：

| 患者 | 住院 | 字段 | 命题表值 | admissions 值 | 影响命题数 | 命题表减 admissions（秒） |
| --- | --- | --- | --- | --- | --- | --- |
| 71676 | 124971 | DISCHTIME | 2200-01-22 12:30:00 | 2200-01-24 12:30:00 | 89 | -172800.0000 |
| 98790 | 187987 | DISCHTIME | 2200-10-24 15:43:00 | 2200-10-25 15:43:00 | 108 | -86400.0000 |

逐条受影响命题在 `admission_metadata_conflicts.csv`；合并同一冲突后见 `admission_conflict_summary.csv`。**[待确认]** 当前 release 无法解释或裁定哪套时间正确。下文 EHR 时间边界统计明确采用 admissions 的时间作为比较基准，这是一种报告口径，不是临床真实性裁决。Judge 实际收到的日期另外从 payload 读取，见第 7 节。

### 5.2 EHR 内容与时间字段

| note 类别 | 条数 |
| --- | --- |
| Case Management | 14 |
| Consult | 1 |
| Discharge summary | 26 |
| ECG | 306 |
| Echo | 71 |
| General | 91 |
| Nursing | 1228 |
| Nursing/other | 12 |
| Nutrition | 92 |
| Physician | 1223 |
| Radiology | 1134 |
| Rehab Services | 81 |
| Respiratory | 471 |
| Social Work | 37 |

**[已验证]** 排除的是目标住院的最终出院小结；实际仍存在历史出院小结，其范围计数为 `{'other': 26}`。已检查 human BHC 来源 note ID 不与 reference EHR note ID 重叠，并检查目标住院内没有 Discharge summary。

原始 EHR 有 4684 种不同 TEXT，103 个重复文本额外行。相同正文不等于相同 note（ID、记录时间等可能不同），本任务未删除。

| 按患者统计 | 最小 | 中位数 | P95 | 最大 |
| --- | --- | --- | --- | --- |
| ehr_notes | 10 | 25.0000 | 203.1000 | 314 |
| ehr_characters | 22900 | 70287.0000 | 607482.8000 | 931897 |
| propositions | 36 | 113.0000 | 221.2500 | 422 |

**[已验证]** 时间异常/边界统计：`{'CHARTTIME:before_target_admission': 108, 'CHARTTIME:after_target_discharge': 12, 'STORETIME:after_target_discharge': 17, 'CHARTDATE:chartdate_differs_from_charttime_date': 61, 'STORETIME:before_target_admission': 4}`。全部涉及的 note、字段、时间及秒数差异在 `temporal_anomalies.csv`。CHARTDATE 是日期，CHARTTIME 是事件/记录时间字段，STORETIME 是存储时间字段，不可互相替代。晚于目标出院时间的条目不被自动删除，也不直接断言是错误或未来信息泄漏。

**[待确认]** 仅凭 `reference_only_admission=True` 不能确定作者检索器实际采用 HADM_ID、自然日范围还是精确时刻；本任务用 HADM_ID 计算“目标/其他住院”，另算自然日是否覆盖，不能把它宣称为复现了原检索 SQL。生产场景的“当时已经可见的信息”需要另行定义时间可用性规则。

参考 PDF 的成员名单、患者覆盖、可解析性和页数均已检查，见 `pdf_inventory.csv`。**PDF 与 CSV 全文的临床内容等价性没有自动证明**；不因都能打开就声称两者逐项完全一致。

## 6. 已有 VeriFact AI 覆盖了哪些样本

**[已验证]** 共 1437100 行预测，覆盖 10093 个不同 proposition。按作者与命题类型分：

| 作者 | 类型 | 全部命题 | 有 AI 命题 | AI 行数 | 无效命题 | 有 AI 的无效命题 |
| --- | --- | --- | --- | --- | --- | --- |
| human | claim | 5648 | 5648 | 711574 | 24 | 24 |
| human | sentence | 2977 | 0 | 0 | 426 | 0 |
| llm | claim | 3447 | 3447 | 599778 | 6 | 6 |
| llm | sentence | 998 | 998 | 125748 | 0 | 0 |

human sentence 整组不在当前实验矩阵中。它们没有预测不等于推理失败，也不能归因为 invalid。其他组的无效命题仍可能有预测。

### 6.1 模型、rater、matrix 不是同一种对象

| 模型 | 预测行 | 不同命题 | rater 数 | 空理由 | 空 reasoning_chain |
| --- | --- | --- | --- | --- | --- |
| Gemma-3-12B | 141302 | 10093 | 14 | 0 | 141302 |
| Gemma-3-27B | 141302 | 10093 | 14 | 0 | 141302 |
| Llama-70B | 182666 | 10093 | 26 | 0 | 182666 |
| Llama-8B | 182666 | 10093 | 26 | 0 | 182666 |
| Qwen-3-30B-A3B-Instruct | 141302 | 10093 | 14 | 1 | 141302 |
| Qwen-3-30B-A3B-Thinking | 141228 | 10093 | 14 | 0 | 0 |
| Qwen-3-32B | 141302 | 10093 | 14 | 0 | 141302 |
| R1-70B | 182666 | 10093 | 26 | 0 | 0 |
| R1-8B | 182666 | 10093 | 26 | 0 | 0 |

**[官方定义且已按文件核对]** 每个模型应覆盖 42 个 main matrix 行；4 个 Llama/R1 模型另外覆盖 12 个 preliminary 行。matrix 共 54 行，按角色计数 `{'main': 42, 'preliminary_sensitivity': 12}`。展开到模型后有 426 个组合。

一个 matrix 行包含 author_type、proposition_type 和检索设置；一个 rater_alias 表示 model 与检索设置，不含 BHC 作者和 proposition 类型。因此同一个 rater 可出现在多个 matrix 行中，174 个 rater 不应与 426 个组合混同。

实际参数取值：

| 参数 | 实际取值 |
| --- | --- |
| fact_type | claim, sentence |
| retrieval_method | dense, hybrid, rerank, sparse |
| top_n | 10, 100, 125, 150, 25, 5, 50, 75 |
| reference_format | absolute_time, relative_time, score |
| reference_only_admission | False, True |
| deduplicate_text | True |

精确模型名称、tokenizer、是否 reasoning、结构化输出模型和原始 artifact 信息完整保存于 `model_metadata.csv`。不只按简写 R1-70B 等猜具体模型版本。完整 rater 和 matrix 另存为同名 CSV。

### 6.2 缺失预测是如何独立发现的

按 matrix 的作者/命题类型选取 propositions，再按官方模型适用范围解析到 rater，得到 **1437174** 个预期 `(proposition_id, rater_alias, model)` 组合；逐键与实际 verdicts 比较，得到缺失 **74** 行、范围外 **0** 行。

| 模型 | rater | 作者 | 类型 | 应有 | 实际 | 缺失 |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen-3-30B-A3B-Thinking | v1.1.0-rater-048 | human | claim | 5648 | 5574 | 74 |

`missing_verdict_keys.csv` 保存每条缺失的完整 key、患者、GT 和 invalid 状态；`model_configuration_coverage.csv` 保存全部允许组合的预期、实际与缺失数量。两者均由本审计独立生成；README 提到的官方覆盖文件在本地 release 中不存在。

另有 1 条空 reason，完整 key 在 `empty_reasons.csv`。README 说明保留过一个 Qwen Instruct 空理由例外；实际数量与模型分别列出，不补写理由。

## 7. Reference payload 与模型间可比性

**[已验证]** 400597 个 reference_id 全量重新计算 `SHA256(reference.encode('utf-8'))`；同时检查 ID 唯一、每个 verdict 都能找到 payload、每个 payload 都被引用。reference 字符长度统计为 `{'min_characters': 282, 'median_characters': 11704.0, 'max_characters': 41352, 'mean_characters': 12204.621038100635}`。同一 payload 可被多个 verdict 复用，具体频数见 `reference_reuse_distribution.csv`。

把同一 proposition、同一组检索参数、不同模型的输入并排比较，182666 个多模型比较组中有 **112821** 组使用了不止一个精确 payload。按配置的完整汇总在 `context_consistency.csv`，100 个确定性例子在 `context_difference_examples.csv`。

**重要边界：**ID 不同意味着精确文本不同，可能只是空白、排序、时间/类别元信息，也可能是内容差异；本任务没有将这些差异全量分类。因此不能直接说所有这些组的医学证据不同，也不能只看到“配置相同”就认为 Judge 比较控制了输入上下文。

`reason`、`reasoning_chain`、`reasoning_final_answer` 属于模型输出，不能当成医生解释的 ground truth。参考上下文内的编号是局部编号，不是原始 note 的 ROW_ID；发布文件没有逐条结构化的 evidence span 金标准。

### 7.1 Judge 实际收到的住院时间

从每个 payload 前 400 个字符提取 `Hospital Admission Start/End`，连接到对应患者及 rater 的 `reference_format`。仅对 `absolute_time` 解析 ISO 日期并比较两套元数据；相对时间格式中的 `Now`、`… days … hours ago` 不与绝对日期字符串比较，score 格式也不要求具有住院时间 header。比较不适用时，机器结果中的 matches 字段为 null/空值。

| reference 格式 | 预测行 | 绝对时间已比较行 | 与 admissions 不一致行 | 与命题表不一致行 |
| --- | --- | --- | --- | --- |
| absolute_time | 1381948 | 1381948 | 0 | 49866 |
| relative_time | 27576 | 0 | 0 | 0 |
| score | 27576 | 0 | 0 | 0 |

下表列出绝对时间 header 与任一元数据来源不一致的组；完整结果在 `reference_admission_headers.csv`。这能说明模型实际收到哪个值，不能证明其临床真实性。相对时间的舍入规则及其精确基准尚未重现。

| 患者 | 命题表出院 | admissions 出院 | Judge header 出院 | 与 admissions 一致 | 与命题表一致 | 不同 payload | 预测行 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 71676 | 2200-01-22 12:30:00 | 2200-01-24 12:30:00 | 2200-01-24 12:30:00 | True | False | 2182 | 9524 |
| 98790 | 2200-10-24 15:43:00 | 2200-10-25 15:43:00 | 2200-10-25 15:43:00 | True | False | 3467 | 11512 |

## 8. 官方说法与实际结果的核对

下面每行的 expected 来自声明，observed 来自独立数据审计。来源证据、PDF 页码与短摘录在 `audit.json.sources`，原始 README/PDF 哈希在 manifest 中。

| 官方说法 | 来源 | 声称 | 实际 | 状态 |
| --- | --- | --- | --- | --- |
| 患者数 | README; PDF p1 | 100 | 100 | 一致 |
| proposition 总数 | README; PDF p5 | 13070 | 13070 | 一致 |
| LLM-written propositions | PDF p5 | 4445 | 4445 | 一致 |
| human-written propositions | PDF p5 | 8625 | 8625 | 一致 |
| atomic claim propositions | PDF p5 | 9095 | 9095 | 一致 |
| sentence propositions | PDF p5 | 3975 | 3975 | 一致 |
| 发布的 AI annotations | README | 1437100 | 1437100 | 一致 |
| 有 AI 结果的命题 | README | 10093 | 10093 | 一致 |
| Judge 模型数 | README | 9 | 9 | 一致 |
| matrix 总行数 | README | 54 | 54 | 一致 |
| 允许的 model/configuration 组合 | README | 426 | 426 | 一致 |
| main matrix 行数 | README | 42 | 42 | 一致 |
| preliminary matrix 行数 | README | 12 | 12 | 一致 |
| 第一轮三人完全不一致命题 | PDF p5 | 478 | 467 | 不一致 |
| 空 AI reason 例外数量 | README verdict schema | 1 | 1 | 一致 |
| human_claim 医生配对一致率(%) | PDF p6 Table 1 | 73.3000 | 73.3000 | 一致 |
| human_sentence 医生配对一致率(%) | PDF p6 Table 1 | 66.9000 | 66.9000 | 一致 |
| llm_claim 医生配对一致率(%) | PDF p6 Table 1 | 88.5000 | 88.5000 | 一致 |
| llm_sentence 医生配对一致率(%) | PDF p6 Table 1 | 84.7000 | 84.7000 | 一致 |

README 提到而实际不存在的文件：`['verifact-bhc-croissant.jsonld', 'verifact/coverage.csv', 'verifact/missing_verdict_keys.csv']`。它们也不在当前 SHA256SUMS 的应有列表里时，只能确认“本地 release 与其说明不一致”；不能自行推断用户漏下了文件，或某次作者构建失败。

论文 PDF 第 5 页写第一轮三人完全不一致为 478 条；本地文件按三票重算为 467 条。两者差异未能由当前 release 解释，不自行归因为过滤、版本修订或排版错误。

## 9. 对后续科研的适用性与限制

- **Baseline：**主外键和最终 GT 的多数票/裁决来源可核对，可建立明确分母的复算；第二轮流程异常命题须单列，不把其标签自动改掉。human sentence 无现成 AI 结果、缺失预测和 invalid 筛选必须明确处理。
- **错误分析：**可以回到原文、医生分歧、模型输入及输出；模型 reference 不是 gold evidence，没有理由时不能编造医生理由。先辨别命题质量、证据覆盖、Judge 判断和标注分歧。
- **训练：**只有已有 proposition 的标签可直接使用；改写或重新拆分后的单元需要新的评价对应。模型输出不是新增人工标注，模型原训练语料是否含 MIMIC 或此任务内容也未由 release 证明。
- **实验划分：**以患者为分组单位，同一患者的两种作者、两种粒度、重复内容和全部 EHR 保持在同一分区。这里没有替研究者创建 train/dev/test；官方表没有提供可直接沿用的这类划分。
- **文档级目标：**完整 BHC 与命题之间的联系可用，但多处匹配及 claim 改写妨碍直接定位；按命题算对多少与一篇文档中定位对多少问题不是同一个指标。
- **时间和公平比较：**先冻结可用 EHR 范围、事实粒度、证据预算和实际 payload；相同配置名称不保证相同输入文本。
- **溯源：**哈希只能证明这次输入与清单的一致性及运行期间未变，不能证明原始患者事件真实、标注正确、模型调用真实执行过或 PDF/CSV 内容完全等价。

## 10. 全部主要表的字段与缺失情况

CSV 的 NULL 为 0 是读取定义，不意味着所有字段有信息；应同时看空串和纯空白计数。Parquet 不同值计数对 UTF-8 文本先做 SHA-256，避免超长推理文本占用过大内存；这是基于密码学哈希的内容去重，非近似基数算法，仍依赖 SHA-256 无碰撞假设。


### propositions（13070 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| proposition_id | CSV string (uncoerced) | 0 | 0 | 0 | 13070 | 36 |
| text | CSV string (uncoerced) | 0 | 0 | 0 | 12650 | 400 |
| author_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| proposition_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 8 |
| parent_text_chunk | CSV string (uncoerced) | 0 | 0 | 0 | 1307 | 735 |
| brief_hospital_course | CSV string (uncoerced) | 0 | 0 | 0 | 200 | 7623 |
| subject_id | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 5 |
| row_id | CSV string (uncoerced) | 0 | 4445 | 0 | 101 | 7 |
| hadm_id | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 6 |
| admitdate | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 10 |
| admittime | CSV string (uncoerced) | 0 | 0 | 0 | 94 | 8 |
| dischargedate | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 10 |
| dischargetime | CSV string (uncoerced) | 0 | 0 | 0 | 78 | 8 |

### human_verdicts（13070 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| proposition_id | CSV string (uncoerced) | 0 | 0 | 0 | 13070 | 36 |
| text | CSV string (uncoerced) | 0 | 0 | 0 | 12650 | 400 |
| author_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| proposition_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 8 |
| rater1 | CSV string (uncoerced) | 0 | 0 | 0 | 20 | 1 |
| rater2 | CSV string (uncoerced) | 0 | 0 | 0 | 23 | 1 |
| rater3 | CSV string (uncoerced) | 0 | 0 | 0 | 22 | 1 |
| verdict1 | CSV string (uncoerced) | 0 | 0 | 0 | 3 | 13 |
| verdict2 | CSV string (uncoerced) | 0 | 0 | 0 | 3 | 13 |
| verdict3 | CSV string (uncoerced) | 0 | 0 | 0 | 3 | 13 |
| uncertain_flag1 | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| uncertain_flag2 | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| uncertain_flag3 | CSV string (uncoerced) | 0 | 1 | 0 | 3 | 5 |
| comment1 | CSV string (uncoerced) | 0 | 13070 | 0 | 1 | 0 |
| comment2 | CSV string (uncoerced) | 0 | 13070 | 0 | 1 | 0 |
| comment3 | CSV string (uncoerced) | 0 | 13064 | 0 | 7 | 62 |
| round1_num_raters_agree | CSV string (uncoerced) | 0 | 0 | 0 | 3 | 1 |
| round1_majority_vote | CSV string (uncoerced) | 0 | 467 | 0 | 4 | 13 |
| rater4 | CSV string (uncoerced) | 0 | 12603 | 0 | 2 | 2 |
| rater5 | CSV string (uncoerced) | 0 | 12603 | 0 | 2 | 2 |
| verdict4 | CSV string (uncoerced) | 0 | 12603 | 0 | 4 | 13 |
| verdict5 | CSV string (uncoerced) | 0 | 12603 | 0 | 4 | 13 |
| comment4 | CSV string (uncoerced) | 0 | 12643 | 0 | 353 | 998 |
| comment5 | CSV string (uncoerced) | 0 | 13062 | 0 | 9 | 272 |
| round2_decision | CSV string (uncoerced) | 0 | 12603 | 0 | 3 | 8 |
| adjudicated_verdict | CSV string (uncoerced) | 0 | 12603 | 0 | 4 | 13 |
| adjudicated_comment | CSV string (uncoerced) | 0 | 12839 | 0 | 197 | 622 |
| human_gt | CSV string (uncoerced) | 0 | 0 | 0 | 3 | 13 |

### proposition_validity（13070 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| proposition_id | CSV string (uncoerced) | 0 | 0 | 0 | 13070 | 36 |
| text | CSV string (uncoerced) | 0 | 0 | 0 | 12650 | 400 |
| author_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| proposition_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 8 |
| invalid | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| imperative | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| interrogative | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| incomplete | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| vague | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| imperative_draft | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| interrogative_draft | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| incomplete_draft | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| vague_draft | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |

### ehr_noteevents（4787 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| ROW_ID | CSV string (uncoerced) | 0 | 0 | 0 | 4787 | 7 |
| SUBJECT_ID | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 5 |
| HADM_ID | CSV string (uncoerced) | 0 | 0 | 0 | 125 | 8 |
| CHARTDATE | CSV string (uncoerced) | 0 | 0 | 0 | 822 | 10 |
| CHARTTIME | CSV string (uncoerced) | 0 | 403 | 0 | 3583 | 19 |
| STORETIME | CSV string (uncoerced) | 0 | 1537 | 0 | 3251 | 19 |
| CATEGORY | CSV string (uncoerced) | 0 | 0 | 0 | 14 | 17 |
| DESCRIPTION | CSV string (uncoerced) | 0 | 0 | 0 | 234 | 65 |
| CGID | CSV string (uncoerced) | 0 | 1537 | 0 | 637 | 7 |
| ISERROR | CSV string (uncoerced) | 0 | 4787 | 0 | 1 | 0 |
| TEXT | CSV string (uncoerced) | 0 | 0 | 0 | 4684 | 21486 |

### admissions（100 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| ROW_ID | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 5 |
| SUBJECT_ID | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 5 |
| HADM_ID | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 6 |
| ADMITTIME | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 19 |
| DISCHTIME | CSV string (uncoerced) | 0 | 0 | 0 | 100 | 19 |
| DEATHTIME | CSV string (uncoerced) | 0 | 92 | 0 | 9 | 19 |
| ADMISSION_TYPE | CSV string (uncoerced) | 0 | 0 | 0 | 3 | 9 |
| ADMISSION_LOCATION | CSV string (uncoerced) | 0 | 0 | 0 | 5 | 25 |
| DISCHARGE_LOCATION | CSV string (uncoerced) | 0 | 0 | 0 | 11 | 25 |
| INSURANCE | CSV string (uncoerced) | 0 | 0 | 0 | 4 | 10 |
| LANGUAGE | CSV string (uncoerced) | 0 | 0 | 0 | 8 | 4 |
| RELIGION | CSV string (uncoerced) | 0 | 0 | 0 | 12 | 19 |
| MARITAL_STATUS | CSV string (uncoerced) | 0 | 4 | 0 | 6 | 9 |
| ETHNICITY | CSV string (uncoerced) | 0 | 0 | 0 | 11 | 26 |
| EDREGTIME | CSV string (uncoerced) | 0 | 32 | 0 | 69 | 19 |
| EDOUTTIME | CSV string (uncoerced) | 0 | 32 | 0 | 69 | 19 |
| DIAGNOSIS | CSV string (uncoerced) | 0 | 0 | 0 | 82 | 84 |
| HOSPITAL_EXPIRE_FLAG | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 1 |
| HAS_CHARTEVENTS_DATA | CSV string (uncoerced) | 0 | 0 | 0 | 1 | 1 |

### model_metadata（9 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| model | CSV string (uncoerced) | 0 | 0 | 0 | 9 | 23 |
| judge_model_name | CSV string (uncoerced) | 0 | 0 | 0 | 9 | 51 |
| tokenizer_model_name | CSV string (uncoerced) | 0 | 0 | 0 | 9 | 41 |
| is_reasoning_model | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| structured_output_model_name | CSV string (uncoerced) | 0 | 6 | 0 | 2 | 50 |
| structured_output_tokenizer_name | CSV string (uncoerced) | 0 | 6 | 0 | 2 | 37 |
| source_artifact | CSV string (uncoerced) | 0 | 0 | 0 | 9 | 91 |
| source_sha256 | CSV string (uncoerced) | 0 | 0 | 0 | 9 | 64 |

### rater_configurations（174 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| rater_alias | CSV string (uncoerced) | 0 | 0 | 0 | 174 | 16 |
| rater_name | CSV string (uncoerced) | 0 | 0 | 0 | 174 | 165 |
| model | CSV string (uncoerced) | 0 | 0 | 0 | 9 | 23 |
| fact_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 8 |
| retrieval_method | CSV string (uncoerced) | 0 | 0 | 0 | 4 | 6 |
| top_n | CSV string (uncoerced) | 0 | 0 | 0 | 8 | 3 |
| reference_format | CSV string (uncoerced) | 0 | 0 | 0 | 3 | 13 |
| reference_only_admission | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| deduplicate_text | CSV string (uncoerced) | 0 | 0 | 0 | 1 | 4 |

### experiment_matrix（54 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| author_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| proposition_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 8 |
| fact_type | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 8 |
| retrieval_method | CSV string (uncoerced) | 0 | 0 | 0 | 4 | 6 |
| top_n | CSV string (uncoerced) | 0 | 0 | 0 | 8 | 3 |
| reference_format | CSV string (uncoerced) | 0 | 0 | 0 | 3 | 13 |
| reference_only_admission | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 5 |
| deduplicate_text | CSV string (uncoerced) | 0 | 0 | 0 | 1 | 4 |
| publication_role | CSV string (uncoerced) | 0 | 0 | 0 | 2 | 23 |

### verdicts（1437100 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| model | VARCHAR | 0 | 0 | 0 | 9 | 23 |
| proposition_id | VARCHAR | 0 | 0 | 0 | 10093 | 36 |
| rater_alias | VARCHAR | 0 | 0 | 0 | 174 | 16 |
| verdict | VARCHAR | 0 | 0 | 0 | 3 | 13 |
| reason | VARCHAR | 0 | 0 | 1 | 1299574 | 10670 |
| reasoning_chain | VARCHAR | 0 | 930540 | 0 | 506511 | 56648 |
| reasoning_final_answer | VARCHAR | 0 | 930540 | 0 | 488953 | 2935 |
| reference_id | VARCHAR | 0 | 0 | 0 | 400597 | 64 |

### reference_payloads（400597 行）

| 字段 | 读取类型 | NULL | 空串 | 纯空白 | 不同值 | 最大字符数 |
| --- | --- | --- | --- | --- | --- | --- |
| reference_id | VARCHAR | 0 | 0 | 0 | 400597 | 64 |
| reference | VARCHAR | 0 | 0 | 0 | 400597 | 41352 |

## 11. 文件清单及完整性

| release 相对路径 | 字节 | 清单哈希匹配 |
| --- | --- | --- |
| LICENSE.txt | 2518 | True |
| licenses/DeepSeek_R1_MIT_LICENSE | 1064 | True |
| licenses/Gemma_3_TERMS_OF_USE_2024-04-01.txt | 8498 | True |
| licenses/Llama_3.1_LICENSE | 7680 | True |
| licenses/Llama_3.3_LICENSE | 7909 | True |
| licenses/MODEL_LICENSES.md | 1725 | True |
| licenses/Qwen3_30B_A3B_2507_APACHE_2.0_LICENSE | 11343 | True |
| licenses/Qwen3_32B_APACHE_2.0_LICENSE | 11343 | True |
| prompts/prompts_atomic_claim.tar.gz | 1397 | True |
| prompts/prompts_llm_writer.tar.gz | 1111 | True |
| prompts/prompts_proposition_validity.tar.gz | 1674 | True |
| propositions/human_verdicts.csv.gz | 627004 | True |
| propositions/proposition_validity.csv.gz | 575176 | True |
| propositions/propositions.csv.gz | 1224938 | True |
| README.md | 9545 | True |
| reference_ehr/admissions.csv.gz | 5877 | True |
| reference_ehr/ehr_noteevents.csv.gz | 2896179 | True |
| reference_ehr/ehr_noteevents_pdf.tar.gz | 12555721 | True |
| reference_ehr/subject_ids.txt | 692 | True |
| SHA256SUMS.txt | 2342 | — |
| verifact/experiment_matrix.csv | 3468 | True |
| verifact/model_metadata.csv | 2535 | True |
| verifact/rater_configurations.csv | 38763 | True |
| verifact/reference_payloads.parquet | 417872137 | True |
| verifact/verdicts.parquet | 396059336 | True |

## 12. 需关注、失败与未验证的自动检查

| 检查 | 状态 | 观察到的内容 | 证据位置 |
| --- | --- | --- | --- |
| human.second_round_consistency | fail | 2 | second_round_anomalies.csv; paper p4 annotation flow |
| admissions.timestamp_metadata_agreement | warning | {'affected_propositions': 456, 'patients': 4} | admission_metadata_conflicts.csv |
| ehr.timestamp_caveats | warning | {'CHARTTIME:before_target_admission': 108, 'CHARTTIME:after_target_discharge': 12, 'STORETIME:after_target_discharge': 17, 'CHARTDATE:chartdate_differs_from_charttime_date': 61, 'STORETIME:before_target_admission': 4} | temporal_anomalies.csv |
| reference_pdf.content_equivalence | unverified | Archive members, PDF structure/page counts and patient filenames checked; clinical text equivalence not checked | pdf_inventory.csv |
| documentation.readme_declared_files | warning | ['verifact-bhc-croissant.jsonld', 'verifact/coverage.csv', 'verifact/missing_verdict_keys.csv'] | Local release README file tree / Version 1.1.0 scope |
| coverage.no_missing_verdicts | warning | 74 | missing_verdict_keys.csv |
| verdicts.explanations_present | warning | 1 | empty_reasons.csv (README mentions one exception) |
| comparability.identical_contexts_across_models | warning | 112821 | context_consistency.csv (exact UTF-8 differences, not necessarily semantic differences) |
| provenance.original_model_artifacts | unverified | ['data/verifact_results/verifact_gemma3_12B/score_reports/verdicts.feather', 'data/verifact_results/verifact_gemma3_27B/score_reports/verdicts.feather', 'data/verifact_results/verifact_qwen3_30B-A3B-Instruct/score_reports/verdicts.feather', 'data/verifact_results/verifact_qwen3_30B-A3B-Thinking/score_reports/verdicts.feather', 'data/verifact_results/verifact_qwen3_32B/score_reports/verdicts.feather', 'data/verifact_results/verifact_deepseek_r1_distill_llama_8B/score_reports/verdicts.feather', 'data/verifact_results/verifact_deepseek_r1_distill_llama_70B/score_reports/verdicts.feather', 'data/verifact_results/verifact_llama3_1_8B/score_reports/verdicts.feather', 'data/verifact_results/verifact_llama3_1_70B/score_reports/verdicts.feather'] | Original artifacts are not part of this release |
| claims.round1_all_different | warning | 467 | PDF p5 |

## 13. 输出文件与重跑方式

从项目根目录、Conda `research-verifact` 环境运行：

```powershell
python -B scripts/audit_dataset.py
python -B -m unittest discover -s tests -v
```

默认生成下一个未占用的 `outputs/001_dataset_audit/run_XXX/`。可用 `--run-name` 指定新目录，但已存在目录会被拒绝；写入 raw 范围也会被拒绝。审计可以离线重复运行，执行期间不访问 API、不下载数据、不进行模型推理。

- `report.md`：本报告，由机器结果生成。
- `audit.json`：汇总、字段画像、source evidence、官方说法比较和完整检查结果。
- `checks.json`：独立读取的自动检查结果；fail 导致非零退出，warning 与 unverified 不伪装为通过。
- `manifest.json`：输入文件/论文哈希、代码与环境文件哈希、实际包版本、命令、Git 状态、输出哈希及运行状态。
- `run.log`：每个阶段的运行日志。
- `*_index.csv`：患者、文档、命题及 EHR note 的可回查索引，包含原始键及显式派生字段，不复制整套临床正文。
- `model_configuration_coverage.csv` / `missing_verdict_keys.csv`：预期矩阵和逐键覆盖差异。
- `context_consistency.csv`：不同 Judge 相同检索配置下的精确输入比较。
- `reference_admission_headers.csv`：每个患者的实际 Judge 住院时间 header 与两套元数据对照。
- 其他 CSV：类别分布、重复、时间异常、模型元数据、档案成员与 PDF 页数等细节。

空的异常 CSV 保留表头，表示已执行检查但没有该类记录。更详细的字段与运行约定见任务目录 `tasks/001_dataset_audit/README.md`。
