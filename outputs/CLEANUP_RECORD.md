# outputs 精简核验

- 基线提交：`43f2d94be3bf0702bc2d8fbe54ea91c350695a14`。
- 范围：仅替换 outputs 子树；其余根文件与目录 Git 对象保持不变。
- 清理前：2,104 个文件，26,626,388 字节。
- 保留既有 Markdown：252 份，1,533,502 字节；另新增本核验说明与 README 索引。
- 移除：1,852 个文件。删除不改写历史提交。
- 覆盖001–097全部97个任务编号、99个任务目录；085三个历史/正式分支分别保留，不混淆。
- 选择原则：正式报告优先，早期实验按现行入口指定的最终报告保留；关键性能补表、机制失败说明和更正优先。
- 不保留：JSON/CSV数组与逐例机器明细、图片、重复运行、旧状态副本、运输/服务探针等。
- 保留文档使用既有 blob SHA；正文不重写，不从未脱敏原库重新导入临床内容。
- 删除文件保存在基线提交中；保留文档的历史链接不会为精简版重新篡改。
- 本轮没有收费API、重跑实验、模型升级、修改.gitignore或原仓库提交。
- 本核验是执行者结构自检，不是独立研究审计。

| 实验目录 | 保留说明文档 |
|---|---|
| 001_dataset_audit | [README.md](001_dataset_audit/README.md) · [run_006/report.md](001_dataset_audit/run_006/report.md) |
| 002_reproduce_paper_results | [README.md](002_reproduce_paper_results/README.md) · [run_003/report.md](002_reproduce_paper_results/run_003/report.md) |
| 003_error_analysis | [README.md](003_error_analysis/README.md) · [run_001/review_004/report.md](003_error_analysis/run_001/review_004/report.md) |
| 004_event_alignment_pilot | [README.md](004_event_alignment_pilot/README.md) · [run_003/analysis/report.md](004_event_alignment_pilot/run_003/analysis/report.md) |
| 005_pilot_effect_analysis | [README.md](005_pilot_effect_analysis/README.md) · [run_002/review_002/report.md](005_pilot_effect_analysis/run_002/review_002/report.md) |
| 006_source_context_feasibility | [README.md](006_source_context_feasibility/README.md) · [run_001/review_001/semantic_001/report.md](006_source_context_feasibility/run_001/review_001/semantic_001/report.md) |
| 007_context_retrieval | [README.md](007_context_retrieval/README.md) · [run_001/review_001/semantic_001/report.md](007_context_retrieval/run_001/review_001/semantic_001/report.md) |
| 008_retrieval_planning | [README.md](008_retrieval_planning/README.md) · [run_001/report.md](008_retrieval_planning/run_001/report.md) |
| 009_retrieval_baselines | [README.md](009_retrieval_baselines/README.md) · [report.md](009_retrieval_baselines/report.md) |
| 010_verifact_baseline_alignment | [README.md](010_verifact_baseline_alignment/README.md) · [report.md](010_verifact_baseline_alignment/report.md) |
| 011_evidence_integrity_packaging | [README.md](011_evidence_integrity_packaging/README.md) · [report.md](011_evidence_integrity_packaging/report.md) |
| 012_comparative_error_diagnosis | [README.md](012_comparative_error_diagnosis/README.md) · [report.md](012_comparative_error_diagnosis/report.md) |
| 013_multi_mechanism_screen | [README.md](013_multi_mechanism_screen/README.md) · [report.md](013_multi_mechanism_screen/report.md) |
| 014_qwen27b_baseline_comparison | [README.md](014_qwen27b_baseline_comparison/README.md) · [report.md](014_qwen27b_baseline_comparison/report.md) |
| 015_disagreement_adjudication | [README.md](015_disagreement_adjudication/README.md) · [report.md](015_disagreement_adjudication/report.md) |
| 016_disagreement_triggered_review_validation | [CURRENT.md](016_disagreement_triggered_review_validation/CURRENT.md) · [completion_002/report.md](016_disagreement_triggered_review_validation/completion_002/report.md) |
| 017_verification_supervised_evidence_utility | [README.md](017_verification_supervised_evidence_utility/README.md) · [report.md](017_verification_supervised_evidence_utility/report.md) |
| 018_verifact_gap_attribution | [README.md](018_verifact_gap_attribution/README.md) · [report.md](018_verifact_gap_attribution/report.md) · [statistics.md](018_verifact_gap_attribution/statistics.md) |
| 019_support_boundary_screen | [CURRENT.md](019_support_boundary_screen/CURRENT.md) · [report.md](019_support_boundary_screen/report.md) · [statistics.md](019_support_boundary_screen/statistics.md) |
| 020_lambda2_patient_validation | [CURRENT.md](020_lambda2_patient_validation/CURRENT.md) · [report.md](020_lambda2_patient_validation/report.md) · [statistics.md](020_lambda2_patient_validation/statistics.md) |
| 021_bge_localization | [CURRENT.md](021_bge_localization/CURRENT.md) · [report.md](021_bge_localization/report.md) |
| 022_competition_aware_support_calibration | [CURRENT_STATUS.md](022_competition_aware_support_calibration/CURRENT_STATUS.md) · [report.md](022_competition_aware_support_calibration/report.md) · [statistics.md](022_competition_aware_support_calibration/statistics.md) |
| 023_lambda_boundary_response_analysis | [CURRENT_STATUS.md](023_lambda_boundary_response_analysis/CURRENT_STATUS.md) · [report.md](023_lambda_boundary_response_analysis/report.md) · [statistics.md](023_lambda_boundary_response_analysis/statistics.md) |
| 024_lambda2_transfer_validation | [CURRENT_STATUS.md](024_lambda2_transfer_validation/CURRENT_STATUS.md) · [report.md](024_lambda2_transfer_validation/report.md) |
| 025_lambda_flip_risk_separability | [CURRENT_STATUS.md](025_lambda_flip_risk_separability/CURRENT_STATUS.md) · [report.md](025_lambda_flip_risk_separability/report.md) |
| 026_frozen_sd_patient_transfer | [CURRENT_STATUS.md](026_frozen_sd_patient_transfer/CURRENT_STATUS.md) · [report.md](026_frozen_sd_patient_transfer/report.md) |
| 027_dual_judge_transfer_diagnosis | [CURRENT_STATUS.md](027_dual_judge_transfer_diagnosis/CURRENT_STATUS.md) · [report.md](027_dual_judge_transfer_diagnosis/report.md) |
| 028_traceable_claim_evidence_verification | [CURRENT_STATUS.md](028_traceable_claim_evidence_verification/CURRENT_STATUS.md) · [report.md](028_traceable_claim_evidence_verification/report.md) |
| 029_semantic_information_gate | [CURRENT_STATUS.md](029_semantic_information_gate/CURRENT_STATUS.md) · [report.md](029_semantic_information_gate/report.md) |
| 030_gate_training_stability | [CURRENT_STATUS.md](030_gate_training_stability/CURRENT_STATUS.md) · [report.md](030_gate_training_stability/report.md) |
| 031_training_expansion_confirmation | [CURRENT_STATUS.md](031_training_expansion_confirmation/CURRENT_STATUS.md) · [report.md](031_training_expansion_confirmation/report.md) |
| 032_evidence_relation_correction | [CURRENT_STATUS.md](032_evidence_relation_correction/CURRENT_STATUS.md) · [report.md](032_evidence_relation_correction/report.md) |
| 033_gate_training_subset | [CURRENT_STATUS.md](033_gate_training_subset/CURRENT_STATUS.md) · [report.md](033_gate_training_subset/report.md) |
| 034_same_data_comparison | [CURRENT_STATUS_002.md](034_same_data_comparison/CURRENT_STATUS_002.md) · [lambda_extension_001/run_001/report.md](034_same_data_comparison/lambda_extension_001/run_001/report.md) · [report.md](034_same_data_comparison/report.md) |
| 035_lambda_boundary_calibration | [CURRENT_STATUS_002.md](035_lambda_boundary_calibration/CURRENT_STATUS_002.md) · [erratum_001.md](035_lambda_boundary_calibration/erratum_001.md) · [report.md](035_lambda_boundary_calibration/report.md) |
| 036_final_validation | [CURRENT_STATUS.md](036_final_validation/CURRENT_STATUS.md) · [methods_and_settings.md](036_final_validation/methods_and_settings.md) · [paper_tables.md](036_final_validation/paper_tables.md) · [report.md](036_final_validation/report.md) |
| 037_ns_na_decision | [CURRENT_STATUS.md](037_ns_na_decision/CURRENT_STATUS.md) · [report.md](037_ns_na_decision/report.md) |
| 038_evidence_explanation_audit | [CURRENT_STATUS.md](038_evidence_explanation_audit/CURRENT_STATUS.md) · [report.md](038_evidence_explanation_audit/report.md) |
| 039_full_ehr_attribution | [CURRENT_STATUS.md](039_full_ehr_attribution/CURRENT_STATUS.md) · [report.md](039_full_ehr_attribution/report.md) |
| 040_route_decision | [CURRENT_STATUS.md](040_route_decision/CURRENT_STATUS.md) · [report.md](040_route_decision/report.md) |
| 041_evidence_gated_explanation_sync | [CURRENT_STATUS.md](041_evidence_gated_explanation_sync/CURRENT_STATUS.md) · [report.md](041_evidence_gated_explanation_sync/report.md) |
| 042_coverage_aware_evidence_packing | [CURRENT_STATUS.md](042_coverage_aware_evidence_packing/CURRENT_STATUS.md) · [report.md](042_coverage_aware_evidence_packing/report.md) |
| 043_targeted_evidence_utility | [CURRENT_STATUS.md](043_targeted_evidence_utility/CURRENT_STATUS.md) · [report.md](043_targeted_evidence_utility/report.md) |
| 044_incremental_evidence_recovery | [CURRENT_STATUS.md](044_incremental_evidence_recovery/CURRENT_STATUS.md) · [report.md](044_incremental_evidence_recovery/report.md) |
| 045_semantic_recovery_screen | [CURRENT_STATUS.md](045_semantic_recovery_screen/CURRENT_STATUS.md) · [report.md](045_semantic_recovery_screen/report.md) |
| 046_requirement_aware_retrieval_screen | [CURRENT_STATUS.md](046_requirement_aware_retrieval_screen/CURRENT_STATUS.md) · [report.md](046_requirement_aware_retrieval_screen/report.md) |
| 047_mechanism_stratified_validation | [CURRENT_STATUS.md](047_mechanism_stratified_validation/CURRENT_STATUS.md) · [report.md](047_mechanism_stratified_validation/report.md) |
| 048_end_to_end_evidence_recovery | [CURRENT_STATUS.md](048_end_to_end_evidence_recovery/CURRENT_STATUS.md) · [report.md](048_end_to_end_evidence_recovery/report.md) |
| 049_evidence_decision_utilization | [CURRENT_STATUS.md](049_evidence_decision_utilization/CURRENT_STATUS.md) · [report.md](049_evidence_decision_utilization/report.md) |
| 050_repeated_score_aggregation | [CURRENT_STATUS.md](050_repeated_score_aggregation/CURRENT_STATUS.md) · [report.md](050_repeated_score_aggregation/report.md) |
| 051_thinking_mode_validation | [CURRENT_STATUS.md](051_thinking_mode_validation/CURRENT_STATUS.md) · [report.md](051_thinking_mode_validation/report.md) |
| 052_first_tier_validation | [CURRENT_STATUS.md](052_first_tier_validation/CURRENT_STATUS.md) · [report.md](052_first_tier_validation/report.md) |
| 053_thinking_prior_validation | [CURRENT_STATUS.md](053_thinking_prior_validation/CURRENT_STATUS.md) · [report.md](053_thinking_prior_validation/report.md) |
| 054_unlabeled_prior_shift | [CURRENT_STATUS.md](054_unlabeled_prior_shift/CURRENT_STATUS.md) · [report.md](054_unlabeled_prior_shift/report.md) |
| 055_zero_label_policy_adaptation | [CURRENT_STATUS.md](055_zero_label_policy_adaptation/CURRENT_STATUS.md) · [report.md](055_zero_label_policy_adaptation/report.md) |
| 056_shift_decomposition | [CURRENT_STATUS.md](056_shift_decomposition/CURRENT_STATUS.md) · [report.md](056_shift_decomposition/report.md) |
| 057_soft_shift_detection | [CURRENT_STATUS.md](057_soft_shift_detection/CURRENT_STATUS.md) · [report.md](057_soft_shift_detection/report.md) |
| 058_unlabeled_batch_scaling | [CURRENT_STATUS.md](058_unlabeled_batch_scaling/CURRENT_STATUS.md) · [report.md](058_unlabeled_batch_scaling/report.md) |
| 059_joint_prior_judge_drift | [CURRENT_STATUS.md](059_joint_prior_judge_drift/CURRENT_STATUS.md) · [report.md](059_joint_prior_judge_drift/report.md) |
| 060_class_specific_drift | [CURRENT_STATUS.md](060_class_specific_drift/CURRENT_STATUS.md) · [report.md](060_class_specific_drift/report.md) |
| 061_prior_anchored_drift | [CURRENT_STATUS.md](061_prior_anchored_drift/CURRENT_STATUS.md) · [report.md](061_prior_anchored_drift/report.md) |
| 062_low_rank_empirical_transport | [CURRENT_STATUS.md](062_low_rank_empirical_transport/CURRENT_STATUS.md) · [report.md](062_low_rank_empirical_transport/report.md) |
| 063_minimal_label_reliability | [CURRENT_STATUS.md](063_minimal_label_reliability/CURRENT_STATUS.md) · [report.md](063_minimal_label_reliability/report.md) · [soft_report.md](063_minimal_label_reliability/soft_report.md) |
| 064_safe_policy_selection | [CURRENT_STATUS.md](064_safe_policy_selection/CURRENT_STATUS.md) · [future_report.md](064_safe_policy_selection/future_report.md) · [future_v2_report.md](064_safe_policy_selection/future_v2_report.md) · [report.md](064_safe_policy_selection/report.md) |
| 065_verification_evidence_construction | [CURRENT_STATUS.md](065_verification_evidence_construction/CURRENT_STATUS.md) · [report.md](065_verification_evidence_construction/report.md) |
| 066_oracle_headroom | [CURRENT_STATUS.md](066_oracle_headroom/CURRENT_STATUS.md) · [report.md](066_oracle_headroom/report.md) |
| 067_conservative_evidence_packing | [CURRENT_STATUS.md](067_conservative_evidence_packing/CURRENT_STATUS.md) · [execution_note_002.md](067_conservative_evidence_packing/execution_note_002.md) · [report.md](067_conservative_evidence_packing/report.md) · [report_final.md](067_conservative_evidence_packing/report_final.md) |
| 068_final_pack_utility_diagnosis | [CURRENT_STATUS.md](068_final_pack_utility_diagnosis/CURRENT_STATUS.md) · [report.md](068_final_pack_utility_diagnosis/report.md) |
| 069_final_pack_controlled_repair | [067_correction.md](069_final_pack_controlled_repair/067_correction.md) · [CURRENT_STATUS.md](069_final_pack_controlled_repair/CURRENT_STATUS.md) · [report.md](069_final_pack_controlled_repair/report.md) |
| 070_fixed_evidence_reasoning_diagnosis | [CURRENT_STATUS.md](070_fixed_evidence_reasoning_diagnosis/CURRENT_STATUS.md) · [report.md](070_fixed_evidence_reasoning_diagnosis/report.md) |
| 071_judge_icl_feasibility | [CURRENT_STATUS.md](071_judge_icl_feasibility/CURRENT_STATUS.md) · [prompt_comparison.md](071_judge_icl_feasibility/prompt_comparison.md) · [report.md](071_judge_icl_feasibility/report.md) |
| 072_adaptive_judge_examples | [CURRENT_STATUS.md](072_adaptive_judge_examples/CURRENT_STATUS.md) · [confirmation_decision.md](072_adaptive_judge_examples/confirmation_decision.md) · [report.md](072_adaptive_judge_examples/report.md) · [source_scope_note.md](072_adaptive_judge_examples/source_scope_note.md) |
| 073_clinical_example_matching | [CURRENT_STATUS.md](073_clinical_example_matching/CURRENT_STATUS.md) · [report.md](073_clinical_example_matching/report.md) |
| 074_anchor_dynamic_examples | [CURRENT_STATUS.md](074_anchor_dynamic_examples/CURRENT_STATUS.md) · [report.md](074_anchor_dynamic_examples/report.md) |
| 075_annotated_static_examples | [CURRENT_STATUS.md](075_annotated_static_examples/CURRENT_STATUS.md) · [report.md](075_annotated_static_examples/report.md) |
| 076_existing_results_synthesis | [CURRENT_STATUS.md](076_existing_results_synthesis/CURRENT_STATUS.md) · [evidence_map.md](076_existing_results_synthesis/evidence_map.md) · [numeric_appendix.md](076_existing_results_synthesis/numeric_appendix.md) · [report.md](076_existing_results_synthesis/report.md) |
| 077_static_example_discrimination | [CURRENT_STATUS.md](077_static_example_discrimination/CURRENT_STATUS.md) · [numeric_appendix.md](077_static_example_discrimination/numeric_appendix.md) · [report.md](077_static_example_discrimination/report.md) |
| 078_component_ablation | [CURRENT_STATUS.md](078_component_ablation/CURRENT_STATUS.md) · [f4_extension_001/performance_tables.md](078_component_ablation/f4_extension_001/performance_tables.md) · [f4_extension_001/report.md](078_component_ablation/f4_extension_001/report.md) · [performance_tables.md](078_component_ablation/performance_tables.md) · [report.md](078_component_ablation/report.md) |
| 079_f4_priorg_adaptation | [CURRENT_STATUS.md](079_f4_priorg_adaptation/CURRENT_STATUS.md) · [performance_tables.md](079_f4_priorg_adaptation/performance_tables.md) · [report.md](079_f4_priorg_adaptation/report.md) |
| 080_final_decision_adaptation | [CURRENT_STATUS.md](080_final_decision_adaptation/CURRENT_STATUS.md) · [class_metrics.md](080_final_decision_adaptation/class_metrics.md) · [performance_tables.md](080_final_decision_adaptation/performance_tables.md) · [report.md](080_final_decision_adaptation/report.md) |
| 081_gt_blind_evidence_selection | [CURRENT_STATUS.md](081_gt_blind_evidence_selection/CURRENT_STATUS.md) · [report.md](081_gt_blind_evidence_selection/report.md) |
| 082_anchor_configuration_adaptation | [CURRENT_STATUS.md](082_anchor_configuration_adaptation/CURRENT_STATUS.md) · [executive_summary.md](082_anchor_configuration_adaptation/executive_summary.md) · [report.md](082_anchor_configuration_adaptation/report.md) |
| 083_native_rationale_information | [CURRENT_STATUS.md](083_native_rationale_information/CURRENT_STATUS.md) · [executive_summary.md](083_native_rationale_information/executive_summary.md) · [report.md](083_native_rationale_information/report.md) |
| 084_f4_coverage_validation | [083_oof_diagnosis.md](084_f4_coverage_validation/083_oof_diagnosis.md) · [CURRENT_STATUS.md](084_f4_coverage_validation/CURRENT_STATUS.md) · [coverage_inventory.md](084_f4_coverage_validation/coverage_inventory.md) · [report.md](084_f4_coverage_validation/report.md) |
| 085_r1_70b_autodl | [report_offline.md](085_r1_70b_autodl/report_offline.md) |
| 085_r1_70b_model_swap | [README.md](085_r1_70b_model_swap/README.md) · [report_predeploy.md](085_r1_70b_model_swap/report_predeploy.md) · [tokenizer_length_audit.md](085_r1_70b_model_swap/tokenizer_length_audit.md) |
| 085_r1_70b_valdemardi | [CURRENT_STATUS.md](085_r1_70b_valdemardi/CURRENT_STATUS.md) · [completion_metadata_correction.md](085_r1_70b_valdemardi/completion_metadata_correction.md) · [report_formal.md](085_r1_70b_valdemardi/report_formal.md) |
| 086_global_demonstration_selection | [README.md](086_global_demonstration_selection/README.md) · [report.md](086_global_demonstration_selection/report.md) |
| 087_f4_evidence_intervention | [086_correction.md](087_f4_evidence_intervention/086_correction.md) · [README.md](087_f4_evidence_intervention/README.md) · [cost_tables.md](087_f4_evidence_intervention/cost_tables.md) · [performance_tables.md](087_f4_evidence_intervention/performance_tables.md) · [report.md](087_f4_evidence_intervention/report.md) |
| 088_evidence_preserving_demonstration_compression | [README.md](088_evidence_preserving_demonstration_compression/README.md) · [report.md](088_evidence_preserving_demonstration_compression/report.md) |
| 089_source_audited_demo_compression | [cost_tables.md](089_source_audited_demo_compression/cost_tables.md) · [coverage_semantic_review.md](089_source_audited_demo_compression/coverage_semantic_review.md) · [performance_tables.md](089_source_audited_demo_compression/performance_tables.md) · [report.md](089_source_audited_demo_compression/report.md) |
| 090_demo_constructor_repair_validation | [CURRENT_STATUS.md](090_demo_constructor_repair_validation/CURRENT_STATUS.md) · [cost_tables.md](090_demo_constructor_repair_validation/cost_tables.md) · [performance_tables.md](090_demo_constructor_repair_validation/performance_tables.md) · [report.md](090_demo_constructor_repair_validation/report.md) · [results_map_084_090.md](090_demo_constructor_repair_validation/results_map_084_090.md) |
| 091_integrated_evidence_decision_study | [B_tables.md](091_integrated_evidence_decision_study/B_tables.md) · [C_feasibility.md](091_integrated_evidence_decision_study/C_feasibility.md) · [report.md](091_integrated_evidence_decision_study/report.md) |
| 092_task_adapted_verifier | [CURRENT_STATUS.md](092_task_adapted_verifier/CURRENT_STATUS.md) · [architecture.md](092_task_adapted_verifier/architecture.md) · [detailed_tables.md](092_task_adapted_verifier/detailed_tables.md) · [method_positioning.md](092_task_adapted_verifier/method_positioning.md) · [report.md](092_task_adapted_verifier/report.md) |
| 093_lossless_evidence_budget | [detailed_tables.md](093_lossless_evidence_budget/detailed_tables.md) · [history_difference.md](093_lossless_evidence_budget/history_difference.md) · [method.md](093_lossless_evidence_budget/method.md) · [report.md](093_lossless_evidence_budget/report.md) |
| 094_answer_isolated_verification | [detailed_tables.md](094_answer_isolated_verification/detailed_tables.md) · [history_difference.md](094_answer_isolated_verification/history_difference.md) · [report.md](094_answer_isolated_verification/report.md) · [source_locator_correction.md](094_answer_isolated_verification/source_locator_correction.md) |
| 095_anchored_minimal_contrast | [CURRENT_STATUS.md](095_anchored_minimal_contrast/CURRENT_STATUS.md) · [baseline_findings.md](095_anchored_minimal_contrast/baseline_findings.md) · [detailed_tables.md](095_anchored_minimal_contrast/detailed_tables.md) · [manuscript_zh.md](095_anchored_minimal_contrast/manuscript_zh.md) · [report.md](095_anchored_minimal_contrast/report.md) |
| 096_r1_native_priorg | [CURRENT_STATUS.md](096_r1_native_priorg/CURRENT_STATUS.md) · [manuscript_implications.md](096_r1_native_priorg/manuscript_implications.md) · [report.md](096_r1_native_priorg/report.md) · [valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k/publication_tables.md](096_r1_native_priorg/valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k/publication_tables.md) |
| 097_native_judge_source_dependence | [b_matched_ablation.md](097_native_judge_source_dependence/b_matched_ablation.md) · [report.md](097_native_judge_source_dependence/report.md) · [source_alignment.md](097_native_judge_source_dependence/source_alignment.md) |
