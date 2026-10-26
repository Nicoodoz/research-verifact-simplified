# 独立审计记录与后续状态

## 最近任务（截至072）

066–072当前均为执行者自检/诊断状态，未宣称独立审计PASS。072静态/动态示例优化的确认组未达到事前升级门槛，自检864 PASS不等于独立审计或方法通过；071首轮development阳性由用户决定不重复并结项。067的实现及正式来源争议已在068–069说明，旧v1成绩不能作为保守增补方法证据。

[072交审](../outputs/072_adaptive_judge_examples/audit_handoff.md) · [071交审](../outputs/071_judge_icl_feasibility/audit_handoff.md) · [070交审](../outputs/070_fixed_evidence_reasoning_diagnosis/audit_handoff.md) · [069交审](../outputs/069_final_pack_controlled_repair/audit_handoff.md) · [068交审](../outputs/068_final_pack_utility_diagnosis/audit_handoff.md) · [067更正](../outputs/069_final_pack_controlled_repair/067_correction.md)。现行研究与技术恢复规则见[研究执行原则](../docs/RESEARCH_EXECUTION.md)；旧审计正文、证据及hash保持原样。

## 历史审计索引

**036待独立审计：** 执行者已完成标准对照、reserved40最终评价及自检。用户授权自检完成后直接推送，不代表审计PASS。见[交审材料](../outputs/036_final_validation/audit_handoff.md)。独立审计文件尚未生成。

**034/035快速独立审计PASS：** 034全部主指标/配对区间及逐ID来源通过；035九项测试、16折预测重放与17个SLSQP目标值复核通过。环境故障由正确conda激活解决，原521项成果不变。[034审计](034_same_data_comparison.md) · [035审计](035_lambda_boundary_calibration.md) · [环境入口](../docs/RUN_ENVIRONMENT.md)。

**033快速独立审计PASS：** 48422项离线核验、4项测试和两主要比较独立复算通过；未重训全部模型。未找到稳定同风险更优subset，A3固定点收益保留，A全40仅作保守覆盖建议。[审计](033_gate_training_subset.md) · [报告](../outputs/033_gate_training_subset/report.md)。

**032快速独立审计PASS，可冻结／结项：** 20项测试、135模型重放、54236组NLI输入重建及7个评价文件对照通过；主方案未实现PA/MCC共同提高，不改选辅助winner。见[独立审计](032_evidence_relation_correction.md)及[主报告](../outputs/032_evidence_relation_correction/report.md)。

**031快速独立审计PASS，可冻结／结项：** 24项测试、八模型重训、13个评价文件重放通过；4513尝试与37.70924338元累计核对一致，两主要负向比较独立复算通过。停止当前新增信息Gate，不自动032。见[独立审计](031_training_expansion_confirmation.md)及[主报告](../outputs/031_training_expansion_confirmation/report.md)。

**030快速独立审计PASS，可冻结／结项：** 23项测试、32,688个保存状态核验通过；独立重建全部划分，33个模型抽样重训吻合，k11主要区间复算一致。组成敏感性未解决，不冻结泛化Gate、不自动扩量或031。见[独立审计](030_gate_training_stability.md)及[主报告](../outputs/030_gate_training_stability/report.md)。

**029快速独立审计PASS，可冻结／结项：** 23项测试、36组完整离线重训和343份模型／结果逐字节对照通过；独立复核3096个模型状态及主要区间。保留有限OOF信号，迁移未稳定，不选winner、不自动030。见[独立审计](029_semantic_information_gate.md)及[主报告](../outputs/029_semantic_information_gate/report.md)。

**028快速独立审计PASS，可冻结／结项：** 310次回执、费用、引用及完整混合包络独立复算通过；23项测试、16份正式文件断网重放通过。方法未过门槛，停止当前版本，不自动029或reserved40。见[独立审计](028_traceable_claim_evidence_verification.md)及[主报告](../outputs/028_traceable_claim_evidence_verification/report.md)。

