# 精简实验成果目录（2026-10-26）

本次只精简 research-verifact-simplified 的 outputs；原研究仓库未改动，镜像其余目录和根文件逐字节保留。
每个实验目录保留 1–5 份既有关键说明：正式报告、状态入口、重要性能表及必要更正；保留正负结果，不按效果好坏筛选。
保留文档沿用此前阅读镜像的脱敏版本，本次未改写其正文或数值；这不是完整复现实验包。代码、协议、审计仍在 tasks、src、reviews 等原位置。

清理前快照：[完整阅读镜像](https://github.com/Nicoodoz/research-verifact-simplified/tree/43f2d94be3bf0702bc2d8fbe54ea91c350695a14)。
删除的机器结果、图表、逐例记录及重复版本可回查该快照。历史正文中的相对链接可能指向已移除文件，请在上述快照中打开同路径。
根目录 MIRROR_MANIFEST.json、MIRROR_BUILD_REPORT.json 和旧阅读说明按用户边界原样保留，描述的是清理前构建；本次范围以本页和 CLEANUP_RECORD.md 为准。

**解释次序：067 必须结合 069/067_correction.md；086 必须结合 087/086_correction.md；083 结合 084/083_oof_diagnosis.md。085 的正式结果是 Valdemardi report_formal.md，其他两个085目录是历史准备。**

| 实验目录 | 主报告 | 保留文件数 |
|---|---|---:|
| 001_dataset_audit | [报告](001_dataset_audit/run_006/report.md) | 2 |
| 002_reproduce_paper_results | [报告](002_reproduce_paper_results/run_003/report.md) | 2 |
| 003_error_analysis | [报告](003_error_analysis/run_001/review_004/report.md) | 2 |
| 004_event_alignment_pilot | [报告](004_event_alignment_pilot/run_003/analysis/report.md) | 2 |
| 005_pilot_effect_analysis | [报告](005_pilot_effect_analysis/run_002/review_002/report.md) | 2 |
| 006_source_context_feasibility | [报告](006_source_context_feasibility/run_001/review_001/semantic_001/report.md) | 2 |
| 007_context_retrieval | [报告](007_context_retrieval/run_001/review_001/semantic_001/report.md) | 2 |
| 008_retrieval_planning | [报告](008_retrieval_planning/run_001/report.md) | 2 |
| 009_retrieval_baselines | [报告](009_retrieval_baselines/report.md) | 2 |
| 010_verifact_baseline_alignment | [报告](010_verifact_baseline_alignment/report.md) | 2 |
| 011_evidence_integrity_packaging | [报告](011_evidence_integrity_packaging/report.md) | 2 |
| 012_comparative_error_diagnosis | [报告](012_comparative_error_diagnosis/report.md) | 2 |
| 013_multi_mechanism_screen | [报告](013_multi_mechanism_screen/report.md) | 2 |
| 014_qwen27b_baseline_comparison | [报告](014_qwen27b_baseline_comparison/report.md) | 2 |
| 015_disagreement_adjudication | [报告](015_disagreement_adjudication/report.md) | 2 |
| 016_disagreement_triggered_review_validation | [报告](016_disagreement_triggered_review_validation/completion_002/report.md) | 2 |
| 017_verification_supervised_evidence_utility | [报告](017_verification_supervised_evidence_utility/report.md) | 2 |
| 018_verifact_gap_attribution | [报告](018_verifact_gap_attribution/report.md) | 3 |
| 019_support_boundary_screen | [报告](019_support_boundary_screen/report.md) | 3 |
| 020_lambda2_patient_validation | [报告](020_lambda2_patient_validation/report.md) | 3 |
| 021_bge_localization | [报告](021_bge_localization/report.md) | 2 |
| 022_competition_aware_support_calibration | [报告](022_competition_aware_support_calibration/report.md) | 3 |
| 023_lambda_boundary_response_analysis | [报告](023_lambda_boundary_response_analysis/report.md) | 3 |
| 024_lambda2_transfer_validation | [报告](024_lambda2_transfer_validation/report.md) | 2 |
| 025_lambda_flip_risk_separability | [报告](025_lambda_flip_risk_separability/report.md) | 2 |
| 026_frozen_sd_patient_transfer | [报告](026_frozen_sd_patient_transfer/report.md) | 2 |
| 027_dual_judge_transfer_diagnosis | [报告](027_dual_judge_transfer_diagnosis/report.md) | 2 |
| 028_traceable_claim_evidence_verification | [报告](028_traceable_claim_evidence_verification/report.md) | 2 |
| 029_semantic_information_gate | [报告](029_semantic_information_gate/report.md) | 2 |
| 030_gate_training_stability | [报告](030_gate_training_stability/report.md) | 2 |
| 031_training_expansion_confirmation | [报告](031_training_expansion_confirmation/report.md) | 2 |
| 032_evidence_relation_correction | [报告](032_evidence_relation_correction/report.md) | 2 |
| 033_gate_training_subset | [报告](033_gate_training_subset/report.md) | 2 |
| 034_same_data_comparison | [报告](034_same_data_comparison/report.md) | 3 |
| 035_lambda_boundary_calibration | [报告](035_lambda_boundary_calibration/report.md) | 3 |
| 036_final_validation | [报告](036_final_validation/report.md) | 4 |
| 037_ns_na_decision | [报告](037_ns_na_decision/report.md) | 2 |
| 038_evidence_explanation_audit | [报告](038_evidence_explanation_audit/report.md) | 2 |
| 039_full_ehr_attribution | [报告](039_full_ehr_attribution/report.md) | 2 |
| 040_route_decision | [报告](040_route_decision/report.md) | 2 |
| 041_evidence_gated_explanation_sync | [报告](041_evidence_gated_explanation_sync/report.md) | 2 |
| 042_coverage_aware_evidence_packing | [报告](042_coverage_aware_evidence_packing/report.md) | 2 |
| 043_targeted_evidence_utility | [报告](043_targeted_evidence_utility/report.md) | 2 |
| 044_incremental_evidence_recovery | [报告](044_incremental_evidence_recovery/report.md) | 2 |
| 045_semantic_recovery_screen | [报告](045_semantic_recovery_screen/report.md) | 2 |
| 046_requirement_aware_retrieval_screen | [报告](046_requirement_aware_retrieval_screen/report.md) | 2 |
| 047_mechanism_stratified_validation | [报告](047_mechanism_stratified_validation/report.md) | 2 |
| 048_end_to_end_evidence_recovery | [报告](048_end_to_end_evidence_recovery/report.md) | 2 |
| 049_evidence_decision_utilization | [报告](049_evidence_decision_utilization/report.md) | 2 |
| 050_repeated_score_aggregation | [报告](050_repeated_score_aggregation/report.md) | 2 |
| 051_thinking_mode_validation | [报告](051_thinking_mode_validation/report.md) | 2 |
| 052_first_tier_validation | [报告](052_first_tier_validation/report.md) | 2 |
| 053_thinking_prior_validation | [报告](053_thinking_prior_validation/report.md) | 2 |
| 054_unlabeled_prior_shift | [报告](054_unlabeled_prior_shift/report.md) | 2 |
| 055_zero_label_policy_adaptation | [报告](055_zero_label_policy_adaptation/report.md) | 2 |
| 056_shift_decomposition | [报告](056_shift_decomposition/report.md) | 2 |
| 057_soft_shift_detection | [报告](057_soft_shift_detection/report.md) | 2 |
| 058_unlabeled_batch_scaling | [报告](058_unlabeled_batch_scaling/report.md) | 2 |
| 059_joint_prior_judge_drift | [报告](059_joint_prior_judge_drift/report.md) | 2 |
| 060_class_specific_drift | [报告](060_class_specific_drift/report.md) | 2 |
| 061_prior_anchored_drift | [报告](061_prior_anchored_drift/report.md) | 2 |
| 062_low_rank_empirical_transport | [报告](062_low_rank_empirical_transport/report.md) | 2 |
| 063_minimal_label_reliability | [报告](063_minimal_label_reliability/report.md) | 3 |
| 064_safe_policy_selection | [报告](064_safe_policy_selection/report.md) | 4 |
| 065_verification_evidence_construction | [报告](065_verification_evidence_construction/report.md) | 2 |
| 066_oracle_headroom | [报告](066_oracle_headroom/report.md) | 2 |
| 067_conservative_evidence_packing | [报告](067_conservative_evidence_packing/report.md) | 4 |
| 068_final_pack_utility_diagnosis | [报告](068_final_pack_utility_diagnosis/report.md) | 2 |
| 069_final_pack_controlled_repair | [报告](069_final_pack_controlled_repair/report.md) | 3 |
| 070_fixed_evidence_reasoning_diagnosis | [报告](070_fixed_evidence_reasoning_diagnosis/report.md) | 2 |
| 071_judge_icl_feasibility | [报告](071_judge_icl_feasibility/report.md) | 3 |
| 072_adaptive_judge_examples | [报告](072_adaptive_judge_examples/report.md) | 4 |
| 073_clinical_example_matching | [报告](073_clinical_example_matching/report.md) | 2 |
| 074_anchor_dynamic_examples | [报告](074_anchor_dynamic_examples/report.md) | 2 |
| 075_annotated_static_examples | [报告](075_annotated_static_examples/report.md) | 2 |
| 076_existing_results_synthesis | [报告](076_existing_results_synthesis/report.md) | 4 |
| 077_static_example_discrimination | [报告](077_static_example_discrimination/report.md) | 3 |
| 078_component_ablation | [报告](078_component_ablation/report.md) | 5 |
| 079_f4_priorg_adaptation | [报告](079_f4_priorg_adaptation/report.md) | 3 |
| 080_final_decision_adaptation | [报告](080_final_decision_adaptation/report.md) | 4 |
| 081_gt_blind_evidence_selection | [报告](081_gt_blind_evidence_selection/report.md) | 2 |
| 082_anchor_configuration_adaptation | [报告](082_anchor_configuration_adaptation/report.md) | 3 |
| 083_native_rationale_information | [报告](083_native_rationale_information/report.md) | 3 |
| 084_f4_coverage_validation | [报告](084_f4_coverage_validation/report.md) | 4 |
| 085_r1_70b_autodl | [报告](085_r1_70b_autodl/report_offline.md) | 1 |
| 085_r1_70b_model_swap | [报告](085_r1_70b_model_swap/report_predeploy.md) | 3 |
| 085_r1_70b_valdemardi | [报告](085_r1_70b_valdemardi/report_formal.md) | 3 |
| 086_global_demonstration_selection | [报告](086_global_demonstration_selection/report.md) | 2 |
| 087_f4_evidence_intervention | [报告](087_f4_evidence_intervention/report.md) | 5 |
| 088_evidence_preserving_demonstration_compression | [报告](088_evidence_preserving_demonstration_compression/report.md) | 2 |
| 089_source_audited_demo_compression | [报告](089_source_audited_demo_compression/report.md) | 4 |
| 090_demo_constructor_repair_validation | [报告](090_demo_constructor_repair_validation/report.md) | 5 |
| 091_integrated_evidence_decision_study | [报告](091_integrated_evidence_decision_study/report.md) | 3 |
| 092_task_adapted_verifier | [报告](092_task_adapted_verifier/report.md) | 5 |
| 093_lossless_evidence_budget | [报告](093_lossless_evidence_budget/report.md) | 4 |
| 094_answer_isolated_verification | [报告](094_answer_isolated_verification/report.md) | 4 |
| 095_anchored_minimal_contrast | [报告](095_anchored_minimal_contrast/report.md) | 5 |
| 096_r1_native_priorg | [报告](096_r1_native_priorg/report.md) | 4 |
| 097_native_judge_source_dependence | [报告](097_native_judge_source_dependence/report.md) | 3 |
