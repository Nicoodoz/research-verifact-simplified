"""Freeze metadata-only nested screening and construct private model inputs."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys,shutil,tarfile
from collections import Counter
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
P=R/'.local_models/117_verdict_probe';O=R/'outputs/117_verdict_probe'
def main():
 P.mkdir(exist_ok=True);O.mkdir(parents=True,exist_ok=True)
 rec=c.read(R/'.local_models/117_semantic_probe/data_recommendation.json')
 split=rec['training_pool'];train=split['first_head_training']['ids'];val_sids=set(split['validation_patient_ids'])
 raw={r['id']:r for r in c.rows(R/'.local_models/106_label_preparation/training_pool.jsonl')}
 index={r['id']:r for r in c.rows(R/'outputs/106_label_preparation/data_pool_index.jsonl')}
 val=sorted(i for i,r in index.items() if str(r['sid']) in val_sids);screen=rec['coarse_screen']['ids']
 assert len(train)==1024 and len(val)==730 and len(screen)==160 and not set(train)&set(val)
 assert not {str(raw[i]['sid']) for i in train}&val_sids
 keys={r['id']:r for r in c.rows(R/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
 inputs={r['id']:r for r in c.rows(R/'.local_models/116_research_cycle/inputs_selection1817.jsonl')}
 base={r['id']:r for r in c.rows(R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
 assert all(keys[i]['old_panel'] in ('natural','pressure') for i in screen)
 metadata=[];payload=[]
 for role,ids in [('train',train),('validation',val),('screen',screen)]:
  for i in ids:
   if role=='screen':
    m=keys[i];item=inputs[i]
   else:
    m=index[i];item=dict(id=i,claim=raw[i]['claim'],reference=raw[i]['reference'],expected_prompt_sha256=m['input_token_sha256'])
   metadata.append(dict(id=i,sid=str(m['sid']),GT=m['GT'],author=m['author'],role=role,panel=m.get('old_panel'),paper_r1=m.get('paper_r1'),baseline107=base[i]['verdict'] if role=='screen' else None))
   payload.append({k:item[k] for k in ('id','claim','reference','expected_prompt_sha256')})
 assert len({r['id'] for r in payload})==1914
 cfg113=c.read(R/'tasks/113_label_path/config.json')
 session=dict(cycle=2,start_epoch=1793287154,start_beijing='2026-10-29 23:19:14',duration_seconds=36000,deadline_beijing='2026-10-30 09:19:14',GPU_cap_CNY=15.8,API_cap_CNY=80,hourly_CNY=1.58,no_shutdown=True)
 job=dict(name='features_initial',worker='extract117.py',ids=[r['id'] for r in payload],model_dir='/root/verifact_image/models/qwen3.5-9b',adapter_path=cfg113['adapter_path'],adapter_sha256=cfg113['adapter_sha256'],inputs='data/inputs.jsonl',max_seq_length=16384,batch_size=4,phase_limit_seconds=10800)
 B=P/'bundle';(B/'data').mkdir(parents=True,exist_ok=True)
 c.put(P/'session.json',session);c.put(B/'session.json',session);c.put(P/'features_initial.json',job);c.put(B/'data/features_initial.json',job)
 c.putl(P/'metadata.jsonl',metadata);c.putl(B/'data/inputs.jsonl',payload)
 c.put(P/'data_selection.json',dict(training_ids=train,validation_ids=val,screen_ids=screen,source='metadata-only fixed hash; full8 validation adopted before extraction',unreviewed_excluded=False,confirmed_gap_excluded=False))
 for name in ['tasks/117_verdict_probe/extract117.py','tasks/105_brief_supervision/common105.py','tasks/104_supervision_evidence/training104.py']:
  dst=B/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,dst)
 with tarfile.open(P/'bundle117.tar.gz','w:gz',compresslevel=1) as t:
  for f in B.rglob('*'):
   if f.is_file():t.add(f,arcname=f.relative_to(B),recursive=False)
 c.put(O/'state.json',dict(**session,status='PREPARED',active_job='features_initial',best_candidate='107_label_only',paid_API_CNY=0,confirmation40_used=False,train_N=1024,validation_N=730,screen_N=160))
 c.put(O/'preparation.json',dict(task=117,method='verdict_probe',N=len(payload),roles={r:dict(N=sum(m['role']==r for m in metadata),GT=dict(Counter(m['GT'] for m in metadata if m['role']==r)),patients=len({m['sid'] for m in metadata if m['role']==r})) for r in ['train','validation','screen']},prefix='{"verdict":"',labels_in_model_input=False,ancestor107_saw_some_internal_validation=True,unchanged_doctor_GT=True,all_raw_reference=True,unreviewed_excluded=False,head_hyperparameters_selected_on_validation_only=True))
 c.putl(O/'selection_manifest.jsonl',metadata)
 print(c.canonical(dict(input_N=len(payload),bundle_bytes=(P/'bundle117.tar.gz').stat().st_size)))
if __name__=='__main__':main()