**027快速独立审计PASS，可冻结／结项：** 21项测试、11个正式文件重放通过；独立排序/冲突/高rescue核验与重点病例抽查通过。026停线保持，无新Gate、阈值或winner，0API/0拟合。见[独立审计](027_dual_judge_transfer_diagnosis.md)及[主报告](../outputs/027_dual_judge_transfer_diagnosis/report.md)。

**026快速独立审计PASS，可冻结／结项：** 冻结SD未过迁移门槛，停止当前版本；1352次调用、52个条件Qwen请求、冻结时序及费用核验通过，22项测试、15文件断网重放通过。见[独立审计](026_frozen_sd_patient_transfer.md)及[主报告](../outputs/026_frozen_sd_patient_transfer/report.md)。不自动reserved test。

**025快速独立审计PASS，可冻结／结项：** E路线停止；024D第二Judge正向OOF线索保留，历史D不可评价、Qwen未复现，完整门槛无winner。23项测试、15个正式输出及3个来源输出重放通过；0API，不自动后续。见[独立审计](025_lambda_flip_risk_separability.md)及[主报告](../outputs/025_lambda_flip_risk_separability/report.md)。

**024快速独立审计PASS，可冻结／结项：** 3515/3516核心有效；两模型方向支持，未达强迁移证据门槛。43项测试、15个核心文件断网重放及全部回执/费用核验通过；不自动reserved40。见[独立审计](024_lambda2_transfer_validation.md)及[主报告](../outputs/024_lambda2_transfer_validation/report.md)。

**023快速独立审计PASS，可冻结／结项：** 已完成401点与精确切换分析、患者敏感性、两张主图及作者补图，自检通过；0新增API、固定λ=2不变。见[主报告](../outputs/023_lambda_boundary_response_analysis/report.md)与[独立审计](023_lambda_boundary_response_analysis.md)。固定λ=2保持，不自动开启后续任务或reserved40。

**022快速独立审计PASS，可冻结／结项：** 022完成零API阶段A：16名development患者1529条R0＋879条R1折外评分，竞争感知与学习全局λ的2408条标签完全相同；相对U2正确数R0−28、R1−13，false-S虽减少但PA/MCC未达门槛。停止B/Qwen，保留λ=2；新增费用0/80元。[报告](../outputs/022_competition_aware_support_calibration/report.md) · [独立审计](022_competition_aware_support_calibration.md)。方法门槛仍为FAIL，停止阶段B/Qwen。

**2026-09-19：019–021快速独立审计PASS，可冻结／结项。** 019保护门槛失败、020仅development确认、021严格等价FAIL均保持。环境／共享.gitignore／当前导航及安全重放入口已同步，见[项目总览](../docs/PROJECT_STATUS.md)和[复现说明](../docs/REPRODUCIBILITY.md)。

**018快速独立审计PASS：** 1251条离线机器分析与78例重点深读已完成，0新增API。原VeriFact高PA伴随更多false-S及更低MCC点估计；执行者优先建议研究Judge支持边界，但最大可实现净headroom未知。见[主报告](../outputs/018_verifact_gap_attribution/report.md)与[审计交接](../outputs/018_verifact_gap_attribution/audit_handoff.md)。2026-09-16快速独立审计PASS、无阻塞问题，可冻结／结项；见[018审计](018_verifact_gap_attribution.md)。

**017独立审计PASS：** 017完成12名已暴露患者192条GT盲证据干预：19条稳定错误中稳定救回0条，160条稳定正确中破坏3条；未达事前headroom门槛，停止，不训练selector、不使用剩余10人确认。2026-09-16快速独立审计通过、无阻塞问题，可冻结／结项；见[017审计](017_verification_supervised_evidence_utility.md)。见[主报告](../outputs/017_verification_supervised_evidence_utility/report.md)与[审计交接](../outputs/017_verification_supervised_evidence_utility/audit_handoff.md)。

