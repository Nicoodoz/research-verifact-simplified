"""Historical planning references; current-card absolute measurements gate107."""
import common107 as c


def measured_remaining(train_tokens,training_probes,checkpoint_seconds,optimizer_seconds,prefill_probes,decode_probes,batches,config):
    """Absolute current-card estimate; no A800 or batch8 throughput ratio.

    Every actual frozen batch is assigned the next measured upper input-length
    bin. Prefill includes four decode tokens; the larger measured incremental
    decode slope projects the remaining380, so both arms may use all384 tokens.
    """
    import math
    bs=config['evaluation']['batch_size'];allow=estimate_allowances()
    if bs not in (1,2,8) or not batches or sum(len(b['ids']) for b in batches)!=500 or any(not 1<=len(b['ids'])<=bs for b in batches):raise ValueError('Frozen evaluation batches do not cover500 at the configured batch size')
    speed=min(float(p['tokens'])/float(p['seconds']) for p in training_probes)
    if not math.isfinite(speed) or speed<=0:raise ValueError('Finite measured training speed required')
    bins=sorted(prefill_probes,key=lambda p:p['input_tokens'])
    if not bins or any(p['output_tokens_each']!=4 or p['seconds']<=0 for p in bins):raise ValueError('Measured four-token prefills required')
    d={p['output_tokens_each']:p for p in decode_probes};t4=bins[-1]['seconds']
    if not {128,384}<=set(d):raise ValueError('Current-card128/384 decode probes required')
    slope=max((d[128]['seconds']-t4)/124,(d[384]['seconds']-d[128]['seconds'])/256,1e-6)
    per_batch=[]
    for batch in batches:
        upper=next((p['input_tokens'] for p in bins if p['input_tokens']>=batch['max_input_tokens']),None)
        if upper is None:raise ValueError('A frozen batch exceeds measured input context')
        prefill=max(p['seconds'] for p in bins if p['input_tokens']<=upper)
        per_batch.append(dict(batch=batch['batch'],N=len(batch['ids']),max_input_tokens=batch['max_input_tokens'],
            measured_upper_input_bin=upper,prefill_with_four_tokens_seconds=prefill,
            estimate384_seconds=prefill+380*slope))
    training=train_tokens/speed*allow['training_factor']+allow['checkpoint_count_each']*checkpoint_seconds+max(
        allow['minimum_optimizer_overhead_each_seconds'],allow['optimizer_steps_each']*optimizer_seconds*1.25)
    evaluation=sum(p['estimate384_seconds'] for p in per_batch)*allow['evaluation_factor']
    return dict(train_each=training,eval_each=evaluation,remaining_overhead=allow['remaining_overhead_seconds'],
        conservative_train_tokens_per_second=speed,checkpoint_seconds_each=checkpoint_seconds,
        optimizer_step_seconds=optimizer_seconds,decode_seconds_per_token_upper_slope=slope,
        frozen_eval_batch_size=bs,frozen_eval_batch_count=len(batches),all500_may_generate384=True,
        evaluation_margin_factor=allow['evaluation_factor'],per_batch_estimates=per_batch,
        formula='sum(measured_upper_prefill_bin4 + 380*max_incremental_decode_slope) * 1.20; training tokens / slowest measured speed *1.35 + actual saves/optimizer')


def estimate_allowances():
    return dict(training_factor=1.35,evaluation_factor=1.20,checkpoint_count_each=51,
        optimizer_steps_each=50,minimum_optimizer_overhead_each_seconds=30,remaining_overhead_seconds=300,
        evaluation_output_tokens_each=384,minimum_peak_headroom_bytes=268435456)


