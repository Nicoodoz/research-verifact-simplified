# 全部任务与当前入口（2026-10-30）

补充CPU核查：[120医生标注分层](../outputs/120_full_pool_sft/annotation_strata.md)显示，首轮三医师一致样本也同时出现质量提升与false-S增加，不能把风险全归于标注争议；[131源文上下文核查](../outputs/131_source_context_probe/report.md)完成6例，没有找到支持盲目扩大输入的新决定性依据。无新增GPU调用，40对reason仍为准备资产。

102已按用户2026-10-27最新指令最终封存，不补跑；零API、分类效果未检验。原预算停止解释的更正和本次双仓库发布授权见[最终封存说明](../outputs/102_demo_relation/closure.md)。

当前默认、授权和环境以[PROJECT_STATUS](PROJECT_STATUS.md)、[AGENTS](../AGENTS.md)及[RUN_ENVIRONMENT](RUN_ENVIRONMENT.md)为准。此表只导航真实工件，不把任务结束解释成方法通过；旧协议、输出内README/CURRENT和审计正文保持原阶段语义。最新稿为[095完整论文](../outputs/095_anchored_minimal_contrast/manuscript_zh.md)。

|任务|结果来源|核验与范围|当前适用范围|
|---|---|---|---|
|132_midpoint_update|[阶段结果](../outputs/132_midpoint_update/report.md) · [固定方案](../tasks/132_midpoint_update/PROTOCOL.md)|107/120有效更新中点，160条全部有效并通过扩展条件|新实例22:15起19元预算，340条正在接续；原160条不重发，粗筛不是最终收益|
|131_source_context_probe|[源文核查](../outputs/131_source_context_probe/report.md)|6例完整reference及相关原始note上下文；600片段可定位|没有新增分类成绩，未据此盲目扩大上下文或回填训练|
|130_header_blocks|[最终报告](../outputs/130_header_blocks/final_report.md) · [固定方案](../tasks/130_header_blocks/PROTOCOL.md)|160初筛后只补340，完整500均有效；输入tokens−28.40%|总正确不变、FS+1、压力MCC下降，停止格式扩大|
|129_native_reference_check|[最终报告](../outputs/129_native_reference_check/final_report.md) · [固定诊断](../tasks/129_native_reference_check/PROTOCOL.md)|107/120各160，清空reference后全部判NA，回执已回传|会响应证据缺失；不证明非空证据关系判断正确|
|128_sqrt_weight_refresh|[最终报告](../outputs/128_sqrt_weight_refresh/final_report.md) · [固定方案](../tasks/128_sqrt_weight_refresh/PROTOCOL.md)|同220起点149步和完整500完成，模型/完整状态回传|相对120正确−3、FS−3，MCC均下降；停止当前配方，不扩1317|
|127_native_reason_data|[数据准备](../outputs/127_native_reason_data/report.md) · [入口](../tasks/127_native_reason_data/CURRENT.md)|仅CPU，累计60条审读、40条配对及全部3675原标签保留|有限补充S/NA保护理由；其中6条针对107真实错误；无分类收益证明，不新训|
|126_conditional_state_readout|[准备与取消](../tasks/126_conditional_state_readout/CURRENT.md)|仅准备，未GPU提取、未真实拟合|按研究方向取消，无效果成绩|
|125_dual_state_readout|[160报告](../outputs/125_dual_state_readout/report.md)|固定拼接头真实CPU初筛|相对原117 MLP净−4正确、FS+4，阴性停止|
|124_seed_mean_readout|[报告](../outputs/124_seed_mean_readout/final_report.md) · [结果](../outputs/124_seed_mean_readout/full1817.json)|固定均值完整1817、区间及部署指针均保留|有真实标签增益；按用户最新方向停止后接融合主线，不改写为阴性|
|123_claim_only_control|[状态](../tasks/123_claim_only_control/CURRENT.md) · [TF-IDF](../outputs/123_claim_only_control/report.md) · [既有端到端记录](../outputs/117_verdict_probe/e2e_live_check.json)|TF-IDF已完成；同9B空reference对照准备后取消未跑|没有同9B诊断成绩；保留既有TF-IDF和端到端记录|
|122_balanced_pool_sft|[报告](../outputs/122_balanced_pool_sft/report.md) · [500指标](../outputs/122_balanced_pool_sft/balanced_pool_sft500.json)|32患者729条92步；500全部有效，160首回执复用|自然正确−21、压力+3；合计正确−18、FS−4，NS收益伴随S/NA损失；阴性结束|
|121_nearest_memory|[原160](../outputs/121_nearest_memory/report.md) · [固定扩展](../outputs/121_nearest_memory/reconsidered_extension.md)|固定配置完整1817，历史结果不改|MCC/PA收益伴随大幅FS及少数类损失；按方向退出后接主线|
|120_full_pool_sft|[220报告](../outputs/120_full_pool_sft/report.md) · [369步结果](../outputs/120_full_pool_sft/final_report.md)|369步2945条与1817首次评价完成，模型/完整状态回传|MCC .6250、正确1599、FS109/362；质量收益保留、风险明显；原220成绩保留|
|119_warm_head_ft|[报告](../outputs/119_warm_head_ft/report.md) · [指标](../outputs/119_warm_head_ft/trained_best160.json)|完整369步、内部验证与固定160；执行者复核|自然收益伴随压力/NS损失，停止扩大|
|118_full_data_heads|[重拟合](../outputs/118_full_data_heads/reconsidered_refit.md) · [seed检查](../outputs/118_full_data_heads/seed_stability.md)|全40人固定配方及两seed已完成|保留平方根头真实收益与风险；后接分类路线不再为论文主线|
|117_verdict_probe|[原报告](../outputs/117_verdict_probe/report.md) · [扩展](../outputs/117_verdict_probe/reconsidered_extension.md) · [原流程复验](../outputs/118_full_data_heads/unweighted_workflow_seed118.md)|完整1817和原选轮流程两seed保留|MCC/PA真实收益不改；用户按研究方向停止后接分类主线|
|116_research_cycle|[报告](../outputs/116_research_cycle/report.md) · [比较](../outputs/116_research_cycle/comparison.jsonl) · [流程复盘](116_WORKFLOW_REVIEW.md) · [状态](../outputs/116_research_cycle/cycle_state.json)|六候选真实评价；两次训练及完整状态回传；确认40未用|未达到主要目标，保留107；API0，GPU空闲但未关机|
|115_label_sum|[报告](../outputs/115_label_sum/final_report.md) · [分析](../outputs/115_label_sum/analysis.md) · [比较](../outputs/115_label_sum/comparison.json) · [协议](../tasks/115_label_sum/protocol.md)|同196、数值/梯度CPU检查、50步、500首次及患者配对；执行者自检|115未形成通过保护条件的综合增量，停止当前label_sum配方，保留107主基线。；完整状态回传，新授权双仓库发布，未关机，不自动116|
|114_matched_refresh|[报告](../outputs/114_matched_refresh/final_report.md) · [比较](../outputs/114_matched_refresh/comparison.json) · [去正文预测](../outputs/114_matched_refresh/predictions_sanitized.jsonl) · [协议](../tasks/114_matched_refresh/protocol.md)|固定匹配清单、50步/392次、500同ID、患者配对及完整状态回传；执行者自检|自然风险改善伴随NA损失，未过事前保护条件，停止当前配方；107保留，未关机，不自动115|
|113_label_path|[报告](../outputs/113_label_path/final_report.md) · [初筛](../outputs/113_label_path/pilot_comparison.json) · [门槛](../outputs/113_label_path/pilot_gate.json) · [协议](../tasks/113_label_path/protocol.md)|固定真路径评分及患者配对，执行者自检非独立审计|113有小幅正向点估计，但未达到预先固定的继续门槛：180条仅改变5条、净多3条正确，未减少false-S。停止本次label_path扩展，不补500，不宣称评分机制普遍无效。；不自动114或关机|
|112_disagreement_vote|[报告](../outputs/112_disagreement_vote/final_report.md) · [比较](../outputs/112_disagreement_vote/comparison.json) · [去正文预测](../outputs/112_disagreement_vote/predictions_sanitized.jsonl) · [协议](../tasks/112_disagreement_vote/protocol.md)|固定规则真值表、原180预期核对、138首回执及患者配对；执行者自检非独立审计|112未通过保留判断：固定投票有小幅MCC和PA点估计收益，但错误放行增加，且部署调用超过单107的两倍。保留107 label_only，停止disagreement_vote，不追加规则。；无训练/105新增/API/自动关机，不自动113|
|111_half_extension|[最终报告](../outputs/111_half_extension/final_report.md) · [指标](../outputs/111_half_extension/final_metrics.md) · [去正文预测](../outputs/111_half_extension/predictions_sanitized.jsonl) · [协议](../tasks/111_half_extension/protocol.md)|完整1817/103原180同ID比较、1000次患者配对、执行者自检非独立审计|111未支持保留update_half：新增1317相对105、107均降低MCC与PA，完整1817的错误放行减少不足以抵消正确S与NA损失。结束109续训＋插值衍生路线。；API0，材料回传；按用户要求未关机，不自动112|
|110_update_interpolation|[最终报告](../outputs/110_update_interpolation/final_report.md) · [指标](../outputs/110_update_interpolation/final_metrics.md) · [诊断](../outputs/110_update_interpolation/diagnostic192.json) · [实现检查](../outputs/110_update_interpolation/implementation_checks.json)|192预测/32NA真实标签CE、有效BA cat两点各500、执行者自检|有压力收益与自然代价；无新训练/API，未升级默认；用户撤销自动关机|
|109_boundary_replay|[最终报告](../outputs/109_boundary_replay/final_report.md) · [完整指标](../outputs/109_boundary_replay/comparison.json) · [真实选样](../outputs/109_boundary_replay/mining_summary.json) · [执行自检](../outputs/109_boundary_replay/execution_selfcheck.json)|527真实预测、192条/24步续训、完整500；执行者自检非外部审计|当前配方无效，NA→NS塌缩；模型/完整状态回传，用户关机，不自动下一任务|
|108_semantic_hierarchy|[最终报告](../outputs/108_semantic_hierarchy/final_report.md) · [指标](../outputs/108_semantic_hierarchy/final_metrics.md) · [配对与病例](../outputs/108_semantic_hierarchy/gpu_analysis.md) · [自检](../outputs/108_semantic_hierarchy/final_selfcheck.json)|固定预测复算及1000患者配对，非外部独立审计|同资料GPU比较阴性，停止分层扩大；模型/完整状态回传，关机命令接受，账单待核；API0|
|107_support_aux|[当前报告](../outputs/107_support_aux/final_report.md) · [完整指标](../outputs/107_support_aux/final_metrics.md) · [协议](../tasks/107_support_aux/protocol.md)|[执行者自检](../outputs/107_support_aux/final_selfcheck.json)，非独立审计|两臂fresh各50步/500评价完成；GPU停费且CPU报告完成；API0，不自动下一任务|
|106_label_preparation|[一页决定](../outputs/106_label_preparation/decision.md) · [报告](../outputs/106_label_preparation/report.md) · [协议](../tasks/106_label_preparation/protocol.md) · [交接](../tasks/106_label_preparation/GPU_HANDOFF.md)|[执行者自检](../outputs/106_label_preparation/final_selfcheck.json)；[子代理反证复核](../outputs/106_label_preparation/adversarial_review.md)，非医生审计|仅研究/数据/CPU准备；推荐同196标签mean/sum诊断，0新增API/GPU，READY_FOR_NEXT_GPU_DECISION|
|105_brief_supervision|[最终报告](../outputs/105_brief_supervision/final_report.md) · [完整指标](../outputs/105_brief_supervision/final_metrics.md) · [源文案例](../outputs/105_brief_supervision/final_case_analysis.md)|[执行者自检](../outputs/105_brief_supervision/final_selfcheck.json)，非独立医生审计|两组训练、1500回执完成；短理由无增量，NA/false-S恶化；停止扩大，用户已关机|
|104_supervision_evidence|[一页结论](../outputs/104_supervision_evidence/summary.md) · [正式报告](../outputs/104_supervision_evidence/report.md) · [配对指纹](../outputs/104_supervision_evidence/paired_manifest.json)|[执行者自检](../outputs/104_supervision_evidence/selfcheck.json)；[有限工程复核](../reviews/104_supervision_evidence/engineering_review.md)，非医生审计|512盘点、288首审、196配对；64 API，额外盲复核8/16；不训练、不升级默认|
|103_lora_selection|[最终报告](../outputs/103_lora_selection/final_report.md) · [完整指标](../outputs/103_lora_selection/final_metrics.md) · [第一阶段](../outputs/103_lora_selection/report.md)|[执行者自检](../outputs/103_lora_selection/final_selfcheck.json)，非独立审计|9B/35B完成；27B停40条；自然提升伴随风险恶化，不直接全量训练；用户已关机|
|102_demo_relation|[报告](../outputs/102_demo_relation/report.md) · [关系核查](../outputs/102_demo_relation/method_review.md)|[执行者自检](../outputs/102_demo_relation/selfcheck.json)，独立审计未执行|零API；构造及预算核查后停止，未运行分类，不自动103|
|101_nsna_review|[正式报告](../outputs/101_nsna_review/report.md) · [病例](../outputs/101_nsna_review/case_analysis.md)|[执行者自检](../outputs/101_nsna_review/selfcheck.json)，独立审计未执行|plain：失败停止；review：失败停止；默认不变，不自动新实验|
|100_preregistered_followup|[一页结论](../outputs/100_preregistered_followup/night_summary_display.md) · [正式报告](../outputs/100_preregistered_followup/report_display.md)|[执行者自检](../outputs/100_preregistered_followup/selfcheck.json)，独立审计未执行|失败停止；32患者隔离确认，未升级默认，不自动新实验|
|099_judge_selection|[正式报告](../outputs/099_judge_selection/report.md) · [费用](../outputs/099_judge_selection/cost_ledger.json)|[执行者自检](../outputs/099_judge_selection/selfcheck.json)，独立审计未执行|四模型608 HTTP200；主35B-A3B、备27B，O优先但诊断/C48有代价；默认与098不变|
|098_p90_native_confirmation|[正式报告](../outputs/098_p90_native_confirmation/report_display.md) · [主表](../outputs/098_p90_native_confirmation/main_table.csv)|[执行者自检](../outputs/098_p90_native_confirmation/selfcheck.json)，独立审计未执行|全部冻结请求完成；demo_protect对verifact_ref/demo_lenmatch/compact48均未达门槛，压力/重复亦有失败，停止本版|
|097_native_judge_source_dependence|[正式报告](../outputs/097_native_judge_source_dependence/report.md) · [同ID表](../outputs/097_native_judge_source_dependence/a_same_id.csv)|[执行者自检](../outputs/097_native_judge_source_dependence/selfcheck.json)，独立审计未执行|同V4原生接口raw有信号但未超过B＋G；B构造与费用门槛未过，默认不变|
|096_r1_native_priorg|[正式报告](../outputs/096_r1_native_priorg/report.md) · [论文更新](../outputs/096_r1_native_priorg/manuscript_implications.md)|[执行者自检](../outputs/096_r1_native_priorg/valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k/selfcheck.json)，独立审计未执行|AWQ-Marlin1143 HTTP200；自然R1 raw599/800，适配595；停止适配、默认不变，不自动097|
|095_anchored_minimal_contrast|[总报告](../outputs/095_anchored_minimal_contrast/report.md)|[独立最终复核](../reviews/095_anchored_minimal_contrast/final_review.md)|统一9065母体B补齐与诊断；C构造语义失败，未运行分类，默认不变、不自动096|
|094_answer_isolated_verification|[正式报告](../outputs/094_answer_isolated_verification/report.md)|未执行；[执行者自检](../outputs/094_answer_isolated_verification/selfcheck.json)|B/V/Q首轮已完成，Q未证明优于B；停止本版，不自动095|
|093_lossless_evidence_budget|[正式报告](../outputs/093_lossless_evidence_budget/report.md)|未执行；[执行者自检](../outputs/093_lossless_evidence_budget/selfcheck.json)|真实B/F/A首轮完成；停止本版、默认不变，不自动094|
|001_dataset_audit|[成果入口](../outputs/001_dataset_audit/README.md)|[实际审计记录](../reviews/001_dataset_audit.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|002_reproduce_paper_results|[成果入口](../outputs/002_reproduce_paper_results/README.md)|[实际审计记录](../reviews/002_reproduce_paper_results.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|003_error_analysis|[成果入口](../outputs/003_error_analysis/README.md)|[实际审计记录](../reviews/003_error_analysis.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|004_event_alignment_pilot|[成果入口](../outputs/004_event_alignment_pilot/README.md)|[实际审计记录](../reviews/004_event_alignment_pilot.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|005_pilot_effect_analysis|[成果入口](../outputs/005_pilot_effect_analysis/README.md)|[实际审计记录](../reviews/005_pilot_effect_analysis.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|006_source_context_feasibility|[成果入口](../outputs/006_source_context_feasibility/README.md)|[实际审计记录](../reviews/006_source_context_feasibility.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|007_context_retrieval|[成果入口](../outputs/007_context_retrieval/README.md)|[实际审计记录](../reviews/007_context_retrieval.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|008_retrieval_planning|[成果入口](../outputs/008_retrieval_planning/README.md)|[实际审计记录](../reviews/008_retrieval_planning.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|009_retrieval_baselines|[成果入口](../outputs/009_retrieval_baselines/report.md)|[实际审计记录](../reviews/009_retrieval_baselines.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|010_verifact_baseline_alignment|[成果入口](../outputs/010_verifact_baseline_alignment/report.md)|[实际审计记录](../reviews/010_verifact_baseline_alignment.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|011_evidence_integrity_packaging|[成果入口](../outputs/011_evidence_integrity_packaging/report.md)|[实际审计记录](../reviews/011_evidence_integrity_packaging.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|012_comparative_error_diagnosis|[成果入口](../outputs/012_comparative_error_diagnosis/report.md)|[实际审计记录](../reviews/012_comparative_error_diagnosis.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|013_multi_mechanism_screen|[成果入口](../outputs/013_multi_mechanism_screen/report.md)|[实际审计记录](../reviews/013_multi_mechanism_screen.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|014_qwen27b_baseline_comparison|[成果入口](../outputs/014_qwen27b_baseline_comparison/report.md)|[实际审计记录](../reviews/014_qwen27b_baseline_comparison.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|015_disagreement_adjudication|[成果入口](../outputs/015_disagreement_adjudication/report.md)|[实际审计记录](../reviews/015_disagreement_adjudication.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|016_disagreement_triggered_review_validation|[成果入口](../outputs/016_disagreement_triggered_review_validation/completion_002/report.md)|[实际审计记录](../reviews/016_disagreement_triggered_review_validation.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|017_verification_supervised_evidence_utility|[成果入口](../outputs/017_verification_supervised_evidence_utility/report.md)|[实际审计记录](../reviews/017_verification_supervised_evidence_utility.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|018_verifact_gap_attribution|[成果入口](../outputs/018_verifact_gap_attribution/report.md)|[实际审计记录](../reviews/018_verifact_gap_attribution.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|019_support_boundary_screen|[成果入口](../outputs/019_support_boundary_screen/report.md)|[实际审计记录](../reviews/019_support_boundary_screen.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|020_lambda2_patient_validation|[成果入口](../outputs/020_lambda2_patient_validation/report.md)|[实际审计记录](../reviews/020_lambda2_patient_validation.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|021_bge_localization|[成果入口](../outputs/021_bge_localization/report.md)|[实际审计记录](../reviews/021_bge_localization.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|022_competition_aware_support_calibration|[成果入口](../outputs/022_competition_aware_support_calibration/report.md)|[实际审计记录](../reviews/022_competition_aware_support_calibration.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|023_lambda_boundary_response_analysis|[成果入口](../outputs/023_lambda_boundary_response_analysis/report.md)|[实际审计记录](../reviews/023_lambda_boundary_response_analysis.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|024_lambda2_transfer_validation|[成果入口](../outputs/024_lambda2_transfer_validation/report.md)|[实际审计记录](../reviews/024_lambda2_transfer_validation.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|025_lambda_flip_risk_separability|[成果入口](../outputs/025_lambda_flip_risk_separability/report.md)|[实际审计记录](../reviews/025_lambda_flip_risk_separability.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|026_frozen_sd_patient_transfer|[成果入口](../outputs/026_frozen_sd_patient_transfer/report.md)|[实际审计记录](../reviews/026_frozen_sd_patient_transfer.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|027_dual_judge_transfer_diagnosis|[成果入口](../outputs/027_dual_judge_transfer_diagnosis/report.md)|[实际审计记录](../reviews/027_dual_judge_transfer_diagnosis.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|028_traceable_claim_evidence_verification|[成果入口](../outputs/028_traceable_claim_evidence_verification/report.md)|[实际审计记录](../reviews/028_traceable_claim_evidence_verification.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|029_semantic_information_gate|[成果入口](../outputs/029_semantic_information_gate/report.md)|[实际审计记录](../reviews/029_semantic_information_gate.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|030_gate_training_stability|[成果入口](../outputs/030_gate_training_stability/report.md)|[实际审计记录](../reviews/030_gate_training_stability.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|031_training_expansion_confirmation|[成果入口](../outputs/031_training_expansion_confirmation/report.md)|[实际审计记录](../reviews/031_training_expansion_confirmation.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|032_evidence_relation_correction|[成果入口](../outputs/032_evidence_relation_correction/report.md)|[实际审计记录](../reviews/032_evidence_relation_correction.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|033_gate_training_subset|[成果入口](../outputs/033_gate_training_subset/report.md)|[实际审计记录](../reviews/033_gate_training_subset.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|034_same_data_comparison|[成果入口](../outputs/034_same_data_comparison/report.md)|[实际审计记录](../reviews/034_same_data_comparison.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|035_lambda_boundary_calibration|[成果入口](../outputs/035_lambda_boundary_calibration/report.md)|[实际审计记录](../reviews/035_lambda_boundary_calibration.md)|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|036_final_validation|[成果入口](../outputs/036_final_validation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|037_ns_na_decision|[成果入口](../outputs/037_ns_na_decision/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|038_evidence_explanation_audit|[成果入口](../outputs/038_evidence_explanation_audit/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|039_full_ehr_attribution|[成果入口](../outputs/039_full_ehr_attribution/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|040_route_decision|[成果入口](../outputs/040_route_decision/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|041_evidence_gated_explanation_sync|[成果入口](../outputs/041_evidence_gated_explanation_sync/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|042_coverage_aware_evidence_packing|[成果入口](../outputs/042_coverage_aware_evidence_packing/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|043_targeted_evidence_utility|[成果入口](../outputs/043_targeted_evidence_utility/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|044_incremental_evidence_recovery|[成果入口](../outputs/044_incremental_evidence_recovery/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|045_semantic_recovery_screen|[成果入口](../outputs/045_semantic_recovery_screen/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|046_requirement_aware_retrieval_screen|[成果入口](../outputs/046_requirement_aware_retrieval_screen/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|047_mechanism_stratified_validation|[成果入口](../outputs/047_mechanism_stratified_validation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|048_end_to_end_evidence_recovery|[成果入口](../outputs/048_end_to_end_evidence_recovery/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|049_evidence_decision_utilization|[成果入口](../outputs/049_evidence_decision_utilization/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|050_repeated_score_aggregation|[成果入口](../outputs/050_repeated_score_aggregation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|051_thinking_mode_validation|[成果入口](../outputs/051_thinking_mode_validation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|052_first_tier_validation|[成果入口](../outputs/052_first_tier_validation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|053_thinking_prior_validation|[成果入口](../outputs/053_thinking_prior_validation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|054_unlabeled_prior_shift|[成果入口](../outputs/054_unlabeled_prior_shift/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|055_zero_label_policy_adaptation|[成果入口](../outputs/055_zero_label_policy_adaptation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|056_shift_decomposition|[成果入口](../outputs/056_shift_decomposition/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|057_soft_shift_detection|[成果入口](../outputs/057_soft_shift_detection/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|058_unlabeled_batch_scaling|[成果入口](../outputs/058_unlabeled_batch_scaling/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|059_joint_prior_judge_drift|[成果入口](../outputs/059_joint_prior_judge_drift/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|060_class_specific_drift|[成果入口](../outputs/060_class_specific_drift/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|061_prior_anchored_drift|[成果入口](../outputs/061_prior_anchored_drift/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|062_low_rank_empirical_transport|[成果入口](../outputs/062_low_rank_empirical_transport/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|063_minimal_label_reliability|[成果入口](../outputs/063_minimal_label_reliability/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|064_safe_policy_selection|[成果入口](../outputs/064_safe_policy_selection/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|065_verification_evidence_construction|[成果入口](../outputs/065_verification_evidence_construction/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|066_oracle_headroom|[成果入口](../outputs/066_oracle_headroom/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|067_conservative_evidence_packing|[成果入口](../outputs/067_conservative_evidence_packing/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑；[069更正](../outputs/069_final_pack_controlled_repair/067_correction.md)|
|068_final_pack_utility_diagnosis|[成果入口](../outputs/068_final_pack_utility_diagnosis/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|069_final_pack_controlled_repair|[成果入口](../outputs/069_final_pack_controlled_repair/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|070_fixed_evidence_reasoning_diagnosis|[成果入口](../outputs/070_fixed_evidence_reasoning_diagnosis/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|071_judge_icl_feasibility|[成果入口](../outputs/071_judge_icl_feasibility/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|072_adaptive_judge_examples|[成果入口](../outputs/072_adaptive_judge_examples/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|073_clinical_example_matching|[成果入口](../outputs/073_clinical_example_matching/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|074_anchor_dynamic_examples|[成果入口](../outputs/074_anchor_dynamic_examples/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|075_annotated_static_examples|[成果入口](../outputs/075_annotated_static_examples/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|076_existing_results_synthesis|[成果入口](../outputs/076_existing_results_synthesis/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|077_static_example_discrimination|[成果入口](../outputs/077_static_example_discrimination/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|078_component_ablation|[成果入口](../outputs/078_component_ablation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|079_f4_priorg_adaptation|[成果入口](../outputs/079_f4_priorg_adaptation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|080_final_decision_adaptation|[成果入口](../outputs/080_final_decision_adaptation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|081_gt_blind_evidence_selection|[成果入口](../outputs/081_gt_blind_evidence_selection/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|082_anchor_configuration_adaptation|[成果入口](../outputs/082_anchor_configuration_adaptation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|083_native_rationale_information|[成果入口](../outputs/083_native_rationale_information/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|084_f4_coverage_validation|[成果入口](../outputs/084_f4_coverage_validation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|085_r1_70b_autodl|[成果入口](../outputs/085_r1_70b_valdemardi/report_formal.md)|未找到对应独立审计记录；自检不等于独立审计|这是旧Casperhansen/AWS准备分支，未作为正式运行主线；085正式结果已在Valdemardi分支完成。|
|085_r1_70b_model_swap|[成果入口](../outputs/085_r1_70b_valdemardi/report_formal.md)|未找到对应独立审计记录；自检不等于独立审计|这是旧Casperhansen/AWS准备分支，未作为正式运行主线；085正式结果已在Valdemardi分支完成。|
|085_r1_70b_valdemardi|[成果入口](../outputs/085_r1_70b_valdemardi/report_formal.md)|未找到对应独立审计记录；自检不等于独立审计|085 Valdemardi正式实验完成，默认未升级；不自动访问R1端点。|
|086_global_demonstration_selection|[成果入口](../outputs/086_global_demonstration_selection/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑；[087归因更正](../outputs/087_f4_evidence_intervention/086_correction.md)|
|087_f4_evidence_intervention|[成果入口](../outputs/087_f4_evidence_intervention/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|088_evidence_preserving_demonstration_compression|[成果入口](../outputs/088_evidence_preserving_demonstration_compression/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|089_source_audited_demo_compression|[成果入口](../outputs/089_source_audited_demo_compression/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|090_demo_constructor_repair_validation|[成果入口](../outputs/090_demo_constructor_repair_validation/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|091_integrated_evidence_decision_study|[成果入口](../outputs/091_integrated_evidence_decision_study/report.md)|未找到对应独立审计记录；自检不等于独立审计|历史任务；方法成败、阶段范围以正式成果为准，不自动续跑|
|092_task_adapted_verifier|[成果入口](../outputs/092_task_adapted_verifier/report.md)|未找到对应独立审计记录；自检不等于独立审计|092完整结项，默认未升级，无自动后续任务。|
