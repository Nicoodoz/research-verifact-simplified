"""Offline risk intervals, source-independent sensitivities and cost projections."""
import numpy as np
from collections import Counter
import common103 as c
from analyze_final103 import metric,pair

def risk_interval(rows,base,new):
 subjects=sorted({r['sid'] for r in rows});groups={s:[r for r in rows if r['sid']==s] for s in subjects}
 def vector(rr,key):
  truth=[r['GT'] for r in rr];pred=[r['predictions'][key] for r in rr]
  denominators=[sum(g!='Supported' for g in truth),sum(g=='Not Supported' for g in truth),sum(g=='Not Addressed' for g in truth)]
  numerators=[sum(g!='Supported' and p=='Supported' for g,p in zip(truth,pred)),sum(g==p=='Not Supported' for g,p in zip(truth,pred)),sum(g==p=='Not Addressed' for g,p in zip(truth,pred))]
  return np.array([n/d if d else np.nan for n,d in zip(numerators,denominators)])
 draws=[]
 for seed in range(1000):
  pick=np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True);rr=[r for i in pick for r in groups[subjects[i]]];draws.append(vector(rr,new)-vector(rr,base))
 a=np.array(draws);point=vector(rows,new)-vector(rows,base)
 return {key:dict(delta=float(point[j]),ci95=np.nanpercentile(a[:,j],[2.5,97.5]).tolist(),valid_draws=int(np.isfinite(a[:,j]).sum())) for j,key in enumerate(['false_S_rate','NS_recall','NA_recall'])}