016已完成现有6名development患者601条验证：V4/Qwen均完整，92条分歧各完成ordinary repeat和015原版independent-review。review较最强单模型净-5条、较repeat净+1条；未达到原事前门槛，停止本方向，不做v2/v3或扩大。累计usage估算及未知预留¥21.79039103/¥40。Qwen保留127条硅基流动回答＋474条阿里云回答，基础模型跨时段，相关限制已披露。当前唯一必读[016中文主报告](../outputs/016_disagreement_triggered_review_validation/completion_002/report.md)；2026-09-16快速独立审计PASS，可冻结／结项，见[016审计](016_disagreement_triggered_review_validation.md)。

2026-09-16更新：014/015修订定向独立复核PASS，原R1/R2两项交付阻塞已关闭，可冻结／结项。原研究数值及015停止决定保持；详见[014审计末尾](014_qwen27b_baseline_comparison.md)与[015审计末尾](015_disagreement_adjudication.md)。

阅读顺序：各审计末尾最新追加决定当前状态，不能用009文件开头的初审／有条件通过措辞覆盖末尾修订PASS。早期审计里的后续建议与预算是当时记录；当前研究状态见[根README](../README.md)；001–018均有相应独立审计记录，013、015、016均没有可自动扩大的winner，未来API路由与80元总额规则见[现行约定](../docs/API_POLICY.md)及[AGENTS](../AGENTS.md#api-调用费用与确认规则)。

本目录保存独立审计模型对执行模型成果的审查意见，包括审查范围、结论、问题状态和是否建议进入下一阶段。原审计意见记录审计者的判断，后续修订自查和用户结项决定另行标明；这些记录不替代 `tasks/` 的任务说明或 `outputs/` 的实验报告，也不直接修改执行成果。

001–003 的初始记录于 **2026-09-13** 根据本会话实际完成的审计补记；此后追加 003 定向复核、004 离线准备与真实执行审计，以及 2026-09-14 的 004 修订定向独立复核。下表同步最近一次实际审计状态；任务结项、修订者自查和独立复核是不同事实，不能相互替代。

| 记录 | 原审计及后续状态 | 成果用途与限制 |
| --- | --- | --- |
| [001：数据集审计](001_dataset_audit.md) | 原审计通过，无阻塞修正；任务完成 | 作为 002、003 的数据基础，继续保留原始异常及使用限制 |
| [002：论文结果复算与统一评价](002_reproduce_paper_results.md) | 原审计通过，无阻塞修正；任务完成 | 后续统一评价入口；仓库外输出目录问题仍未修复，运行限制已写入任务说明 |
| [003：探索性错误分析](003_error_analysis.md) | 定向复核 PASS，H03 原阻塞问题关闭；原审计及修订历史保留 | 已结项，现行 review_004 保留，继续使用冻结患者分组 |
| [004：事件核对先导实验](004_event_alignment_pilot.md#修订定向独立复核通过2026-09-14) | 修订定向独立复核 PASS（2026-09-14）；原重放阻塞项与费用归属问题均关闭 | 已完成，可正式冻结／结项；结果方向不一致、执行遵守有限，不直接扩大当前版本 |
| [005：pilot 作用与退化分析](005_pilot_effect_analysis.md) | 独立审计 PASS（2026-09-14）；统计、材料对应及主要观察通过核对，无阻塞修正 | 已完成的探索性依据；当时上下文建议的后续验证见006，当前边界见013与根README |
| [006：局部来源上下文可行性](006_source_context_feasibility.md) | 精简独立审计 PASS（2026-09-14）；未发现阻塞修正，主比较缺失继续保留 | 可接受并结项；不直接扩大，EHR 来源／事件对应仍为待验证候选 |
| [007：上下文辅助检索](007_context_retrieval.md) | 精简独立审计 PASS（2026-09-14）；实际检索／评分可重建，无交付阻塞项 | 可结项；局部召回不等于稳定收益，当时预算/截取控制的后续处理见008–009 |
| [008：LLM 检索规划](008_retrieval_planning.md) | 精简独立审计 PASS（2026-09-14）；输入复用、候选链路和评分核对通过，无交付阻塞项 | 可结项；尚无稳定planner优势，009已作空白解析诊断和基础检索对照，当前边界见013与根README |
| [009：检索基线比较与证据损失定位](009_retrieval_baselines.md) | 修订定向独立复核 PASS（2026-09-15）；正常审计文档更新的重放阻塞关闭，冻结材料校验保留 | 可正式冻结／结项；C48 暂作实用基线并保留 A48，未证明稳定优势；当时证据组织建议的后续校准/筛选见010–013 |
| [010：VeriFact baseline 校准](010_verifact_baseline_alignment.md) | 精简独立审计 PASS（2026-09-15）；两层比较、同期输入、回执／费用和评分通过核对，无阻塞项 | 可冻结／结项；C48 可保留作实用对照，未证明稳定优势或新 packaging 有效 |
| [011：证据完整性与局部结构恢复](011_evidence_integrity_packaging.md) | 精简独立审计 PASS（2026-09-15）；预设门槛、重复／费用和离线重放核对通过 | 可冻结／结项；停止当前B/C组合扩展，650条main未启动，保留冻结C48对照 |
| [012：三组对照错误诊断](012_comparative_error_diagnosis.md) | 独立审计 PASS（2026-09-15）；三组对应、选例、原文轨迹和核心解释核对通过，无阻塞项 | 可冻结／结项；目标/支持范围与输入保真仍为待验证方向，未深读错误和无医学gold限制保留 |
| [013：多机制压力筛选](013_multi_mechanism_screen.md) | 快速独立审计 PASS（2026-09-15）；输入／回执、刷新控制、停止结果及重放核对通过，无阻塞项 | 可冻结／结项；四个实现停止扩大，不组合、不做新患者确认；局部作用不等于整体收益 |
| [014：Qwen27B固定证据比较](014_qwen27b_baseline_comparison.md) | 修订定向独立复核PASS（2026-09-16），R1/R2关闭 | 可结项；Qwen为研究候选，未证明非劣或本地部署性能 |
| [015：分歧证据仲裁](015_disagreement_adjudication.md) | 修订定向独立复核PASS（2026-09-16），R1/R2关闭 | 可结项；无winner，不新患者确认；不以对照替代winner |
| [016：分歧触发独立复核](016_disagreement_triggered_review_validation.md) | 快速独立审计PASS（2026-09-16），无阻塞项 | 可冻结／结项；review较最强单模型−5、较repeat+1，停止；混合供应商限制保留 |
| [017：verdict监督证据utility](017_verification_supervised_evidence_utility.md) | 快速独立审计PASS（2026-09-16），无阻塞项 | headroom未达门槛，停止；未训练、未新患者确认 |
| [018：跨队列差距归因](018_verifact_gap_attribution.md) | 快速独立审计PASS（2026-09-16），无阻塞项 | 可冻结／结项；支持边界为研究优先级，最大可实现净收益仍unknown；非新方法验证 |
| [019：支持边界筛查](019_support_boundary_screen.md) | 快速独立审计PASS（2026-09-19） | 原低false-S门槛失败，无winner |
| [020：固定λ2新患者确认](020_lambda2_patient_validation.md) | 快速独立审计PASS（2026-09-19） | 总体双轮增益保留类别代价；未开reserved test |
| [021：BGE本地化](021_bge_localization.md) | 快速独立审计PASS（2026-09-19） | 严格等价FAIL；不能继承020成绩 |

012已完成全任务独立审计，结论PASS；当前依据见[012审计](012_comparative_error_diagnosis.md)。原执行报告和三个定向核查保留其历史范围，不替代医生裁决；011的停止决定继续有效。

013已通过[快速独立审计](013_multi_mechanism_screen.md)，可冻结／结项。四个具体分支均未通过压力筛选，停止扩大，不执行组合或新患者确认；没有新的论文方法候选。其研究限制及审计范围仍保留。

当前状态以各审计文件末尾注明日期的追加结论为准；旧审计原文、run 报告和 manifest 保留历史状态。004 本次先记录独立复核结论，再同步当前说明，两个阶段的范围和文件指纹见 [状态同步记录](artifacts/004_revision_20260914/state_sync.json)。

记录中的链接用于定位被审查成果。后续若修正、复核或结项，应明确追加实际状态、来源和依据，不把修订者自查或用户结项决定记为独立复核通过。
