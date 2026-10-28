"""Prepare the one selected label-objective diagnostic; never launches a service."""
import copy
import common106 as c


def main():
    previous=c.read(c.ROOT/'tasks/105_brief_supervision/config.json')
    if (c.TASK/'config.json').exists():
        old=c.read(c.TASK/'config.json')
        if old.get('design',{}).get('sole_main_change')=='training_example_selection':
            c.put(c.PRIVATE/'drafts_data_design/config.json',old)
    config=copy.deepcopy(previous)
    config['task']=106
    # The control's legacy loss/ordering definition remains exactly 105.
    config['training']['candidate_loss']='verdict_value_sum_CE_div_fixed_global_mean_length_plus_other_answer_mean_CE'
    config['training']['value_token_mean_normalizer']=360/196
    config['training_N']=196
    config['trainable_arms']=['label_sum']
    config['control_arm']='label_mean'
    config['evaluation']['arms']=['base_judge',*c.ARMS]
    config['evaluation']['old_predictions_reused']=True
    config['evaluation']['old_predictions_policy']='105 base and label_only196 exact cached first answers only under frozen runtime/input/batch/parser conditions; different runtime reruns both evaluations without retraining control'
    config['design']=dict(
        sole_main_change='verdict_value_token_mean_vs_globally_normalized_sum',
        arms=list(c.ARMS), per_arm_N=196,
        quotas=dict(zip(c.LABELS,[83,62,51])),
        exact_same_training_ID_order_claim_GT_reference_prompt=True,
        global_verdict_length_sum=360, global_normalizer=360/196,
        global_mean_verdict_segment_weight_preserved=True,
        teacher_errors_are_current_9b_training_errors=False,
        relation_proxy_not_new_doctor_gold=True,
        explicit_class_weights_used=False,false_S_risk_loss_used=False,
        control_implicit_verdict_length_weights=dict(zip(c.LABELS,[1,1/2,1/3])),
        initialization='label_sum_from_original_9b; label_mean_frozen105_original_base_training_control',
        control_adapter_is_never_candidate_initialization=True,
        candidate_data512_prepared_but_inactive=True,
        train_patients=40, selection_patients=20,
        confirmation_patients_new_access=False,
        original_claim_GT_reference_unchanged=True)
    config['preparation']=dict(status='READY_FOR_NEXT_GPU_DECISION',GPU_authorized=False,
        paid_API_cap_cny=10,paid_API_actual_cny=0,
        current_service_clinical_processing_confirmed_by_user=True,
        automatic_start_or_default_upgrade=False)
    config['budget']['planning_only_not_GPU_authorization']=True
    c.put(c.TASK/'config.json',config)
    c.put(c.OUT/'api_cost_ledger.json',dict(task=106,cap_cny=10,directory_price_cny=0,
        attempts=0,successful=0,retries=0,unknown_reserve_cny=0,inflight_cny=0,
        clinical_text_sent_to_separate_API=False,model_probe_calls=0,GPU_calls=0,
        previous_budgets_not_carried_forward=True))
    print(c.canonical(dict(task=106,config_sha256=c.sha(c.TASK/'config.json'),API_actual_cny=0,GPU_authorized=False)))


if __name__=='__main__':main()
