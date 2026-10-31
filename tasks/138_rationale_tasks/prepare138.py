"""Prepare a fixed auxiliary-task probe and matched replay control, no GPU/API."""
from pathlib import Path
from collections import Counter
import json,random,shutil,sys,tarfile
R=Path(__file__).resolve().parents[2];P=R/'.local_models/138_rationale_tasks'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
from tokenizer_cpu105 import CPUPinnedTokenizer
from data105 import training_plan
from data138 import encode
sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'));from prompt136 import prompt_ids

def main():
 if (P/'prepared.json').exists():raise RuntimeError('Prepared138 exists; inspect without changing frozen data')
 pool={r['id']:r for r in c.rows(R/'.local_models/133_shuffle_repeat/bundle/data/shuffle_repeat/train.jsonl')}
 reasons=c.rows(R/'.local_models/127_native_reason_data/dataset_v9_new_coverage/paired/train_verdict_reason.jsonl')
 assert len(pool)==2945 and len(reasons)==36
 reason_map={r['id']:r for r in reasons};assert len(reason_map)==36
 for i,r in reason_map.items():
  assert i in pool and all(r[k]==pool[i][k] for k in ['GT','claim','reference'])
  answer=json.loads(r['answer']);assert answer['verdict']==r['GT'] and isinstance(answer['reason'],str) and answer['reason'].strip()
 rng=random.Random(138031);available=sorted(set(pool)-set(reason_map));rng.shuffle(available)
 anchors=[]
 for sid in sorted({str(r['sid']) for r in pool.values()}):anchors.append(next(i for i in available if str(pool[i]['sid'])==sid))
 anchors+= [i for i in available if i not in anchors][:120-len(anchors)]
 assert len(anchors)==len(set(anchors))==120
 label_ids=sorted(set(anchors)|set(reason_map));assert len(label_ids)==156
 slots=[('label/'+i,i,False) for i in label_ids]+[('aux/'+i,i,True) for i in sorted(reason_map)]
 rng.shuffle(slots);tok=CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b')
 old_lengths={r['id']:r for r in c.rows(R/'.local_models/133_shuffle_repeat/bundle/data/shuffle_repeat/lengths.jsonl')}
 memo={};arm_rows={};arm_tokens={}
 for arm in ['rationale_tasks','label_replay']:
  result=[];token_rows=[]
  for sample_id,i,aux in slots:
   row=dict(pool[i],sample_id=sample_id,kind='reason' if aux and arm=='rationale_tasks' else 'label')
   if row['kind']=='reason':row['answer']=json.loads(reason_map[i]['answer'])['reason'];row.pop('messages',None)
   key=(i,row['kind'])
   if key not in memo:
    memo[key]=encode(tok,row)
    if row['kind']=='label':assert memo[key]['prompt_token_sha256']==old_lengths[i]['prompt_token_sha256']
   e=memo[key];assert len(e['input_ids'])<=16384 and e['groups'][-1]>0
   result.append(row);token_rows.append(dict(sample_id=sample_id,original_id=i,kind=row['kind'],input_ids=e['input_ids'],groups=e['groups'],prompt_tokens=e['prompt_tokens'],answer_tokens=e['answer_tokens']))
  arm_rows[arm]=result;arm_tokens[arm]=token_rows
 plan=training_plan([x[0] for x in slots],epochs=2,accumulation=8)
 assert len(plan)==48 and plan[-1]['consumed']==384 and all(x['loss_divisor']==8 for x in plan)
 selected=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
 inputs={r['id']:r for r in c.rows(R/'.local_models/134_author_baselines/bundle/data/inputs.jsonl')}
 oldeval={}
 for f in (R/'.local_models/136_claim_repeat_transfer/evidence/screen160/claim_repeat').glob('*.json'):
  r=c.read(f)
  if 'id' in r:oldeval[r['id']]=r
 evalrows=[]
 for i in sorted(selected):
  tokens=prompt_ids(tok,inputs[i]);sha=c.digest(c.canonical(tokens));assert sha==oldeval[i]['prompt_token_sha256'] and len(tokens)+384<=16384
  evalrows.append(dict(id=i,input_ids=tokens,prompt_token_sha256=sha))
 train_patients={str(pool[i]['sid']) for i in label_ids};keys={r['id']:r for r in c.rows(R/'.local_models/134_author_baselines/keys.jsonl')}
 assert len(train_patients)==32 and not train_patients&{str(keys[i]['sid']) for i in selected}
 session=c.read(R/'.local_models/133_shuffle_repeat/run20261031/session.json')
 for arm in arm_rows:
  B=P/arm/'bundle';c.putl(B/'data/train.jsonl',arm_rows[arm]);c.putl(B/'data/train_tokens.jsonl',arm_tokens[arm]);c.put(B/'data/plan.json',plan);c.putl(B/'data/eval_tokens.jsonl',evalrows);c.put(B/'data/session.json',session)
  job=dict(task=138,arm=arm,seed=138031,model_dir='/root/verifact_image/models/qwen3.5-9b',source_adapter='/root/autodl-tmp/verifact134/adapter120',source_sha256='47e129876475499628de7eca934ee9df156dbaef721f8de26abae31853c7a48a',train_N=192,steps=48,presentations=384,learning_rate=1e-5,phase_limit_seconds=5400,save_reserve_seconds=300,max_seq_length=16384,eval_N=160,eval_input='unchanged136 claim_repeat',classification_gain_not_inferred_from_training=True)
  c.put(B/'data/job.json',job);c.put(P/arm/'job.json',job)
 summary=dict(status='CPU_PREPARED_NOT_RUN',source='120 final369 weights; fresh Adam',seed=138031,reason_N=36,reason_patients=21,reason_GT=dict(Counter(r['GT'] for r in reasons)),extra_anchor_N=120,label_unique_N=156,all_train_patients=32,slots_per_epoch=192,epochs=2,updates=48,presentations=384,
  candidate_tasks_per_epoch={'label':156,'reason':36},control_tasks_per_epoch={'label':192},same_original_ID_exposure=True,eval_N=160,eval_input_matches136=True,GT_unchanged=True,no_new_reason_generated=True,max_training_tokens=max(len(e['input_ids']) for data in arm_tokens.values() for e in data),new_API=0)
 c.put(P/'prepared.json',summary);c.put(R/'outputs/138_rationale_tasks/preparation.json',summary)
 c.putl(R/'outputs/138_rationale_tasks/training_manifest_sanitized.jsonl',[dict(sample_id=s,original_id=i,auxiliary_slot=a,sid=str(pool[i]['sid']),GT=pool[i]['GT']) for s,i,a in slots])
 print(c.canonical(summary))
if __name__=='__main__':main()
