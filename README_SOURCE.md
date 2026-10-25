# Research-VeriFact

临床文本与患者EHR的一致性核验研究。当前已完成至 **097（2026-09-28）**，097已结项，不自动启动下一任务。

## 当前结论与入口

097完成同V4四臂原生接口对照：raw共同158条，C48 B/简洁任务/现行B＋G正确116/125/135；简洁任务只改善raw，未升级最终系统。40例源文核查显示405/482个检索片段被切开，但自动依赖构造及完整S0/W/F/H费用门槛未过，B无分类结果；新增492次HTTP200、¥12.967287/20，默认不变。[097报告](outputs/097_native_judge_source_dependence/report.md)。

096已完成AWQ-Marlin跨Judge与PriorG迁移验证：自然800条Original/V4 raw/R1 raw正确657/617/599；R1重新适配595，旧PriorG直接迁移616且与prior-only同标签。共同798条当前V4＋G正确664、MCC0.5802，R1-adapted594/0.4163。停止本轮适配，默认不变；1143 HTTP200、0重试，AutoDL用户已关机，按token新API0元、GPU租金未知。自检通过，独立审计未执行。 [正式报告](outputs/096_r1_native_priorg/report.md) · [论文更新](outputs/096_r1_native_priorg/manuscript_implications.md)。

默认系统仍为 **C48 → DeepSeek V4 Flash T-S thinking-high → Frozen PriorG，无示例B**。G是固定分数层修正，不是双模型Gate；F4、P90、R1替换、092模型及094候选均未升级默认。

B成功覆盖9065/9065、共同core 8997；同ID原作者/B＋G正确7285/7552、MCC 0.4983/0.5976、false-S 564/347。300构造、117核对后95自动拟触发，但语义核对失败，全局停止C最终Judge/扩量，不能称分类阴性；新增目录价及未知预留¥95.769536/150。

092完成100名患者9065条有效atomic claim的五折患者分组OOF。Frozen/Fine-tuned正确7204/7530、MCC0.4433/0.5156；微调有受控增量，但NS召回仅8.95%。共同956条上B/F4/文本融合正确783/793/795，错误支持41/52/64，融合不构成综合升级。研究完成不等于方法胜出，自检不等于独立审计。

093完成精确重复原文折叠与固定预算补证，保持原C48全部信息及来源：自然共同core 88条B/F/A正确76/77/76，压力30条17/16/18；未证明综合升级，停止本版。153次HTTP200，未优惠原价¥4.097118/20，无重试。

094完成固定C48下答案隔离式问答：自然20条B/V/Q最终均19正确，机制12条为9/8/9；机制Q的false-S为1，B为0。Q未证明系统增量，停止本版。157次HTTP200、0重试，原价¥2.508135/20；问题/来源核查和病例归因均留档。

- [095先读这个](outputs/095_anchored_minimal_contrast/report.md)、[统一9065结果](outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl)、[来源构造停止依据](outputs/095_anchored_minimal_contrast/candidate_cases.md)、[独立复核](reviews/095_anchored_minimal_contrast/final_review.md)
- [094正式报告](outputs/094_answer_isolated_verification/report.md)、[完整指标](outputs/094_answer_isolated_verification/detailed_tables.md)、[病例归因](outputs/094_answer_isolated_verification/case_analysis.md)
- [093报告与历史差异](outputs/093_lossless_evidence_budget/report.md)、[完整指标](outputs/093_lossless_evidence_budget/detailed_tables.md)
- [最新完整中文论文稿](outputs/095_anchored_minimal_contrast/manuscript_zh.md)
- [092正式报告](outputs/092_task_adapted_verifier/report.md)、[全部指标](outputs/092_task_adapted_verifier/detailed_tables.md)、[完成指纹](outputs/092_task_adapted_verifier/completion.json)
- [项目现状与证据边界](docs/PROJECT_STATUS.md)、[完整任务索引](docs/TASK_INDEX.md)
- [执行约定](AGENTS.md)、[研究原则](docs/RESEARCH_EXECUTION.md)、[API预算与路由](docs/API_POLICY.md)
- [环境与启动](docs/RUN_ENVIRONMENT.md)、[离线复查](docs/REPRODUCIBILITY.md)、[独立审计索引](reviews/README.md)

## 数据与科学边界

VeriFact-BHC v1.1.0来自MIMIC-III，共100名患者、13070条句子级和原子级命题；092使用9065条有效atomic claim，human/LLM都纳入并分层。历史20 exploration / 40 development / 40 reserved没有额外未用20名患者。development反复暴露，reserved在036最终评价及后续分析后，095也明确授权现有全部材料开展本轮开发/评价；092曾获明确授权纳入全体患者CV。不得再称未接触holdout。

036确认的是早期U2/Gate/标准校准，不为当前T-S＋PriorG或092提供最终验证。092外层患者隔离与新的独立外部测试不同。完整EHR医生标签、实际C48证据和模型判断分开；原文引用、模型reason和自报label_scores不是新医生GT或token probability。

## 环境与运行

当前CPU分析/API管理环境是research-verifact-029；根environment.yml与其关键实测依赖一致。032/092本地GPU使用独立verifier环境，AutoDL的092环境另有记录；不混入085的vLLM服务。

~~~powershell
pwsh -NoProfile -File scripts/run_research.ps1 scripts/check_research_environment.py
~~~

这是零API环境自检，不会启动实验。新机器重建和GPU入口见[环境说明](docs/RUN_ENVIRONMENT.md)。环境清单不是跨平台完整锁文件，本次没有重新安装环境。

## 目录与保留规则

|目录|用途|
|---|---|
|data/|合法取得的原始/派生数据，原始层只读，不推送临床原文|
|src/、scripts/、tests/|共享实现、入口及必要测试|
|tasks/|按编号的任务代码、协议和导航；旧协议属于形成时授权|
|outputs/|报告、公开ID/指标/指纹；冻结结果保留，不能覆盖重跑|
|reviews/|实际独立审计及证据，不能用执行者自检替代|
|docs/|现行政策、研究资料、来源快照及历史说明|
|.local_models/|私有权重、原文、缓存与环境，受现有gitignore保护|

新研究须用户明确交办；默认新增收费API全任务上限20元，专项上限优先，GPU租金另账。完成报告及自检后保留本地改动；仅在用户明确要求时提交或推送，随后停止。凭据、私有回执、临床原文和权重不提交；不擅改.gitignore。

## 文档适用范围

本页和docs中的现行政策是当前入口。各历史协议、报告、审计和来源文献按形成时解读；旧“待部署/待审/80元”等不再自动成为当前指令。任务导航已标明这一范围，完整旧导航保存在[同步前快照索引](docs/history/2026-09-27_before_sync/README.md)。本次同步依据与检查见[文档维护报告](docs/maintenance/2026-09-27_sync/report.md)。
