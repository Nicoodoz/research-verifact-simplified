# 001_dataset_audit：结果入口

任务已完成。请优先阅读 **[正式中文审计报告](run_006/report.md)**。报告区分实际文件验证、官方定义和仍待确认的内容；包含关系图、分布、覆盖、异常和全部主要表的字段画像。

## 交付文件

| 用途 | 文件 |
| --- | --- |
| 人读报告 | [run_006/report.md](run_006/report.md) |
| 机器可读完整汇总 | [run_006/audit.json](run_006/audit.json) |
| 94 项数据检查 | [run_006/checks.json](run_006/checks.json) |
| 输入、代码、依赖与输出指纹 | [run_006/manifest.json](run_006/manifest.json) |
| 最终重复运行验证 | [verification.json](verification.json) |
| 任务定义、实现和字段约定 | [任务 README](../../tasks/001_dataset_audit/README.md) |
| 审计运行入口 | [audit_dataset.py](../../scripts/audit_dataset.py) |
| 关键逻辑测试 | [test_dataset_audit.py](../../tests/test_dataset_audit.py) |

正式 run 共 35 个文件，其中 30 个 CSV 提供患者、BHC、命题、EHR note 索引，以及标签分布、缺失预测、模型配置、时间冲突等明细。原始临床正文仍从官方数据按键读取。

## 已验证的主要结果

- 100 名患者、100 次目标住院、200 份 BHC、13,070 条命题；参考 EHR 有 4,787 条 note，覆盖 125 个 admission。
- 三张命题表的 ID、文本、作者类型、命题类型完整对应；AI 的命题、rater、model、reference 外键均可解析。
- 人工最终标签为 Supported 9,617 条、Not Supported 1,156 条、Not Addressed 2,297 条。最终 invalid 为 456 条，其中 30 条仍有 AI 预测。
- 1,437,100 行 AI 预测，覆盖 10,093 条命题；9 个模型、174 个 rater、54 行 matrix，展开为 426 个模型与 matrix 组合。
- 400,597 个 reference payload 的内容 SHA-256 全部重新计算并匹配其 ID。官方校验清单内的 24 个文件全部匹配；25 个原始文件在运行前后均未改变。

## 后续研究必须保留的注意事项

1. **医生第二轮字段有 2 条矛盾。** `round2_decision=Agree`，但保存的两位医生标签不同。最终 `human_gt` 与 `adjudicated_verdict` 一致；当前资料不足以解释中间字段差异。完整记录见 [second_round_anomalies.csv](run_006/second_round_anomalies.csv)。两条均属于 human sentence，当前发布的 AI 实验矩阵不覆盖这一组。
2. **4 名患者的出院日期存在两套值。** 命题表比 admissions 早 1–2 天，涉及 456 条命题。绝对时间格式的 Judge header 使用 admissions 中的日期。见 [admission_conflict_summary.csv](run_006/admission_conflict_summary.csv) 和 [reference_admission_headers.csv](run_006/reference_admission_headers.csv)；不据此裁定临床真实时间。
3. **应有预测键中缺少 74 条。** 均属于 Qwen-3-30B-A3B-Thinking 的一个 human claim 配置。另有 2,977 条 human sentence 按实验矩阵设计没有 AI 结果，两者原因不同。见 [配置覆盖](run_006/model_configuration_coverage.csv) 和 [缺失键](run_006/missing_verdict_keys.csv)。
4. **相同检索参数不保证相同 Judge 输入。** 182,666 个多模型比较组中，112,821 组存在不同精确 payload；本任务未将差异进一步归类为排版、排序或医学内容变化。模型间公平比较需要检查实际输入。
5. **论文和说明文件有未解释的差异。** 第一轮三人各投一类，论文写 478 条，实际重算为 467 条。README 提到的 Croissant、coverage.csv、missing_verdict_keys.csv 在本地 release 和其校验清单中均不存在。本任务生成的覆盖表明确属于派生输出。
6. **EHR 范围和评价对象需明确。** 参考记录包含其他住院及历史出院小结，不能把全部 EHR inner join 到只有目标住院的 admissions 表。无效命题仍有标签；新拆分单元不能自动继承标签。没有逐条医生理由或证据 span 金标准。

上述数据基础已被后续 [002 统一评价](../002_reproduce_paper_results/README.md) 和 [003 错误分析](../003_error_analysis/README.md) 采用，两项任务均已完成。当前 invalid、缺失预测和默认 baseline 口径见 002；20/40/40 患者分组由 003 冻结。001 本身没有重判标签或创建训练/测试划分。后续训练或模型对比仍须记录实际队列、时间范围及异常处理，不把任务完成当作异常已经消失。

## 如何理解检查状态

正式结果为 **84 pass、7 warning、2 unverified、1 fail**。唯一 fail 是第二轮医生流程字段矛盾，涉及 2 条记录；原值保留，未通过修改数据或降低检查要求消除失败。

因此正式运行的 manifest 为 `failed_checks`，脚本以非零状态提醒使用者检查数据问题。这表示审计已完整执行并发现数据缺陷；运行时异常另标为 `error`。主外键、最终 GT 的多数票/裁决来源及文件完整性检查均通过。

15 项合成数据测试全部通过。保持代码、环境和输入不变，完整执行 `run_005` 和 `run_006`；32 个机器文件（全部 CSV，以及 audit.json、checks.json）的 SHA-256 完全一致。报告仅运行编号不同；每个运行的输出也与自身 manifest 匹配。详见 [verification.json](verification.json)。

未验证事项包括 PDF 与 EHR CSV 全文的临床等价性、未发布源 Feather artifact 的哈希。审计也不证明医学事实正确或完整重现作者的生成与检索过程。

## 历史运行

遵守项目约定，历史结果均保留且未覆盖。后续分析请使用正式结果。

manifest 中的代码和文档哈希记录运行当时的版本；verification.json 记录最终两次运行完成时的验证。审计完成后更新项目 README、AGENTS 或任务说明，会使当前文档哈希与历史快照不同，这不改变当时的审计结果。后续更新不回写旧 manifest、报告或验证记录。

| 运行 | 定位与说明 |
| --- | --- |
| run_001 | 开发时 SQL 分组错误，运行中断；保留 traceback 与 manifest。 |
| run_002 | 初步完整审计；发现时间字段差异，尚未分开报告身份连接与日期冲突。 |
| run_003 | 开发复查；曾把 relative_time/score 当作绝对日期比较，产生误报，已被后续实现修正并加入回归测试。 |
| run_004 | 增补标注链检查后发现 2 条第二轮矛盾；后续补充了详细原值和报告解释。 |
| run_005 | 最终实现的完整运行。 |
| run_006 | 最终实现的重复运行；当前正式阅读入口，与 run_005 的机器结果逐字节一致。 |

## 重跑

在项目根目录、Conda `research-verifact` 环境中：

```powershell
python -B scripts/audit_dataset.py
python -B -m unittest discover -s tests -v
```

下一次审计默认创建新 run，不覆盖历史目录，也不写入 `data/00_raw/`。具体依赖、参数及退出状态约定见任务 README。
