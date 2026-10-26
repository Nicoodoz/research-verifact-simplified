# 003_error_analysis

003的20/40/40分组保持不变。至009，开发组前24名已用于方法/案例分析，剩余16名沿原顺序使用；当前建议以[009已审结论](../../outputs/009_retrieval_baselines/README.md)为准。

## 目的与范围

基于 001 正式审计和 002 正式复算，探索已有系统在 LLM-written / human-written atomic claims 上反复出现的失败现象。保留发布的医生 GT，不新增医学真值，不预设改检索、微调或重切分。此次不运行新模型，不扩展全面审计。

在查看新案例前冻结患者分组：20 名探索、40 名后续开发、40 名保留测试。此前已详细查看的病例放入探索组，其余仅按患者 ID 的固定 SHA-256 排序分配，不按标签、模型表现或文本挑选。所有同患者 BHC、命题、EHR 共同归组。确切清单与既往曝光说明保存在 `outputs/003_error_analysis/patient_groups.json`，之后不得为了结果更好而重抽。001/002 已有全数据汇总分析，因此这是对今后方法开发的前瞻隔离，不宣称测试数据从未被接触。

## 预先确定的分析方法

- 只分析探索患者的 valid-only atomic claims；分别保存 LLM/human 全量探索队列和排除的 invalid ID。
- 主 baseline 为 002 固定的 R1-70B，sentence facts、N100、rerank、absolute_time、current admission、deduplicate=True。Qwen-3-30B-A3B-Thinking 的同参数配置作为诊断对照；不据此声称 Judge 因果优劣，逐例记录实际 reference 是否相同。
- 复用 `verifact_research.evaluation.evaluate`，完整预测覆盖强制检查。本次描述性点估计用显式 `profile=none`，不做模型排行榜或显著性检验；后续正式实验仍用 002 的患者 bootstrap 协议。
- 初始 24 例：每种作者 9 个错误、3 个正确对照。错误覆盖可用 GT→预测混淆格，再按格大小补足；正确对照尽量每个 GT 类各 1 个。格内按固定 ID 哈希排序，优先每作者每患者最多 2 例，必要的放宽逐例记录。不按文本“好讲故事”挑选。
- 如需要验证一个初步现象，可在同一探索组补充少量反例或关联命题，单独记录选择理由，不替换初始样本。该分层目的抽样不能估计某种失败机制的总体发生率。
- 逐例检查命题与原 BHC/parent、医生投票与可用评论、实际模型 verdict、短 reason、完整 reasoning_chain / reasoning_final_answer 和 reference，以及必要的原始 EHR。原文摘录记录完整键、SHA-256 和字符偏移。日期和 admission 范围不静默修正；reference 不是 gold evidence。
- 分开写直接观察、解释假设、仍不确定之处。有限检索中未找到证据，不等于全 EHR 确认没有证据；英文病例中文释义由本次分析者给出，不属于医生标注。

## 资料与复现

从项目根目录、Conda `research-verifact` 环境运行：

```powershell
python -B tasks/003_error_analysis/analyze.py --help
python -B tasks/003_error_analysis/analyze.py extract
```

第一次分组使用 `freeze --previously-viewed` 显式列出此前已查看的患者；现已冻结的项目应复用本地清单，不能再分组。`extract` 每次创建新的 run，不覆盖历史结果。病例解释是人工逐例阅读（Codex 辅助）形成的探索记录，不是自动运行可重新生成的医学判断；提取、样本选择、指标和证据对应关系可以自动复查。

## 完成情况与结果入口

已完成，用户已确认结项（2026-09-13）。正式提取为 `run_001`，现行修订报告为 `run_001/review_004`；入口见 [输出 README](../../outputs/003_error_analysis/README.md)。探索组 1,817 条有效 claims 的两个配置预测均完整；初始 24 例全部保留并分析，未额外补例或重判医生标签。解释性结论不可当成标注或训练真值。review_004 已按独立审计修正 H03、补充 H04，并自查原 24 例 R1 完整输出；后续独立定向复核已 PASS，H03 原阻塞项关闭，见 [003 审计末尾追加记录](../../reviews/003_error_analysis.md)。未新增医生裁决；现行报告保留修订生成时的历史措辞。

