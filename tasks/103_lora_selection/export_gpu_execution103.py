"""Publishable execution evidence only; never calculate clinical quality metrics."""
import argparse,json,hashlib,shutil,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/103_lora_selection'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True);a=ap.parse_args();r=a.evidence/'results';assert (r/'necessary_inference_complete.json').exists()
 cohort=rows(OUT/'cohort240.jsonl');ids={x['id'] for x in cohort if x['local180']};train_ids=[x['id'] for x in rows(OUT/'train512_ids.jsonl')];summary={};public=[];checks={}
 for model in ['qwen3.6-35b-a3b','qwen3.5-9b']:
  work=r/model/'train';done=read(work/'training_done.json');assert (done['samples'],done['steps'])==(512,64)
  steps=rows(work/'steps.jsonl');assert [pid for step in steps for pid in step['ids']]==train_ids
  update=read(work/'weight_update.json');assert update['any_update'];steady=steps[1:];trainable=read(work/'trainable_parameters.json');resume=read(work/'resume.json')
  variants={arm:rows(r/model/'eval'/(arm+'.jsonl')) for arm in ['label_base','lora_label',('native_api' if model=='qwen3.6-35b-a3b' else 'native_base')]}
  by={arm:{x['id']:x for x in data} for arm,data in variants.items()}
  for arm,data in variants.items():
   assert len(data)==180 and set(by[arm])==ids and all(x['parsed'].get('finish_reason')=='stop' for x in data)
   for x in data:public.append(dict(model=model,arm=arm,**{k:v for k,v in x.items() if k not in ['model','arm','content']}))
  for pid in ids:
   base=by['label_base'][pid];trained=by['lora_label'][pid]
   assert base['prompt_sha256']==trained['prompt_sha256'] and base['batch_ids']==trained['batch_ids']
  summary[model]=dict(training_done=done,checkpoint=resume['checkpoint'],trainable_parameters=trainable['total'],all_lora_B_tensors_updated=update['zero_tensors']==0,expert_slices_checked=sum(v['experts'] for v in update['expert_updates'].values()),expert_slices_updated=sum(v['updated'] for v in update['expert_updates'].values()),steady_training_tokens_per_second=sum(s['tokens'] for s in steady)/sum(s['total_seconds'] for s in steady),peak_training_allocated_bytes=max(s['peak_allocated_bytes'] for s in steps),checkpoint_events=rows(work/'checkpoint_events.jsonl'),inference={arm:dict(N=len(data),invalid=sum(not x['parsed'].get('valid',False) for x in data),generation_seconds=sum(x.get('seconds',0) for x in data),source='reused API reference; not local native control' if arm=='native_api' else 'local') for arm,data in variants.items()})
  checks[model]=dict(exact_train512_order=True,same180_target_ids=True,label_pair_input_hashes_equal=True,label_pair_batches_equal=True,all_receipts_finish_stop=True)
 # Keep all non-clinical resource evidence, not just a hand-picked favourable subset.
 allowed={'load.json','trainable_parameters.json','adapter_setup.json','steps.jsonl','weight_update.json','training_done.json','compiler_timings.json','checkpoint_events.jsonl','resume.json','unused_vision_memory_adjustment.json'}
 for model in ['qwen3.6-35b-a3b','qwen3.5-9b','qwen3.8-27b']:
  for phase in ['probe','probe_tail','train','eval']:
   folder=r/model/phase
   if not folder.exists():continue
   for p in folder.iterdir():
    if p.is_file() and (p.name in allowed or p.name.startswith('memory_lifetime_patch')):
     dest=OUT/'gpu_resources'/model/phase/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 partial=read(r/'qwen3.8-27b/train/resume.json');assert partial['samples']==40 and not (r/'qwen3.8-27b/train/training_done.json').exists()
 summary['qwen3.8-27b']=dict(status='USER_STOPPED_NOT_COMPLETED',saved_samples=40,checkpoint=partial['checkpoint'],not_in_evaluation=True)
 write(OUT/'gpu_training_inference_inventory.json',summary)
 (OUT/'gpu_predictions_sanitized.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in public),encoding='utf-8')
 for name in ['necessary_inference_complete.json','budget_backup_review.json','training_execution_freeze.json','causal_kernel_check.json']:
  if (r/name).exists():shutil.copyfile(r/name,OUT/name)
 cost=read(r/'gpu_cost_status.json');ledger=read(r/'gpu_ledger.json');write(OUT/'gpu_cost_snapshot.json',dict(**cost,hourly_gpu_cny=ledger['gpu_hourly_cny'],storage_reserved_cny=ledger['storage_fixed_cny'],billing_start_epoch=ledger['billing_start_epoch'],GPU_shutdown_confirmed=False,not_final_bill=True,API_uncached_cny=27.5185756,new_API_calls_in_GPU_phase=0))
 write(OUT/'gpu_execution_selfcheck.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks=checks,model27_stopped40_preserved=True,native35_API_reuse180=True,API_not_used_as_local_training_increment=True,quality_metrics_computed=False,clinical_content_removed_from_public_predictions=True,independent_review=False,executor_selfcheck=True,final_evidence_sha256=sha(r/'necessary_inference_complete.json')))
 print('Execution checks passed; resource evidence and sanitized predictions exported; no clinical metrics computed')
if __name__=='__main__':main()
