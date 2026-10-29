"""Prepare original180 pilot and cached500 extension; no model operations."""
from pathlib import Path
import json,sys,tarfile,math
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/109_boundary_replay'));import common109 as c
LABELS=('Supported','Not Supported','Not Addressed')
def main():
 p=R/'.local_models/113_label_path';o=R/'outputs/113_label_path';p.mkdir(exist_ok=True);o.mkdir(parents=True,exist_ok=True)
 allkeys=c.rows(R/'.local_models/111_half_extension/cohort_keys.jsonl');old500={r['id'] for r in allkeys if r['subset']=='old500'}
 history=[r for r in c.rows(R/'outputs/103_lora_selection/final_paired_predictions.jsonl') if r['local180']];pilot={r['id']:r['panel'] for r in history}
 keys=[r for r in allkeys if r['id'] in old500 or r['id'] in pilot];key={r['id']:r for r in keys}
 assert len(old500)==500 and len(pilot)==180 and len(old500&set(pilot))==70 and len(key)==610
 raw={r['id']:r for path in [R/'.local_models/109_boundary_replay/gpu_bundle/data/eval_inputs.jsonl',R/'.local_models/111_half_extension/inputs_new.jsonl'] for r in c.rows(path)}
 base={r['id']:r for r in c.rows(R/'outputs/111_half_extension/predictions_sanitized.jsonl') if r['arm']=='label_only107' and r['id'] in key}
 assert set(key)<=set(raw) and set(base)==set(key) and all(r['valid'] for r in base.values())
 inputs=[dict(id=i,claim=raw[i]['claim'],reference=raw[i]['reference'],expected_prompt_sha256=base[i]['prompt_token_sha256']) for i in sorted(key)]
 assert all(not {'GT','sid','panel','verdict'}&set(r) for r in inputs)
 c.putl(p/'inputs.jsonl',inputs);c.putl(p/'keys.jsonl',[dict(r,pilot_panel=pilot.get(r['id'])) for r in keys]);c.putl(p/'baseline107.jsonl',list(base.values()))
 labels=c.read(R/'outputs/106_label_preparation/tokenizer_labels.json')['labels'];assert [len(labels[g]['verdict_ids']) for g in LABELS]==[1,2,3]
 cfg=dict(task=113,method='label_path',checkpoint='107_label_only',adapter_path='/root/autodl-tmp/verifact109/bundle/source107/checkpoint_a',adapter_sha256=c.SOURCE_ADAPTER_SHA,
  pilot_ids=sorted(pilot),confirm_ids=sorted(old500-set(pilot)),scoring='sum full canonical JSON plus EOS conditional log probabilities',label_order=list(LABELS),label_sequences={g:labels[g]['ids']+[labels[g]['eos_id']] for g in LABELS},first_value_index=4,branch_ids={'S':33490,'Not':2536},
  labels_unchanged=True,temperature=None,length_normalization=False,calibration=False,threshold_search=False,training=False,GT_in_GPU_inputs=False,
  start_beijing='2026-10-29 16:47:24',hourly_CNY=1.58,cap_CNY=1,API_CNY=0,no_shutdown=True,
  continuation=dict(false_S_increase_each_panel_max=0,S_correct_loss_natural_max=2,NS_NA_correct_loss_each_panel_max=1,correct_loss_each_panel_max=1,MCC_drop_other_panel_max=.01,
    quality_signal='one panel gains >=4 correct and >=0.02 MCC',risk_signal='total false-S reduces >=2, total correct does not drop, both MCC drops <=0.01'))
 c.put(R/'tasks/113_label_path/config.json',cfg);c.put(p/'config.json',cfg)
 # The selector sums token log probabilities; averaging would reverse this example.
 paths={'Supported':[-.2,-.2],'Not Supported':[-.15,-.15,-.15],'Not Addressed':[-1.,-1.,-1.]}
 assert max(LABELS,key=lambda g:sum(paths[g]))=='Supported'
 assert max(LABELS,key=lambda g:sum(paths[g])/len(paths[g]))=='Not Supported'
 c.put(o/'preparation.json',dict(pilot_N=180,pilot_panels={'natural':120,'pressure':60},pilot_overlap_old500=70,cached_greedy_N=610,conditional_new_N=430,total_unique_if_extended=610,unchanged_GT_reference_prompt=True,full_JSON_EOS_scoring=True,sum_not_mean_check=True,new_training=False,new_API=0,no_new_greedy_inference=True))
 with tarfile.open(p/'inputs113.tar.gz','w:gz',compresslevel=1) as t:
  for n in ['inputs.jsonl','config.json']:t.add(p/n,arcname=n,recursive=False)
 print(c.canonical(c.read(o/'preparation.json')))
if __name__=='__main__':main()
