"""Decide equal512/256 before any trained-model evaluation, using measured work."""
import argparse,statistics,time
from pathlib import Path
from gpu_worker103 import read,write,rows
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);a=p.parse_args();plan=read(a.bundle/'gpu_plan.json');lengths=rows(a.bundle/'token_lengths.jsonl');train=rows(a.bundle/'train512.jsonl');sample=[r for r in rows(a.bundle/'sample240.jsonl') if r['local180']];ledger=read(a.out/'gpu_ledger.json');elapsed=time.time()-ledger['billing_start_epoch']
 remaining=min(28800-ledger['prior_seconds']-elapsed,(60-ledger['prior_gpu_cny']-ledger['storage_fixed_cny'])/(ledger['gpu_hourly_cny']+ledger['storage_hourly_cny'])*3600-elapsed)
 alternatives=[]
 for count in [512,256]:
  total=0.;detail={}
  for m in plan['candidates']:
   steps=rows(a.out/m/'probe/steps.jsonl');assert len(steps)==4
   rate=sum(s['tokens'] for s in steps[1:])/sum(s['total_seconds'] for s in steps[1:])
   ns=rows(a.out/m/'eval/native_base_speed.jsonl');ls=rows(a.out/m/'eval/label_base_speed.jsonl');assert len(ns)>=3 and len(ls)>=3
   timing_sources={}
   for arm in ['native_base','label_base']:
    path=a.out/m/'eval'/(arm+'.jsonl')
    actual=rows(path) if path.exists() else []
    if len(actual)>=16:
     if arm=='native_base':ns=actual
     else:ls=actual
     timing_sources[arm]='completed formal same-runtime batches'
    else:timing_sources[arm]='frozen speed panel (conservative including compilation)'
   by={r['id']:r for r in lengths if r['model']==m};train_tokens=sum(by[r['id']]['label']+16 for r in train[:count])
   # Actual full-input latency per token includes prefill and decode; reserve25% for long tail.
   completed={arm:{v['id'] for v in rows(a.out/m/'eval'/(arm+'.jsonl'))} if (a.out/m/'eval'/(arm+'.jsonl')).exists() else set() for arm in ['native_base','label_base','lora_label']}
   assert not completed['lora_label'],'Scale must be fixed before trained-model evaluation'
   assert all(ids <= {r['id'] for r in sample} for ids in completed.values())
   native_seconds=sum(by[r['id']]['native'] for r in sample if r['id'] not in completed['native_base'])*sum(r['seconds'] for r in ns)/sum(r['input_tokens'] for r in ns)
   label_seconds=sum(sum(by[r['id']]['label'] for r in sample if r['id'] not in completed[arm]) for arm in ['label_base','lora_label'])*sum(r['seconds'] for r in ls)/sum(r['input_tokens'] for r in ls)
   work=1.25*(train_tokens/rate+native_seconds+label_seconds)+300
   detail[m]=dict(training_tokens=train_tokens,observed_train_tokens_per_second=rate,training_seconds=train_tokens/rate,native_evaluation_seconds=native_seconds,two_label_evaluations_seconds=label_seconds,already_completed_counts={k:len(v) for k,v in completed.items()},timing_sources=timing_sources,reserved_seconds=work);total+=work
  backup=read(a.out/'backup_bandwidth.json')
  parameters=sum(read(a.out/m/'probe/trainable_parameters.json')['total'] for m in plan['candidates'])
  backup_bytes=parameters*16*(2 if count==512 else 1)
  backup_seconds=1.25*backup_bytes/backup['bytes_per_second']+180
  overlap_seconds=sum(v['native_evaluation_seconds'] for v in detail.values())
  backup_extra=max(0,backup_seconds-overlap_seconds)+600
  total+=backup_extra
  alternatives.append(dict(samples_each=count,total_reserved_seconds=total,by_model=detail,backup=dict(measured_bytes_per_second=backup['bytes_per_second'],conservative_checkpoint_bytes=backup_bytes,transfer_and_pack_reserved_seconds=backup_seconds,overlap_with_required_native_evaluation_seconds=overlap_seconds,nonoverlapped_plus_final_sync_reserved_seconds=backup_extra)))
  if total<remaining:break
 else:
  write(a.out/'scale_decision.json',dict(status='INSUFFICIENT_FOR_TWO_COMPLETE_CONTROLS',alternatives=alternatives,remaining_seconds=remaining,no_training_effects_inspected=True));raise SystemExit(2)
 write(a.out/'scale_decision.json',dict(status='GO',samples_each=count,alternatives=alternatives,remaining_seconds=remaining,no_training_effects_inspected=True))
 print('samples_each',count,'planned_hours',total/3600,'remaining_hours',remaining/3600)
if __name__=='__main__':main()