def estimate():
    config=c.read(c.TASK/'config.json')
    old=c.ROOT/'outputs/105_brief_supervision';resources=c.read(old/'a800_resources.json')
    lengths=[r for r in c.rows(old/'train_token_lengths.jsonl') if r['arm']=='label_only']
    if len(lengths)!=196:raise ValueError('Missing frozen196 token lengths')
    tokens=2*sum(r['total_tokens'] for r in lengths);speed=resources['training']['label_only']['steady_tokens_per_second']
    train=tokens/speed;short=resources['evaluation']['label_only']['generation_seconds'];long=resources['evaluation']['base_judge']['generation_seconds']
    # Fresh auxiliary training can change output length; budget BOTH evaluations
    # against the much slower observed untrained baseline, without claiming it
    # bounds all possible new outputs. The real gate additionally scales speed.
    per_train=train*1.35+60
    per_eval=long*1.30
    benchmark=c.read(old/'a800_benchmark.json')
    decode128=next(r for r in benchmark['decode'] if r['forced_tokens_per_sequence']==128)
    overhead=300
    gate=600
    scenarios={}
    rate=2.88
    for name,ev in [('historical_A800_work_at_current_quote_short',short*1.30),('historical_A800_work_at_current_quote_cautious',per_eval)]:
        seconds=gate+2*per_train+2*ev+overhead
        scenarios[name]=dict(seconds=seconds,minutes=seconds/60,compute_cny=seconds*rate/3600,total_with_2cny_reserve=seconds*rate/3600+2,
            not_a_5090_throughput_forecast=True)
    return dict(task=107,planning_only=True,this_script_GPU_started=False,actual_GPU_measurements_available=False,
        fees_this_script=dict(API_cny=0,GPU_cny=0),actual_session_cost_requires_cumulative_billing_ledger=True,
        quote_scenario_cny_per_hour=rate,quote_source='user current RTX5090 rental handoff',quote_is_historical105_not_current_offer=False,
        target_gpu='RTX5090_32GB',evaluation_batch_size=config['evaluation']['batch_size'],
        runtime_estimate_mode='actual_gpu_absolute',
        source='105 A800-SXM4-80GB actual training/evaluation resource receipts',
        train_rows=196,epochs=2,optimizer_steps_each=50,row_consumptions_each=392,train_tokens_each=tokens,
        measured_training_tokens_per_second105=speed,measured_train_compute_seconds105=train,
        measured_label500_seconds105=short,measured_base500_seconds105=long,
        matched_inference_benchmark105=dict(batch_size=8,forced_tokens_per_sequence=128,seconds=decode128['seconds'],
            input_tokens=max(r['input_tokens'] for r in c.rows(old/'eval_token_lengths.jsonl')),
            source='105 a800_benchmark decode128 after decode4 kernel warmup'),
        per_arm_train_remaining_seconds=per_train,per_arm_eval_cautious_seconds=per_eval,
        remaining_overhead_seconds=overhead,resource_gate_seconds_allowance=gate,
        allowances=dict(training_factor=1.35,eval_factor=1.30,checkpoint_each_arm_seconds=60,
            gate_seconds=gate,loading_saving_transfer_shutdown_seconds=overhead,shutdown_unknown_reserve_cny=2),
        absolute_runtime_allowances=estimate_allowances(),
        scenarios=scenarios,hard_cap_cny=20,operating_line_cny=18,API_cap_cny=0,
        new_original_base_trainings=2,new_evaluations_each500=2,
        runtime_price_elapsed_and_measured_throughput_required_before_formal_optimizer=True,
        excludes=['new full model download','new package installation','disk charges requiring new authorization'],
        uncertainty=['auxiliary compute overhead unmeasured until real GPU gate','new adapters can produce longer/invalid outputs',
            'kernel compilation, restoration, network backup, platform shutdown delay','5090 throughput must be measured; A800 batch8 timing is not transferable'])


def main():
    result=estimate();c.put(c.OUT/'cost_estimate.json',result)
    print(c.canonical(dict(scenarios=result['scenarios'],this_script_GPU_started=False,API_cny=0)))


if __name__=='__main__':main()
