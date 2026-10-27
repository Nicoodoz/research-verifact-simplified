"""Decide equal512/256 before any trained-model evaluation, using measured work."""
import argparse,statistics,time
from pathlib import Path
from gpu_worker103 import read,write,rows
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);a=p.parse_args();plan=read(a.bundle/'gpu_plan.json');lengths=rows(a.bundle/'token_lengths.jsonl');train=rows(a.bundle/'train512.jsonl');sample=[r for r in rows(a.bundle/'sample240.jsonl') if r['local180']];ledger=read(a.out/'gpu_ledger.json');elapsed=time.time()-ledger['billing_start_epoch']
 remaining=min(28800-ledger['prior_seconds']-elapsed,(60-ledger['prior_gpu_cny']-ledger['storage_fixed_cny'])/(ledger['gpu_hourly_cny']+ledger['storage_hourly_cny'])*3600-elapsed)
 alternatives=[]
 for count in [512,256]:
  total=900.;detail={}
  for m in plan['candidates']:
   steps=rows(a.out/m/'probe/steps.jsonl');assert len(steps)==4
   rate=sum(s['tokens'] for s in steps[1:])/sum(s['total_seconds'] for s in steps[1:])
   ns=rows(a.out/m/'eval/native_base_speed.jsonl');ls=rows(a.out/m/'eval/label_base_speed.jsonl');assert len(ns)>=3 and len(ls)>=3
   by={r['id']:r for r in lengths if r['model']==m};train_tokens=sum(by[r['id']]['label']+16 for r in train[:count])
   # Actual full-input latency per token includes prefill and decode; reserve25% for long tail.
   native_seconds=sum(by[r['id']]['native'] for r in sample)*sum(r['seconds'] for r in ns)/sum(r['input_tokens'] for r in ns)
   label_seconds=sum(by[r['id']]['label'] for r in sample)*sum(r['seconds'] for r in ls)/sum(r['input_tokens'] for r in ls)
   work=1.25*(train_tokens/rate+native_seconds+2*label_seconds)+300
   detail[m]=dict(training_tokens=train_tokens,observed_train_tokens_per_second=rate,training_seconds=train_tokens/rate,native_evaluation_seconds=native_seconds,two_label_evaluations_seconds=2*label_seconds,reserved_seconds=work);total+=work
  alternatives.append(dict(samples_each=count,total_reserved_seconds=total,by_model=detail))
  if total<remaining:break
 else:
  write(a.out/'scale_decision.json',dict(status='INSUFFICIENT_FOR_TWO_COMPLETE_CONTROLS',alternatives=alternatives,remaining_seconds=remaining,no_training_effects_inspected=True));raise SystemExit(2)
 write(a.out/'scale_decision.json',dict(status='GO',samples_each=count,alternatives=alternatives,remaining_seconds=remaining,no_training_effects_inspected=True))
 print('samples_each',count,'planned_hours',total/3600,'remaining_hours',remaining/3600)
if __name__=='__main__':main()
