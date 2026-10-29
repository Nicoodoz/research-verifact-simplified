"""Freeze the broad-data, single-token recipe before seeing its development result."""
from pathlib import Path
from collections import Counter
import sys,hashlib,shutil,tarfile
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
from tokenizer_cpu105 import CPUPinnedTokenizer
sys.path.insert(0,str(Path(__file__).parent));import classifier116 as interface
P=R/'.local_models/116_research_cycle';O=R/'outputs/116_research_cycle'
def main():
 train=c.rows(P/'data_train768.jsonl');val=c.rows(P/'data_validation128.jsonl');summary=c.read(P/'data_summary.json');assert summary['algorithm_version']=='116/data_v2_gap_only'
 assert len(train)==768 and len(val)==128 and not {str(r['sid']) for r in train}&{str(r['sid']) for r in val}
 assert Counter(r['GT'] for r in train)=={'Supported':384,'Not Supported':192,'Not Addressed':192}
 assert Counter(r['GT'] for r in val)=={'Supported':64,'Not Supported':32,'Not Addressed':32}
 tok=CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b');codeids=interface.label_token_ids(tok)
 lengths=[]
 for role,rows in [('train',train),('validation',val)]:
  for row in rows:
   ids=interface.prompt_ids(tok,row);lengths.append(dict(id=row['id'],role=role,tokens=len(ids),prompt_sha256=c.digest(c.canonical(ids))))
 by={g:sorted([r for r in train if r['GT']==g],key=lambda r:c.digest('116/batch_v1/'+r['id'])) for g in c.LABELS};ordered=[]
 for i in range(192):ordered.extend([by['Supported'][2*i],by['Supported'][2*i+1],by['Not Supported'][i],by['Not Addressed'][i]])
 assert len({r['id'] for r in ordered})==768
 batches=[dict(step=n//8+1,ids=[r['id'] for r in ordered[n:n+8]],divisor=8,consumed=n+8) for n in range(0,768,8)]
 assert all(Counter(next(r['GT'] for r in ordered if r['id']==i) for i in b['ids'])=={'Supported':4,'Not Supported':2,'Not Addressed':2} for b in batches)
 cfg=c.read(R/'tasks/107_support_aux/config.json');tr=cfg['training'];tr.pop('auxiliary');tr.update(epochs=1,learning_rate=5e-5,scheduler='four_step_warmup_cosine_to_0.1',total_steps=96,loss='restricted_three_class_CE',order='fixed_stratified_4S_2NS_2NA_batches')
 for unused in ['head_chunk_tokens','head_checkpoint_recompute']:tr.pop(unused,None)
 cfg.update(task=116,candidate='single_token_768',seed=103027,model_dir='/root/verifact_image/models/qwen3.5-9b',max_seq_length=max(13783,max(x['tokens'] for x in lengths)+1),codes=dict(zip(c.LABELS,['A','B','C'])),code_token_ids=list(codeids),training_N=768,trainable_arms=['single_token_768'],gradient_patients=32,internal_validation_patients=8,validation_N=128,validation_steps=[0,24,48,72,96],selection_rule='max internal validation MCC, then PA, then fewer false-S; no development result',confirmation40_used=False)
 cfg['evaluation']=dict(mode='single_prompt_forward_three_logits_argmax',input_interface='classifier116.messages',full_reference=True,GT_in_inputs=False,batch_size=2,free_greedy_JSON=False,output_map='A/B/C_to_original_verdict_JSON',probabilities_calibrated=False)
 cfg.pop('budget',None);cfg.pop('execution_amendment',None);cfg['design']=dict(whole_recipe=True,not_single_component_causal_ablation=True,fresh_base=True,no_auxiliary_loss=True,no_class_weights=True,no_label_smoothing=True,all_uncertain_original_GT_retained=True)
 B=P/'classifier_bundle';(B/'data/cls').mkdir(parents=True,exist_ok=True)
 c.put(B/'data/cls/config.json',cfg);c.put(R/'tasks/116_research_cycle/single_token_config.json',cfg)
 for name,rows in [('train.jsonl',ordered),('validation.jsonl',val),('lengths.jsonl',lengths)]:c.putl(B/'data/cls'/name,rows)
 c.put(B/'data/cls/plan.json',batches)
 job=dict(name='single_token_768',candidate='single_token',worker='train_classifier116.py',mode='train',backup_best=True,config='data/cls/config.json',eval_ids=c.read(R/'tasks/113_label_path/config.json')['pilot_ids'],phase_limit_seconds=7200,model_dir=cfg['model_dir'])
 c.put(P/'single_token_768.json',job)
 for name in ['tasks/116_research_cycle/train_classifier116.py','tasks/116_research_cycle/classifier116.py','tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/107_support_aux/checkpoint107.py']:
  target=B/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,target)
 with tarfile.open(P/'classifier_bundle.tar.gz','w:gz',compresslevel=1) as t:
  for f in B.rglob('*'):
   if f.is_file():t.add(f,arcname=f.relative_to(B),recursive=False)
 c.put(O/'single_token_preparation.json',dict(code_ids=list(codeids),gradient_N=768,validation_N=128,gradient_patients=32,validation_patients=8,train_tokens=sum(x['tokens'] for x in lengths if x['role']=='train'),max_tokens=max(x['tokens'] for x in lengths),original_GT_retained=True,only_confirmed_gap_excluded=15,train_uncertain_review_count=49,selected_by_training_side_only=True,training_steps=96,validation_steps=cfg['validation_steps'],loss='restricted_three_class_CE',batch_composition={'S':4,'NS':2,'NA':2},not_efficacy_evidence=True))
 print(c.canonical(c.read(O/'single_token_preparation.json')))
if __name__=='__main__':main()
