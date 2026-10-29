"""Reuse114's exact second196 for one fixed, low-rate107 continuation."""
from pathlib import Path
from collections import Counter
import sys,shutil,tarfile
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'))
import common105 as c
from data105 import training_plan
P=R/'.local_models/116_research_cycle';O=R/'outputs/116_research_cycle'

def main():
 rows=c.rows(P/'gentle_refresh_train196.jsonl');summary=c.read(P/'gentle_refresh_summary.json')
 assert len(rows)==196 and Counter(r['GT'] for r in rows)=={'Supported':83,'Not Supported':62,'Not Addressed':51}
 roles=c.read(R/'outputs/103_lora_selection/patient_roles.json')['patients'];assert {str(r['sid']) for r in rows}<=set(map(str,roles['train']))
 assert not {str(r['sid']) for r in rows}&set(map(str,roles['selection']+roles['confirmation']))
 old_lengths=c.rows(R/'.local_models/114_matched_refresh/bundle/data/train_lengths.jsonl')[196:392];assert len(old_lengths)==196
 meta=[]
 for r,e in zip(rows,old_lengths):
  assert r['id']==e['id'];meta.append(dict(id=r['id'],prompt_token_sha256=e['prompt_token_sha256'],answer_sha256=e['answer_sha256'],input_tokens=e['total_tokens']))
 cfg=c.read(R/'tasks/107_support_aux/config.json');tr=cfg['training'];tr.pop('auxiliary',None);tr.update(epochs=1,total_steps=25,learning_rate=2e-5,scheduler='constant new stage, source Adam moments retained',loss='unchanged loss105.backbone_loss')
 cfg.update(task=116,candidate='gentle_refresh',model_dir='/root/verifact_image/models/qwen3.5-9b',max_seq_length=13783,source_root='/root/autodl-tmp/verifact109/bundle/source107',source_adapter_sha256='096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8')
 cfg.update(training_N=196,trainable_arms=['gentle_refresh'],evaluation=dict(mode='original107_greedy_JSON',full_reference=True,GT_in_inputs=False,first_screen_N=180,parser='parse105'))
 cfg.pop('budget',None);cfg.pop('execution_amendment',None);cfg['budget_source']='One116 cycle session; no new budget or elapsed-time origin'
 cfg['design']=dict(start='107 final adapter and Adam moments',selection='fixed final25, never by development score',data='Exact114 second196, same order, no resampling',new_head=False,JSON_interface_unchanged=True,GT_unchanged=True)
 assert max(m['input_tokens'] for m in meta)<=cfg['max_seq_length']
 B=P/'gentle_bundle';(B/'data/gentle').mkdir(parents=True,exist_ok=True)
 shutil.copy2(P/'gentle_refresh_train196.jsonl',B/'data/gentle/train.jsonl');c.putl(B/'data/gentle/lengths.jsonl',meta);c.put(B/'data/gentle/config.json',cfg)
 c.put(R/'tasks/116_research_cycle/gentle_refresh_config.json',cfg)
 job=dict(name='gentle_refresh',candidate='gentle_refresh',worker='train_refresh116.py',output_mode='generative',backup_best=True,config='data/gentle/config.json',model_dir=cfg['model_dir'],eval_ids=c.read(R/'tasks/113_label_path/config.json')['pilot_ids'],phase_limit_seconds=3600)
 c.put(P/'gentle_refresh.json',job)
 files=['tasks/116_research_cycle/train_refresh116.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/data105.py','tasks/105_brief_supervision/loss105.py','tasks/105_brief_supervision/parse105.py','tasks/104_supervision_evidence/training104.py','tasks/107_support_aux/checkpoint107.py']
 for name in files:
  dest=B/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,dest)
 with tarfile.open(P/'gentle_bundle.tar.gz','w:gz',compresslevel=1) as t:
  for f in B.rglob('*'):
   if f.is_file():t.add(f,arcname=f.relative_to(B),recursive=False)
 c.put(O/'gentle_refresh_preparation.json',dict(N=196,patients=len({r['sid'] for r in rows}),GT=dict(Counter(r['GT'] for r in rows)),source114_second196=True,old107=41,new107=155,max_train_tokens=max(m['input_tokens'] for m in meta),steps=25,tail_divisor=4,learning_rate=2e-5,source_Adam_moments_retained=True,old_lr_explicitly_overridden=True,reviewed_gt_explained=41,not_reviewed=150,unresolved=5,not_efficacy_evidence=True))
 print('gentle_refresh prepared: original JSON/loss,25 steps,196 real examples')

if __name__=='__main__':main()
