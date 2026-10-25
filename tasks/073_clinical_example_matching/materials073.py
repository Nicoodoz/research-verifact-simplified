"""Offline material inventory and cached BGE extraction; no paid calls."""
import csv,json,hashlib,re
from collections import Counter
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/073_clinical_example_matching'
OLD=ROOT/'outputs/031_training_expansion_confirmation'
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p): return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def put(p,x):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f: json.dump(x,f,ensure_ascii=False,indent=2)
def jl(p,x):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f:
  for r in x:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
def build():
 OUT.mkdir(exist_ok=True)
 assert not (OUT/'target_blind.jsonl').exists(), 'Do not overwrite completed material generation'
 f=read(ROOT/'outputs/072_adaptive_judge_examples/freeze.json')
 ann={x['proposition_id']:x for x in csv.DictReader((ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv').open(encoding='utf-8-sig'))}
 mats=lines(OLD/'judge_inputs_001/materials.jsonl')
 seen={x['proposition_id'] for x in mats}
 for rel,kind in [('outputs/019_support_boundary_screen/selection/preparation/inputs.jsonl','019'),('outputs/009_retrieval_baselines/development_001/judge_preparation/inputs.jsonl','009'),('outputs/016_disagreement_triggered_review_validation/stage1/base_preparation_001/inputs.jsonl','016'),('outputs/020_lambda2_patient_validation/new10/base_preparation_001/inputs.jsonl','020')]:
  for x in lines(ROOT/rel):
   pid=x['proposition_id']
   if pid in seen or pid not in ann:continue
   ref=x['retrieval']['C48']['reference'] if kind=='009' else x['reference']
   mats.append(dict(proposition_id=pid,subject_id=ann[pid]['subject_id'],author_type=ann[pid]['author_type'],text=x['text'],reference=ref,source_file=rel));seen.add(pid)
 oldpool=lines(ROOT/'outputs/072_adaptive_judge_examples/example_pool.jsonl')
 pool=list(oldpool); ids={x['proposition_id'] for x in pool}
 for label in ('Supported','Not Supported','Not Addressed'):
  cand=[x for x in mats if x['subject_id'] in f['teaching_patients'] and x['proposition_id'] not in ids and ann[x['proposition_id']]['human_gt']==label and ann[x['proposition_id']]['initial_agreement']=='3' and ann[x['proposition_id']]['invalid']=='False' and ann[x['proposition_id']]['second_round_anomaly']=='False' and ann[x['proposition_id']]['time_metadata_conflict']=='False']
  cand.sort(key=lambda x:digest('073/pool:'+x['proposition_id']))
  counts=Counter();chosen=[]
  for x in cand:
   if counts[x['subject_id']]>=2:continue
   counts[x['subject_id']]+=1;chosen.append(x)
   if len(chosen)==8:break
  for x in chosen:
   pid=x['proposition_id'];pool.append(dict(proposition_id=pid,sid=x['subject_id'],claim=x['text'],reference=x['reference'],physician_label=label,source_file=x.get('source_file','outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl'),annotation=ann[pid],selection='full_final_reference'))
 if not (OUT/'pool_candidates.jsonl').exists():jl(OUT/'pool_candidates.jsonl',pool)
 else:
  assert not (OUT/'target_blind.jsonl').exists()
  n=len(list(OUT.glob('pool_candidates_incomplete_*.jsonl')))
  (OUT/'pool_candidates.jsonl').rename(OUT/f'pool_candidates_incomplete_{n:02}.jsonl')
  jl(OUT/'pool_candidates.jsonl',pool)
 # Fresh claims within the existing 16 development patients; labels only used by fixed sampler.
 used={x['id'] for x in lines(ROOT/'outputs/072_adaptive_judge_examples/target_blind.jsonl')}
 targets=[];gold=[]
 for sid in f['pilot_patients']+f['confirmation_patients']:
  rows=[x for x in mats if x['subject_id']==sid and x['proposition_id'] not in used and ann[x['proposition_id']]['invalid']=='False']
  rows.sort(key=lambda x:digest('073/target:'+x['proposition_id']))
  chosen=[]
  # Human claims: one of each class if available; remaining slots deterministic.
  for lab in ('Not Supported','Not Addressed','Supported'):
   matches=[x for x in rows if x['author_type']=='human' and ann[x['proposition_id']]['human_gt']==lab and x not in chosen]
   if matches:chosen.append(matches[0])
  for author,n in [('human',3),('llm',3)]:
   for x in rows:
    if sum(z['author_type']==author for z in chosen)>=n:break
    if x['author_type']==author and x not in chosen:chosen.append(x)
  assert len(chosen)==6,(sid,len(chosen))
  for x in chosen:
   targets.append(dict(id=x['proposition_id'],sid=sid,author=x['author_type'],claim=x['text'],reference=x['reference']))
   gold.append(dict(id=x['proposition_id'],sid=sid,GT=ann[x['proposition_id']]['human_gt']))
 jl(OUT/'target_blind.jsonl',targets);jl(OUT/'target_gt.jsonl',gold)
 extract_vectors(targets,pool,gold)

def extract_vectors(targets,pool,gold):
 needed={digest(x['claim']) for x in targets+pool}
 base=OLD/'materials_001'
 vectors={k:v for k,v in zip(read(base/'embedding_ids.json'),np.load(base/'vectors.npy',allow_pickle=False)) if k in needed}
 sources={k:str(base.relative_to(ROOT)/'vectors.npy') for k in vectors}
 jobs=lines(base/'embedding_jobs.jsonl')
 for j in jobs:
  if not needed.intersection(j['text_ids']):continue
  prefix=hashlib.sha256(json.dumps(j['request_id'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]
  # common031.digest uses canonical JSON; only inspect this embedding job's receipts.
  paths=list((OLD/'attempts').glob(prefix+'_*/request.json'))
  if not paths:
   # The historic digest format is verified by actual request IDs, not assumed.
   paths=[p for p in (OLD/'attempts').glob('*/request.json') if read(p)['job']['request_id']==j['request_id']]
  for p in paths:
   rq=read(p);rp=p.parent/'receipt.json'
   if not rp.exists():continue
   rec=read(rp);assert rec['request_sha256']==sha(p)
   tr=rec['transport']
   if tr['http_status']!=200:continue
   native=json.loads(tr['body_text'])
   for z in native['data']:
    k=j['text_ids'][z['index']]
    if k in needed:vectors[k]=np.asarray(z['embedding'],float);sources[k]=rp.relative_to(ROOT).as_posix()
 # Old 072 examples absent from 031 may have matching embedding caches in 008/016.
 for rel,idfile,vecfile in [('outputs/008_retrieval_planning/candidates_001','embedding_ids.json','embedding_vectors.npy'),('outputs/009_retrieval_baselines/confirmation_001/candidates','embedding_ids.json','vectors.npy'),('outputs/016_disagreement_triggered_review_validation/stage1/candidates_001','embedding_ids.json','vectors.npy'),('outputs/020_lambda2_patient_validation/new10/candidates_001','embedding_ids.json','vectors.npy')]:
  b=ROOT/rel;keys=read(b/idfile);arr=np.load(b/vecfile,allow_pickle=False)
  for k,v in zip(keys,arr):
   if k in needed and k not in vectors:vectors[k]=v;sources[k]=rel+'/'+vecfile
 assert needed<=vectors.keys(),('missing_embeddings',sorted(needed-vectors.keys()))
 keys=sorted(needed);np.save(OUT/'claim_vectors.npy',np.asarray([vectors[k] for k in keys]),allow_pickle=False)
 put(OUT/'vector_ids.json',keys);put(OUT/'vector_sources.json',sources)
 summary={'pool':len(pool),'labels':dict(Counter(x['physician_label'] for x in pool)),'target':len(targets),'GT':dict(Counter(x['GT'] for x in gold)),'embedding_new_calls':0}
 put(OUT/'material_inventory.json',summary);print(summary)
 # Human-readable candidates and exact references, for instructional compatibility review.
 with (OUT/'pool_review.md').open('x',encoding='utf-8',newline='\n') as q:
  for i,x in enumerate(pool):
   q.write(f"## {i+1}. {x['proposition_id']} | {x['physician_label']} | {x['sid']}\n\n{x['claim']}\n\n{x['reference']}\n\n")
if __name__=='__main__':
 if (OUT/'target_blind.jsonl').exists():extract_vectors(lines(OUT/'target_blind.jsonl'),lines(OUT/'pool_candidates.jsonl'),lines(OUT/'target_gt.jsonl'))
 else:build()
