"""CPU planning from actual 105 timings; prices are scenarios, not authorization."""
import common106 as c


def main():
    old=c.ROOT/'outputs/105_brief_supervision'
    r=c.read(old/'a800_resources.json')
    lengths=[v for v in c.rows(old/'train_token_lengths.jsonl') if v['arm']=='label_only']
    assert len(lengths)==196
    tokens=2*sum(v['total_tokens'] for v in lengths)
    speed=r['training']['label_only']['steady_tokens_per_second']
    train=tokens/speed
    short_eval=r['evaluation']['label_only']['generation_seconds']
    long_eval=r['evaluation']['base_judge']['generation_seconds']
    rate=7.98
    # A new loss may alter output length: the cautious main scenario uses the
    # untrained baseline's observed generation wall time, not a claimed forecast.
    components={
        'train/label_sum':train*1.35+50*1.10,
        'development/label_sum':long_eval*1.30,
        'diagnostic/base_judge':long_eval*12/500*1.30+120,
        'diagnostic/label_mean':short_eval*12/500*1.30+120,
        'diagnostic/label_sum':long_eval*12/500*1.30+120,
        'overhead':5*11+60+120,
    }
    after_gate=sum(components.values())
    pre_gate=3*60+4*60+11  # active platform preflight + compile/resource gate + load
    rerun=(long_eval+short_eval)*1.30+2*11
    central=after_gate-(long_eval-short_eval)*1.30
    result=dict(task=106,planning_only=True,GPU_authorized=False,quote_scenario_cny_per_hour=rate,
        measured_source='105 actual A800-SXM4 timings, original196 label data',
        train_tokens=tokens,train_examples=196,epochs=2,optimizer_steps=50,consumption=392,
        measured_train_tokens_per_second=speed,raw_train_compute_seconds=train,
        measured_label500_generation_seconds=short_eval,
        measured_base500_generation_seconds=long_eval,
        diagnostic_N=12,full_legal_paths_per_model=36,
        probability_diagnostic_seconds_allowance_per_model=120,
        probability_diagnostic_allowance_is_unmeasured=True,
        control_retraining_seconds=0,
        remaining_components_seconds=components,remaining_after_gate_seconds=after_gate,
        before_and_including_gate_seconds_allowance=pre_gate,
        baseline_rerun_extra_seconds=rerun,
        cross_hardware_rerun_scope='inference-aligned diagnostic only; control training hardware remains105 A800; strict new-hardware retraining requires another decision',
        scenarios={
            'cached_control_short_output':dict(seconds=pre_gate+central,
                compute_cny=(pre_gate+central)*rate/3600,reserve_cny=2,
                total_planning_cny=(pre_gate+central)*rate/3600+2),
            'cached_control_cautious_output':dict(seconds=pre_gate+after_gate,
                compute_cny=(pre_gate+after_gate)*rate/3600,reserve_cny=2,
                total_planning_cny=(pre_gate+after_gate)*rate/3600+2),
            'rerun_base_and_mean_cautious_output':dict(seconds=pre_gate+after_gate+rerun,
                compute_cny=(pre_gate+after_gate+rerun)*rate/3600,reserve_cny=2,
                total_planning_cny=(pre_gate+after_gate+rerun)*rate/3600+2),
        },
        pure_compute=dict(train_seconds=train,label500_seconds=short_eval,
            probability_diagnostic_allowance_seconds=360),
        allowances=dict(training_factor=1.35,generation_factor=1.30,
            each_model_load_seconds=11,checkpoint_save_seconds=55,
            platform_preflight_seconds=180,compile_resource_gate_seconds=240,
            manual_shutdown_and_unknown_cny=2),
        excludes=['new weights download','new package installation','disk rental invoice','CPU phase reports and bulk transfer after manual shutdown'],
        actual_price_and_elapsed_platform_billing_required_before_optimizer=True,
        no_budget_or_billing_carried_from105=True,
        fees_this_preparation=dict(API_cny=0,GPU_cny=0))
    c.put(c.OUT/'cost_estimate.json',result)
    print(c.canonical(dict(train_tokens=tokens,scenarios=result['scenarios'],GPU_authorized=False)))


if __name__=='__main__':main()
