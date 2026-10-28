"""Local projection from 103 actual timings, not a new hardware price quote."""
import numpy as np
from scipy.optimize import nnls
import common105 as c

def main():
    historical=c.read(c.ROOT/'outputs/103_lora_selection/final_resource_cost_analysis.json')['qwen3.5-9b']
    token=c.read(c.OUT/'token_summary.json');training=token['training']
    total_train_tokens=2*sum(training[arm]['total_tokens']['sum'] for arm in c.ARMS[1:])
    raw_train_seconds=total_train_tokens/historical['training_tokens_per_second']
    # Both direct 103 arms: use timing/token fields only; never prediction or GT.
    root=c.ROOT/'.local_models/103_lora_selection/gpu_final_evidence/results/qwen3.5-9b/eval'
    measured=[]
    for name in ('label_base','lora_label'):
        rows=c.rows(root/(name+'.jsonl'));groups={}
        for row in rows:groups.setdefault(tuple(row['batch_ids']),[]).append(row)
        for ids,rows in groups.items():
            assert len(rows)==len(ids)
            measured.append(dict(arm=name,N=len(rows),seconds=rows[0]['batch_seconds'],
                                 padded_input=max(r['input_tokens'] for r in rows)*len(rows),
                                 max_output=max(r['output_tokens'] for r in rows)))
    features=np.array([[1.,r['padded_input']/8000,r['max_output']*r['N']/8] for r in measured])
    target=np.array([r['seconds'] for r in measured]);coef,_=nnls(features,target)
    fit_error=float(np.sqrt(np.mean((features@coef-target)**2)))
    batches=c.read(c.OUT/'eval_batches.json')['batches']
    # Use the observed 104 answer-token distribution, not max_new_tokens=384.
    brief_target_mean=training['evidence_brief']['answer_tokens']['mean']
    brief_target_p95=training['evidence_brief']['answer_tokens']['p95']
    means={key:historical['inference'][key]['mean_seconds'] for key in ('label_base','lora_label')}
    slowest_rate=min(historical['inference'][key]['aggregate_generated_tokens_per_second'] for key in means)
    empirical_brief_seconds=sum(float(np.dot([1.,b['max_input_tokens']*len(b['ids'])/8000,brief_target_p95*len(b['ids'])/8],coef)) for b in batches)
    conservative_brief_seconds=500*brief_target_mean/slowest_rate
    # Short-answer throughput includes prefill, so this output-token scaling is
    # intentionally conservative; a longer explanation may amortize prefill.
    generation=500*means['label_base']+500*means['lora_label']+max(empirical_brief_seconds,conservative_brief_seconds)
    train_allowance=raw_train_seconds*1.35
    startup_save_sync_allowance=600.
    planned_gpu_hours=(train_allowance+generation+startup_save_sync_allowance)*1.15/3600
    historical_hourly=6.98
    result=dict(historical_GPU='RTX PRO 6000 Blackwell Server Edition',historical_hourly_cny=historical_hourly,
        current_price_not_queried=True,actual_next_instance_quote_required=True,
        train_tokens_two_arms_two_epochs=total_train_tokens,historical_training_tokens_per_second=historical['training_tokens_per_second'],
        training_raw_seconds=raw_train_seconds,training_with_35pct_path_margin_seconds=train_allowance,
        label_base_500_seconds=500*means['label_base'],label_only_500_seconds=500*means['lora_label'],
        evidence_brief_planned_average_output_tokens=brief_target_mean,evidence_brief_p95_training_answer_tokens=brief_target_p95,
        historical_slowest_direct_generated_tokens_per_second=slowest_rate,
        empirical_batch_fit=dict(coefficients=coef.tolist(),features=['intercept','padded_input_tokens/8000','max_output_tokens*N/8'],RMSE_seconds=fit_error,N=len(measured),
                                 projected_brief_seconds=empirical_brief_seconds,extrapolation_not_GPU_measurement=True,
                                 decode_slope_not_identifiable_from_short_outputs=bool(coef[-1]==0),not_used_to_claim_near_zero_decode_cost=True),
        conservative_brief_seconds=conservative_brief_seconds,
        model_load_compile_checkpoint_backup_allowance_seconds=startup_save_sync_allowance,
        final_margin=1.15,planned_GPU_hours=planned_gpu_hours,
        planned_GPU_cny_at_historical_price=planned_gpu_hours*historical_hourly,
        nogpu_planning_allowance_cny=1.,
        planned_total_with_nogpu_1cny=planned_gpu_hours*historical_hourly+1.,
        max_hourly_quote_if_nogpu_cost_1cny_and_operating_line_18=(18-1)/planned_gpu_hours,
        operating_line_cny=18,shutdown_reserve_cny=2,hard_total_compute_cap_cny=20,API_cap_cny=0,
        new_disk_cny=0,existing_weights_and_environment_required=True,
        no_use_of_384_as_average_runtime=True,hardware_transfer_speed_not_assumed_equal=True,
        future_slowdown_action='Stop and preserve fixed500/196 when full plan no longer fits; never reduce N after predictions or silently truncate input')
    c.put(c.OUT/'cost_estimate.json',result)
    print(c.canonical({k:result[k] for k in ('planned_GPU_hours','planned_GPU_cny_at_historical_price','planned_total_with_nogpu_1cny','max_hourly_quote_if_nogpu_cost_1cny_and_operating_line_18')}))

if __name__=='__main__':main()

