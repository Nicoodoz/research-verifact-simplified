# 070：固定证据下的 LLM 判断差异诊断

## 研究决策

**暂停 final pack 与推理方法开发；现有材料不足以支持启动下一项推理实验。** 066 的 Reasoning Oracle 确实能在同一 final reference 上，从现有答案中事后挑对 14/39 条错误；但没有一种候选判断能在完整保护队列上取得稳定净收益。答对候选均无同体重复，一些“答对”的 reason 还把计划当作完成，或忽略 claim 的时间/地点限定。因此不能将 oracle 互补性转成模型路由、prompt 或可学习机制的证据。本轮完成预定的零 API 诊断；协议中“推荐后续实验”的证据门槛**未满足**。

## 固定口径与主要结果

复用 053 的 240 条 development claim（40 人），其中 T-S 核心有效且有 Qwen 完整分数的 **237 条**作为同 ID 主比较。另 3 条 T-S 核心无效保留 053 的固定回退，未给它们编造 Qwen 预测；066 的 240 条 G 基准仍为 201 正确/39 错，14 条 oracle 修复均位于共同 237 条内。逐条校验 N、T、Q 实际请求的 proposition 与完整 final reference：N/T 各 240/240 一致，Q 237/237 一致；Q 的 209 个新回执加 28 个 053 旧回执不能被当成 237 次新重复。三套模型/模式的系统 prompt、模型与生成设置不同，以下只归因于**固定证据下的判断差异**，不单独归因于 thinking 或模型架构。

| 判断（共同 237 条） | 正确 | PA | AC1 | MCC | false-S | S/NS/NA 召回 | 相对 G 的救回/伤害/净值 |
|---|---:|---:|---:|---:|---:|---|---:|
| T-S＋Frozen PriorG（G） | 198 | 83.54% | .7987 | .5596 | 8 | 88.54% / 50.00% / 67.74% | 基准 |
| DeepSeek non-thinking U0（N） | 179 | 75.53% | .6928 | .4465 | 8 | 80.73% / 57.14% / 51.61% | 9 / 28 / −19 |
| DeepSeek thinking 原生 verdict（T） | 180 | 75.95% | .6945 | .4838 | 5 | 78.65% / 57.14% / 67.74% | 1 / 19 / −18 |
| Qwen score argmax U0（Q） | 186 | 78.48% | .7300 | .5286 | 4 | 82.81% / 92.86% / 45.16% | 11 / 23 / −12 |

统一调用 `verifact_research.evaluation.evaluate` 与 `paired_compare`，valid-only、三分类 micro、同一 237 条、40 人、1,000 次患者 cluster bootstrap、missing=error。相对 G 的 ΔPA：N −8.02pp（95%患者区间 −13.03 至 −3.35），T −7.59pp（−11.72 至 −3.77），Q −5.06pp（−9.21 至 −0.84）。Q 的 ΔMCC −.0310，区间 [−.1076,+.0525]，不将其说成确定下降；但净正确 −12 且 S/NA 受损。Q 救回 6 条 GT=NS，同时伤害 7 条 GT=NA、16 条 GT=S；N 救回 4 条 NS，却伤害 7 条 NA、18 条 S。T 的较低 false-S 也伴随 19 条原本正确的 S 改错。细表、每个 ID 的救回/伤害及类别转移见 [`evaluation.json`](evaluation.json)、[`changed_cases.jsonl`](changed_cases.jsonl)。

## 14 条为什么会“修对”

按 066 的 GT oracle 口径，14 条（12 人；GT 为 S 6、NS 6、NA 2）中 N 答对 9 条、Q 答对 11 条、T 原生答对 1 条；N 独有 3 条，Q 独有 4 条，7 条有多个候选答对。**T 的唯一答对 `fa9a579f` 被 Frozen PriorG 从 NS 改成 S**：final reference 确认左肾造瘘与引流，但没有支持 claim 的“大量尿液”。它首先说明同一次 T 分数经固定决策边界会翻转，并不是 T 再推理后改对。Q 的原生 verdict 与 score argmax 在 14 条相同。

可观察的语义线索有两组：

- **NS/NA 的“相关但不完整”边界反复出现。** `024c4356`（4U/Hct23 对 6U/Hct21）、`38a920f8`（10-15 CT 对 10-18 CXR）、`0ad8dc66`（balloon/angioplasty 对 stent）把相似主题但不同数值、时间/方式或操作判 NS；另有尿潴留、复合输血/尿量病例边界更模糊。镜像的 7 条 GT=NA 保护病例被 Q 判 NS，往往也因相关事实有记录而关键日期、剂量、速度或出院状态未见。这个模式值得**界定标签契约**，尚不能证明某模型更会理解证据。
- **完整命题、事件状态与限定词存在张力。** `a52e6343` 中 Q 把“计划转回 VA ICU/已交班”当作“已转回”；`a9f518eb` 把继续/优化 beta-blocker 当作新启动；`ccb46441` 把“renally dose”计划与已实施调剂量混用；`434bed80` 的 N 答对却未在 final reference 中找到 claim 的 24 小时限定。反过来，Q 在 16 条原本正确的 S 中也多次因地点、时间、基线、持续范围等限定而改为 NS。故不能把 Q 的 S 类救回解释为稳定的完整命题推理改善。

逐例“实际 claim—完整 reference—输出 reason/checks/引用—候选解释”见 [`case_ledger.md`](case_ledger.md) 和 [`casebook_full.jsonl`](casebook_full.jsonl)。有些输出引用了 note ID 而非包内序号，引用本身也不保证支持。reason 与 thinking 内容只是可见解释，不代表模型内部因果；本轮没有新增医学 GT，也未对医生标签重新裁决。

## 重复性与下一步

逐字节规范化的**完整请求体**匹配 050–053、055、068–069 的独立 request/receipt：14×3=42 个候选输入中，38 个只有一次回执，3 个 T 输入各两次、1 个 N 输入七次。重复的四种输入全部仍为错误 verdict；**没有一个答对候选被相同设置与 final reference 独立复验**。重复清单与回执路径见 [`exact_repeats.json`](exact_repeats.json)。这个检索范围不等于全仓库所有历史模型结果，但已覆盖本轮同条件相关回执；旧答案复用不算重复。

最有信息价值的下一步是先**收缩为 NS/NA 标签契约与 final reference 可见范围的离线病例裁定**：明确“相关主题存在但关键事件/限定缺失”何时是 NS、何时是 NA，并记录行政页眉能否作为出院事件证据。需要现有医生定义或独立临床裁定作为依据；不能用模型 reason 自证。若之后要考虑唯一的受控推理机制，应是固定证据下的 NS/NA addressability 判断，并且在冻结对称的 NS/NA 与原本正确 S 保护病例、独立同体重复后，只有**系统级净收益且无不可接受的 S/NA 损失**才继续；若仍只是边界倾向挪动或结果不可重复，则停止。当前不预实现，也不启动 071。

## 执行边界

零收费 API、无新增检索、无 evidence pack/PriorG/prompt/路由修改、无 reserved 开发；未 commit/push。来源哈希、覆盖与同证据校验见 [`source_alignment_summary.json`](source_alignment_summary.json)，执行者自检见 [`verification.json`](verification.json)。