| 文件 | 职责 |
| --- | --- |
| `analyze.py` | 冻结患者分组，复用 002 队列与公共评价函数，按混淆格选例，提取真实模型输入输出及 EHR |
| `inspect_cases.py` | 记录本地关键词检索、候选证据窗口与字符位置；不自动归因 |
| `build_review.py` | 校验 EHR/reference 与模型输出锚点，展示完整生成输出，生成逐例文档、阅读范围和报告 |
| `verify.py` | 比较重复提取与报告，检查哈希、链接和测试 |
| `tests/test_error_analysis.py` | 合成数据检查患者隔离、抽样覆盖、跨患者证据、篡改和时间/正文比较 |

检查现有正式成果（不重新抽组、提取或生成 review）：

```powershell
python -B tasks/003_error_analysis/verify.py
```

该命令默认比较 `run_001/review_004` 与重复生成的 `run_002/review_003`，创建新的 verification 目录并运行现有测试。

如需从已保存的解释记录重新生成当前报告，可在两份已验证的提取上回放正式源记录快照：

```powershell
python -B tasks/003_error_analysis/build_review.py --run run_001 --notes outputs/003_error_analysis/run_001/review_004/review_notes_snapshot.json
python -B tasks/003_error_analysis/build_review.py --run run_002 --notes outputs/003_error_analysis/run_001/review_004/review_notes_snapshot.json
```

`build_review.py` 每次创建新的 `review_XXX`，使用 `--notes` 指定记录及其同目录的报告模板；以上两次生成不会覆盖现行结果。随后执行 `python -B tasks/003_error_analysis/verify.py --review-a <run_001中新生成的review目录名> --review-b <run_002中新生成的review目录名>`，把占位符替换成两次命令实际输出的目录名，不能继续用默认的旧 review 检查新产物。不指定 `--notes` 时读取 `outputs/003_error_analysis/review_notes.json` 和同目录 `report_template.md`，适用于明确要采用这些当前源记录的情况。

上述复查无需重新运行 001 或全量 002，也不需要推理 API、新依赖或 GPU。

可重复生成的是患者分组校验、样本、原文材料、指标、证据对应和文档；“阅读产生的解释”本身作为版本化本地研究记录保留，不伪称可以自动重做临床判断。后续迁移工作目录要保留这些本地源记录及冻结分组，不能在新机器上悄悄重新抽样。

## 修订后的阅读与检查

病例页展示两模型的完整 reasoning_chain 和 reasoning_final_answer，短 reason 单独保留。模型输出锚点核对 proposition、rater、字段、哈希、原文及偏移，与 EHR/reference 证据分开。短 reason 未写某条件不能推断模型没有考虑；生成的推理文本也不能证明内部因果机制。

本次逐例复读 24 份 R1 完整输出，并核对两模型短 reason；另补读 9 份 Qwen 完整输出。逐模型范围记在 output_review.json，其余 Qwen 完整字段虽展示，但不声称本轮也已全部复读。文件中还逐项比较最终回答 JSON 与发布列，差异保留原值，不据此改变评价标签。

检查只保证来源、呈现、统计及可重复生成，不把自动检查通过等同于解释或临床结论通过独立复核。

## 后续研究判断

003 形成的优先假设是同一事件、状态、限定条件与支持范围核对；其次是已输入证据的利用。前者已在 [004](../004_event_alignment_pilot/README.md) 按冻结开发组前 6 名、421 条完整有效 claims 执行，且修订独立复核通过：LLM 点估计小幅正向、human 负向，两个患者 bootstrap 区间均跨 0，检查结构遵守有限，不支持直接扩大当前版本。原第二个小实验未按003原方案单独执行；相关证据利用问题已由005–009继续检验，不是当前自动待办。两个假设均不是已确定的论文贡献。后续设计继续固定实际队列、输入与预算，复用 002 评价代码；保留测试组在方法冻结前不用于逐例分析或调参。具体探索依据和反例保留在原报告中。