def main():
 rr=c.lines(c.OUT/'final_paired_predictions.jsonl');records=c.lines(c.OUT/'gpu_predictions_sanitized.jsonl');result={}
 for pan in ['natural','pressure']:
  sub=[r for r in rr if r['panel']==pan];result[pan]={new+'__vs__'+base:risk_interval(sub,base,new) for base,new in [('nine_direct','nine_lora'),('nine_native','nine_lora'),('moe_direct','moe_lora'),('moe_native_api','moe_lora'),('nine_lora','moe_lora')]}
 result['method']='Same sorted-patient RandomState seeds0..999 as unified evaluator; ratios computed on whole sampled clusters; undefined denominators omitted and valid count reported. Primary MCC/PA remain unified evaluate/paired_compare.'
 c.put(c.OUT/'final_risk_intervals.json',result)
 original=c.lines(c.PRIVATE/'gpu_final_evidence/results/scheduling/native9b_before_priority_pause.jsonl');assert len(original)==104
 original35=c.lines(c.PRIVATE/'base35_lora168.jsonl') if (c.PRIVATE/'base35_lora168.jsonl').exists() else None
 # The first168 in the finalized immutable stream preceded the failed long-input batch.
 moe=c.lines(c.PRIVATE/'gpu_final_evidence/results/qwen3.6-35b-a3b/eval/lora_label.jsonl');pre={r['id'] for r in moe[:168]};tail={r['id'] for r in moe[168:]};assert len(pre)==168 and len(tail)==12
 sensitivity={}
 for pan in ['natural','pressure']:
  subset=[r for r in rr if r['panel']==pan and r['id'] in pre];sensitivity[pan]=dict(N=len(subset),excluded_tail=sum(r['panel']==pan and r['id'] in tail for r in rr),metrics={key:metric(subset,key) for key in ['moe_direct','moe_lora']},paired=pair(subset,'moe_direct','moe_lora'))
 normalized={r['id'] for r in records if r['model']=='qwen3.6-35b-a3b' and r['arm']=='label_base' and r['parsed'].get('exact_label_normalized')}
 sub=[r for r in rr if r['id'] in normalized];sensitivity['normalized_baseline_labels']=dict(N=len(sub),GT=dict(Counter(r['GT'] for r in sub)),before_correct=sum(r['predictions']['moe_direct']==r['GT'] for r in sub),after_correct=sum(r['predictions']['moe_lora']==r['GT'] for r in sub),before_false_S=sum(r['GT']!='Supported' and r['predictions']['moe_direct']=='Supported' for r in sub),after_false_S=sum(r['GT']!='Supported' and r['predictions']['moe_lora']=='Supported' for r in sub),all_first_answers_preserved=True)
 c.put(c.OUT/'final_engineering_sensitivity.json',sensitivity)
 inv=c.read(c.OUT/'gpu_training_inference_inventory.json');lengths=c.read(c.OUT/'length_summary.json');usage=c.lines(c.OUT/'usage.jsonl');cost={}
 for m in ['qwen3.5-9b','qwen3.6-35b-a3b']:
  resource=inv[m];steps=c.lines(c.OUT/'gpu_resources'/m/'train/steps.jsonl');rate=resource['steady_training_tokens_per_second'];supervised=sum(v['supervised_tokens'] for v in steps)/512
  # 512/native length statistics are not substituted for the measured full3675 token sum.
  full_tokens=lengths[m]['all_training']['sum']+supervised*3675;compute=full_tokens/rate
  warm_excess=max(0,steps[0]['total_seconds']-steps[0]['tokens']/rate)
  overhead=c.read(c.OUT/'gpu_resources'/m/'train/load.json')['seconds']+c.read(c.OUT/'gpu_resources'/m/'train/adapter_setup.json')['seconds']+warm_excess+sum(e['seconds'] for e in resource['checkpoint_events'])
  arms={}
  for arm in ['native_base','label_base','lora_label']:
   data=[v for v in records if v['model']==m and v['arm']==arm]
   if not data:continue
   seconds=sum(v['seconds'] for v in data);generated=sum(v['output_tokens']+v['thinking_tokens'] for v in data)
   arms[arm]=dict(N=len(data),generation_seconds=seconds,mean_seconds=seconds/len(data),aggregate_generated_tokens_per_second=generated/seconds,peak_allocated_bytes=max(v['peak_allocated_bytes'] for v in data),projected3573_generation_hours=seconds/len(data)*3573/3600,projected3573_compute_cny=seconds/len(data)*3573/3600*6.98)
  cost[m]=dict(actual_512_training_wall_seconds=resource['training_done']['training_wall_seconds'],training_tokens_per_second=rate,full3675_estimated_tokens=full_tokens,full3675_compute_hours=compute/3600,full3675_compute_cny=compute/3600*6.98,full3675_with_observed_startup_and_25pct_margin_hours=(compute+overhead)*1.25/3600,full3675_with_observed_startup_and_25pct_margin_cny=(compute+overhead)*1.25/3600*6.98,full_training_max_input=lengths[m]['all_training']['max'],tested_small_training_max_input=lengths[m]['train512']['max'],inference=arms,confirmation_length_not_measured=True,projected_cost_excludes_new_download_storage_and_external_transfer=True)
 api=[v for v in usage if v['model']=='qwen3.6-35b-a3b' and v['mode']=='native' and v['repeat']==0];cost['moe_native_API_projection']=dict(mean_uncached_cny=sum(v['uncached_cny'] for v in api)/len(api),projected3573_uncached_cny=sum(v['uncached_cny'] for v in api)/len(api)*3573,historical_directory_prices_only=True,not_future_price_quote=True)
 p=c.OUT/'gpu_resources/qwen3.8-27b/train/steps.jsonl';steps=c.lines(p);steady=steps[1:];rate=sum(v['tokens'] for v in steady)/sum(v['total_seconds'] for v in steady)
 cost['unresolved_27b']=dict(completed_samples=40,optimizer_steps=5,short_run_steady_tokens_per_second=rate,remaining472_training_compute_minutes=(lengths['qwen3.8-27b']['train512']['sum']-sum(v['tokens'] for v in steps))/rate/60,minimal_followup_planning_hours=[1.2,1.5],gpu_planning_cny=[1.2*6.98,1.5*6.98],assumptions='Same persistent instance/weights/checkpoint40, complete512,180 local direct base and adapter predictions; reuse existing native API reference; excludes local native full180, downloads and storage; not an authorization or guarantee')
 c.put(c.OUT/'final_resource_cost_analysis.json',cost)
 c.put(c.OUT/'shutdown_confirmation.json',dict(confirmed_by_user=True,platform_exact_shutdown_time_available=False,last_remote_observed='2026-10-27 22:37:40 UTC+08:00',last_recorded_GPU_cny=30.53039536048439,storage_reserved_cny=4,last_recorded_GPU_plus_storage_reserve_cny=34.53039536048439,API_uncached_cny=27.5185756,API_actual_official_cache_cny=27.500758,platform_invoice_pending=True,post_shutdown_storage_retention_billed_separately=True,new_API_calls_in_analysis=0,new_GPU_calls_in_analysis=0))
 print('Offline risk/sensitivity/resource analyses saved')
if __name__=='__main__':main()
