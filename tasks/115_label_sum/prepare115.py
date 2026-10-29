"""Reuse the exact196 and existing code; prepare one normalized label-sum fit."""
from pathlib import Path
from collections import Counter
import sys,shutil,tarfile,ast
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
P=R/'.local_models/115_label_sum';O=R/'outputs/115_label_sum'
def main():
 P.mkdir(exist_ok=True);O.mkdir(parents=True,exist_ok=True);B=P/'bundle';D=B/'data';D.mkdir(parents=True,exist_ok=True)
 source=R/'.local_models/107_support_aux/gpu_bundle_5090_run';old=source/'data/train/label_only.jsonl';rows=c.rows(old);assert len(rows)==196 and len({r['id'] for r in rows})==196
 assert c.sha(old)=='6abf6abb7949e5eca1e316f117c5269ccc87984452822920847cddb37e4008dc'
 assert Counter(r['GT'] for r in rows)=={'Supported':83,'Not Supported':62,'Not Addressed':51}
 role=c.read(R/'outputs/103_lora_selection/patient_roles.json')['patients'];sids={str(r['sid']) for r in rows};assert sids<=set(map(str,role['train'])) and not sids&set(map(str,role['selection']+role['confirmation']))
 lengths=c.rows(R/'.local_models/114_matched_refresh/train_lengths.jsonl')[:196];assert [x['id'] for x in lengths]==[r['id'] for r in rows]
 ll={g:n for g,n in zip(c.LABELS,[1,2,3])};assert sum(ll[r['GT']] for r in rows)==360
 c.putl(D/'train.jsonl',rows+rows);shutil.copy2(old,D/'train196_original.jsonl');c.putl(D/'train_lengths.jsonl',[dict(x,index=k*196+i) for k in range(2) for i,x in enumerate(lengths)])
 plan=c.read(R/'.local_models/114_matched_refresh/plan.json');assert len(plan)==50 and [x['divisor'] for x in plan if x['divisor']!=8]==[4,4];c.put(D/'plan.json',plan)
 for name in ['eval_inputs.jsonl','eval_token_lengths.jsonl','eval_batches.json']:shutil.copy2(R/'.local_models/114_matched_refresh/bundle/data'/name,D/name)
 ev=c.rows(D/'eval_inputs.jsonl');assert len(ev)==500 and all(set(r)=={'id','claim','reference'} for r in ev)
 cfg=c.read(R/'tasks/107_support_aux/config.json');cfg.update(task=115,method='label_sum',model_dir='/root/verifact_image/models/qwen3.5-9b',context_tokens=13097,trainable_arms=['label_sum'],training_N=196,training_presentations=392,unique_training_N=196,estimated_train_seconds=2100,estimated_eval_seconds=1100,return_reserve_seconds=720)
 cfg['training'].pop('auxiliary');cfg['training']['loss']='verdict_value_sum_CE_div_global_mean_length_plus_other_answer_mean_CE';cfg['training']['value_sum_divisor']=360/196
 cfg['evaluation'].update(arms=['label_sum'],old_predictions_reused=True,baseline='107_label_only_original500')
 cfg['budget']=dict(compute_hard_cap_cny=3,API_cap_cny=0,billing_start_beijing='2026-10-29T18:27:44+08:00',hourly_cny=1.58,no_shutdown=True)
 cfg.pop('execution_amendment');cfg['design']=dict(sole_change='per_example_label_mean_to_globally_normalized_label_sum',fresh_original_base=True,initialization_seed=103027,training_data_changed=False,loss_normalizer_fixed=360/196,other_answer_loss_unchanged=True,confirmation40_used=False,epoch_selection='fixed_final_step50',baseline='reuse107_label_only',same_hardware_training_control=False,no_automatic_1317_or116=True)
 cfg['effect_rule']=dict(valid_coverage_min=.95,natural_PA_drop_max=.02,natural_S_recall_drop_max=.02,NS_NA_recall_drop_each_panel_max=.05,pressure_MCC_drop_max=.02,pressure_false_S_increase_max=2,quality_natural_MCC_gain_min=.02,quality_natural_false_S_increase_max=1,risk_natural_false_S_reduction_min=4,risk_natural_MCC_drop_max=.01,each_present_class_recall_positive=True)
 c.put(R/'tasks/115_label_sum/config.json',cfg);c.put(D/'config.json',cfg)
 # Readable execution snapshot: inherited loop, single explicit objective import.
 code=(R/'tasks/114_matched_refresh/worker114.py').read_text(encoding='utf-8')
 code=code.replace('One fresh 9B matched-refresh fit; inherited 105 loss and 107 checkpointing.','One fresh 9B label-sum fit; inherited106 objective and107 checkpointing.')
 code=code.replace("sys.path.insert(0,str(R/'tasks/107_support_aux'))","sys.path.insert(0,str(R/'tasks/107_support_aux'))\nsys.path.insert(0,str(R/'tasks/106_label_preparation'))")
 code=code.replace('from loss105 import backbone_loss',"from loss106 import backbone_sum_loss as backbone_loss\n assert cfg['training']['value_sum_divisor']==360/196")
 code=code.replace('114 compute stop','115 compute stop').replace("arm='matched_refresh'","arm='label_sum'")
 code=code.replace('auxiliary_head=False,gpu=',"auxiliary_head=False,value_sum_divisor=360/196,objective='label_sum',gpu=")
 ast.parse(code);(R/'tasks/115_label_sum/worker115.py').write_bytes(code.encode())
 files=['tasks/115_label_sum/worker115.py','tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/data105.py','tasks/105_brief_supervision/loss105.py','tasks/105_brief_supervision/parse105.py','tasks/106_label_preparation/loss106.py','tasks/107_support_aux/checkpoint107.py']
 for name in files:
  ast.parse((R/name).read_text(encoding='utf-8-sig'));target=B/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,target)
 c.put(B/'manifest.json',{p.relative_to(B).as_posix():c.sha(p) for p in B.rglob('*') if p.is_file() and p.name!='manifest.json'})
 with tarfile.open(P/'bundle115.tar.gz','w:gz',compresslevel=1) as tar:
  for p in B.rglob('*'):
   if p.is_file():tar.add(p,arcname=p.relative_to(B),recursive=False)
 c.put(O/'preparation.json',dict(task=115,original_training_file_SHA256=c.sha(old),original196_unchanged=True,GT=dict(Counter(r['GT'] for r in rows)),train_patients=len(sids),presentations=392,steps=50,short_tail_divisors=[4,4],label_token_lengths=ll,label_token_sum=360,global_fixed_normalizer=360/196,average_label_segment_weight_preserved=sum(ll[r['GT']]/(360/196) for r in rows)/196,relative_to_mean_label_scales={g:n/(360/196) for g,n in ll.items()},evaluation_N=500,evaluation_GT_removed=True,baseline107_reused=True,fresh_base=True,not_continuation107_or109_or114=True,full_original_input_tokens=3270664,no_105_execution=True,no_new_clinical_reviews_needed=True,old106_full_protocol_not_claimed=True,bundle_bytes=(P/'bundle115.tar.gz').stat().st_size))
 print(c.canonical(c.read(O/'preparation.json')))
if __name__=='__main__':main()
