# 010论文材料草稿（非新增主报告）

结论和限制以[主报告](report.md)为准；这里便于写作复用。执行自查完成，尚待独立审计。

## 可复用实验设置

We calibrated a local retrieval baseline against the released VeriFact system on the same 650 valid atomic claims from six previously used development patients (243 LLM-written and 407 human-written). We first rescored the released R1-70B predictions using the common evaluation protocol. This comparison is a same-cohort system reference, rather than a retrieval ablation, because the original and local systems differ in their judges and other components.

We then evaluated the exact released references and the frozen C48 references with contemporaneous calls to the same DeepSeek-V4-Flash judge. Claims, instructions, schema and generation parameters were fixed; only the reference field changed. The references were retained in full, so evidence content, formatting, metadata and input length were not independently controlled. The study therefore measures the performance of the two existing reference packages under a common judge, not the causal effect of a particular packaging operation.

中文设置清单：

- 数据：VeriFact-BHC v1.1.0，复用009完整队列，invalid不入分析；6患者ID和命题ID见 `preparation_001/cohort.csv`，该文件与009逐字节一致。
- 发布配置：唯一 `v1.1.0-rater-121`，R1-70B、100 sentence facts、rerank、absolute_time、当前住院、文本去重。`release_binding.json`保存配置、模型元数据、原文件哈希与002交叉检查。
- 本地C48：原claim→本地BM25与BGE-M3 dense两路交替保留48候选→原claim BGE rerank→每note最多2段、最多16整段、正文及记录头8000字符。整个住院总头另加；实际reference约8047字符，不能将总长误写严格≤8000。本轮未重新运行检索。
- 同期Judge：`deepseek-ai/DeepSeek-V4-Flash`，temperature=0、max_tokens=2048、enable_thinking=false、n=1、stream=false；004/009相同structured提示及schema；只送原proposition与EHR reference。
- 运行：1300个唯一主body，24个预设同输入重复，4并发按冻结顺序交错；1324个有效结果。旧009回答只作跨运行诊断。
- 评价：项目002 `evaluate`/`paired_compare`，三分类micro PA/AC1/MCC，1000次患者cluster bootstrap，作者分开、完整配对。重复不替换canonical；没有缺失敏感性需要启动。
- 定性：先按预登记选例再补全部剩余改变标签的NS，34例、68份完整主输出、75处逐字锚点；不是医学相关性金标准。针对N642额外读取同一已使用患者的原吞咽建议。

## 表格和可支持的结果

- [核心表CSV](tables_001/core_results.csv)／[Markdown](tables_001/core_results.md)：第一层与第二层显式区分。
- [配对差值与区间](tables_001/paired_differences.csv)、[各类完整统计](tables_001/per_class.csv)、[逐患者结果](additional_diagnostics_001/patient_differences.csv)。
- [转移表](analysis_001/transitions.csv)、[同输入跨运行比较](analysis_001/cross_run_c48_drift.json)、[预设重复](analysis_001/repeat_diagnostics.json)。
- [结构统计](reference_diagnostics_001/summary.json)、[note匹配与时间字段](metadata_linkage_001/summary.json)、[费用拆分](additional_diagnostics_001/cost_breakdown.json)。

可写结果：发布系统的较高PA没有在统一Judge的reference比较中重现。发布reference相对C48的ΔMCC为LLM −0.0572、人写−0.0497，两个患者区间跨0；human的PA/AC1区间倾向C48。发布reference输入tokens约为C48的2.40倍。内容恢复和内容遗漏双向存在，且计划/实施、直接/间接、时间范围等判断差异在相关证据已输入时仍存在。

## 相关工作定位与不可越过的边界

最直接参照是VeriFact原发布系统及其真实reference。本地源码阅读路径、固定提交链接和release绑定见[来源说明](../../tasks/010_verifact_baseline_alignment/source_notes.md)。原作者的BGE-M3 dense＋learned sparse/Qdrant配置不能与本地BM25＋dense混称；010验证的是实际保存payload，未恢复原始候选排名、索引或所有运行参数。

008/009的planner与基础检索对照构成前序探索，本任务没有新planner或新的检索算法。它把“发布模型成绩较好”“其证据包在本地Judge下较好”“某种证据组织方法有效”分成三个不同问题。本次仅回答前两者，并为第三者留下可回查假设。

**基础实现问题：** note Description或检查头未随结果进入Judge；条件句与结论拆开后只保留结论。修复这些缺口本身不能直接宣布算法创新。

**探索观察：** 发布更大的证据包并非C48超集；明确目标事件被找回不一定提高原标签一致性；相同完整请求会翻转。案例解释不证明模型内部因果过程。

**本次得到验证的范围：** 六名既有开发患者上的两层校准、完整配对指标、输入/回执绑定和具体原文缺口。不能声称C48普遍优于原VeriFact、已经证明包装有效、具有临床gold evidence，或把这些开发结果称独立保留测试成绩。

下一步可设计固定候选/相近证据预算下的身份与条件完整性对照；在此之前不需要为取得新贡献而扩大planner或换融合公式。本文件不构成新实验执行授权或已冻结的下一任务方案。
