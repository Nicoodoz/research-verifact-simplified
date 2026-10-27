"""Offline only after GPU stopped and private artifacts returned; no model/API calls."""
import argparse,sys,statistics
from pathlib import Path
import common103 as c
sys.path.insert(0,str(c.ROOT/'tasks/099_judge_selection'))
from analyze099 import panel,pair
def main():
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);a=p.parse_args();plan=c.read(c.OUT/'gpu_plan.json');sample={r['id']:r for r in c.lines(c.OUT/'cohort240.jsonl') if r['local180']};lengths=c.read(c.OUT/'length_summary.json');report={}
 for m in plan['candidates']:
  preds={arm:{r['id']:r for r in c.lines(a.results/m/'eval'/(arm+'.jsonl'))} for arm in ['native_base','label_base','lora_label']}
  assert all(set(v)==set(sample) for v in preds.values()),'Missing required same-ID control'
  rr=[dict(r,predictions={'Original':r['paper_r1']}|{arm:preds[arm][pid]['parsed']['verdict'] for arm in preds},arms={arm:preds[arm][pid]['parsed'] for arm in preds}) for pid,r in sample.items()]
  tables={name:panel([r for r in rr if r['panel']==name],list(preds)) for name in ['natural','pressure']}
  steps=c.lines(a.results/m/'train/steps.jsonl');steady=steps[1:];rate=sum(s['tokens'] for s in steady)/sum(s['total_seconds'] for s in steady)
  inference={arm:dict(mean_seconds=statistics.mean(r['seconds'] for r in v.values()),generated_tokens_per_second=sum(r['output_tokens']+r['thinking_tokens'] for r in v.values())/sum(r['seconds'] for r in v.values()),peak_memory_bytes=max(r['peak_allocated_bytes'] for r in v.values())) for arm,v in preds.items()}
  report[m]=dict(results=tables,training_tokens_per_second=rate,first_step_compile_included_seconds=steps[0]['total_seconds'],peak_training_bytes=max(s['peak_allocated_bytes'] for s in steps),inference=inference,full3675_training_seconds_estimate=(lengths[m]['all_training']['sum']+16*3675)/rate,confirmation3573_seconds_by_arm={arm:info['mean_seconds']*3573 for arm,info in inference.items()},confirmation3573_all_three_arms_seconds=sum(info['mean_seconds']*3573 for info in inference.values()),confirmation_cost_is_projection_not_evaluation=True,confirmation_length_distribution_not_measured_this_phase=True)
  c.putl(c.OUT/(m+'_local_predictions.jsonl'),rr)
 c.put(c.OUT/'gpu_analysis.json',report)
 print('Offline GPU analysis saved; compare lora_label against both baselines before recommending full training')
if __name__=='__main__':main()
