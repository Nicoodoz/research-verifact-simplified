"""Freeze anchor+extra controls and one relation-aware dynamic supplement."""
import copy,csv,difflib,itertools,re
from collections import Counter
import numpy as np
from common074 import *
MATERIALS=['outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl','outputs/019_support_boundary_screen/selection/preparation/inputs.jsonl','outputs/020_lambda2_patient_validation/new10/base_preparation_001/inputs.jsonl']
PATTERNS={
 'causal':r'\b(due to|secondary to|because|result(?:ed|ing)?|caus\w*|improved with|in the setting of)\b',
 'time':r'\b(before|after|prior|following|post\w*|pod|overnight|night|day|days)\b|\[\*\*\d',
 'discharge':r'\b(discharge\w*|outpatient|home)\b',
 'negation':r'\b(no|not|without|denied|denies|negative|absent)\b',
 'plan':r'\b(plan\w*|scheduled|will|recommend\w*|pending)\b',
 'change':r'\b(start\w*|stop\w*|restart\w*|continu\w*|held|removed|wean\w*|resolv\w*|improv\w*|increas\w*|decreas\w*|tighten\w*)\b',
 'quantity':r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|mm|ml|mmhg|l|units?|percent|%|s\b)|\b(?:dose|pressure|rate)\b',
}
def clean(t):
 t=re.sub(r'\[\*\*(.*?)\*\*\]',lambda m:m[1] if re.fullmatch(r'[\d\-/ ]+',m[1]) else ' ',t.lower())
 return ' '.join(re.findall(r'[a-z]+|\d+(?:\.\d+)?',t))
def tags(t):return {k for k,p in PATTERNS.items() if re.search(p,t.lower())}
def relsim(a,b):return len(a&b)/len(a|b) if a|b else 0.
def normalized_vectors(targets,pool):
 needed={text_hash(x['claim']) for x in targets+pool};vectors={};sources={}
 caches=[('outputs/073_clinical_example_matching','vector_ids.json','claim_vectors.npy'),('outputs/008_retrieval_planning/candidates_001','embedding_ids.json','embedding_vectors.npy'),('outputs/009_retrieval_baselines/confirmation_001/candidates','embedding_ids.json','vectors.npy'),('outputs/016_disagreement_triggered_review_validation/stage1/candidates_001','embedding_ids.json','vectors.npy'),('outputs/020_lambda2_patient_validation/new10/candidates_001','embedding_ids.json','vectors.npy'),('outputs/031_training_expansion_confirmation/materials_001','embedding_ids.json','vectors.npy')]
 for rel,kf,vf in caches:
  p=ROOT/rel;keys=read(p/kf);arr=np.load(p/vf,allow_pickle=False)
  for k,v in zip(keys,arr):
   if k in needed and k not in vectors:vectors[k]=v;sources[k]=rel+'/'+vf
 base=ROOT/'outputs/031_training_expansion_confirmation'
 for j in lines(base/'materials_001/embedding_jobs.jsonl'):
  if not (needed-vectors.keys())&set(j['text_ids']):continue
  prefix=digest(j['request_id'])[:24]
  for p in (base/'attempts').glob(prefix+'_*/request.json'):
   if not (p.parent/'receipt.json').exists():continue
   rq=read(p);rc=read(p.parent/'receipt.json');assert rq['job']['request_id']==j['request_id'] and rc['request_sha256']==sha(p)
   if rc['transport']['http_status']!=200:continue
   body=read_body=__import__('json').loads(rc['transport']['body_text'])
   for z in body['data']:
    k=j['text_ids'][z['index']]
    if k in needed:vectors[k]=np.asarray(z['embedding'],float);sources[k]=(p.parent/'receipt.json').relative_to(ROOT).as_posix()
 assert needed<=vectors.keys(),('uncached',needed-vectors.keys())
 keys=sorted(needed);arr=np.asarray([vectors[k] for k in keys]);assert np.isfinite(arr).all() and (np.linalg.norm(arr,axis=1)>0).all()
 np.save(OUT/'claim_vectors.npy',arr,allow_pickle=False);put(OUT/'vector_ids.json',keys);put(OUT/'vector_sources.json',sources)
 return {k:arr[i]/np.linalg.norm(arr[i]) for i,k in enumerate(keys)}
def main():
 OUT.mkdir(exist_ok=False)
 old=read(ROOT/'outputs/073_clinical_example_matching/freeze.json');ann=annotations();mats={}
 for rel in MATERIALS:
  for x in lines(ROOT/rel):
   pid=x['proposition_id']
   if pid not in mats:mats[pid]=dict(id=pid,sid=str(x['subject_id']),author=x['author_type'],claim=x['text'],reference=x['reference'],source=rel)
 used=set()
 for rel in ['outputs/072_adaptive_judge_examples/target_blind.jsonl','outputs/073_clinical_example_matching/target_blind.jsonl']:
  used|={x['id'] for x in lines(ROOT/rel)}
 targets=[];gold=[];sampling=[]
 for sid in old['pilot_patients']+old['confirmation_patients']:
  for author in ['human','llm']:
   rows=sorted([x for x in mats.values() if x['sid']==sid and x['author']==author and x['id'] not in used and ann[x['id']]['invalid']=='False'],key=lambda x:text_hash('074/sample:'+x['id']))
   chosen=[]
   for label in ['Not Supported','Not Addressed','Supported']:
    match=[x for x in rows if ann[x['id']]['human_gt']==label]
    if match:chosen.append(match[0])
   for x in rows:
    if len(chosen)==3:break
    if x not in chosen:chosen.append(x)
   assert len(chosen)==3,(sid,author,len(chosen))
   targets+=chosen
   gold.extend(dict(id=x['id'],sid=sid,GT=ann[x['id']]['human_gt']) for x in chosen)
   sampling.append(dict(sid=sid,author=author,available_by_gt=dict(Counter(ann[x['id']]['human_gt'] for x in rows)),selected_ids=[x['id'] for x in chosen]))
 pool=lines(ROOT/'outputs/073_clinical_example_matching/example_pool.jsonl')
 assert all(x['sid'] in old['teaching_patients'] for x in pool)
 assert not {x['sid'] for x in targets}&{x['sid'] for x in pool}
 for x in pool:
  a=ann[x['proposition_id']];assert a['initial_agreement']=='3' and a['invalid']=='False' and a['time_metadata_conflict']=='False' and a['second_round_anomaly']=='False'
  assert [a[k] for k in ['verdict1','verdict2','verdict3']]==[x['physician_label']]*3
 vectors=normalized_vectors(targets,pool);pv=np.asarray([vectors[text_hash(x['claim'])] for x in pool]);pt=[tags(x['claim']) for x in pool]
 extras=[i for i in range(4,len(pool)) if all(difflib.SequenceMatcher(None,clean(pool[i]['claim']),clean(x['claim'])).ratio()<.85 for x in pool[:4])]
 pairs=[(i,j) for i,j in itertools.combinations(extras,2) if pool[i]['sid']!=pool[j]['sid'] and difflib.SequenceMatcher(None,clean(pool[i]['claim']),clean(pool[j]['claim'])).ratio()<.85]
 def score(t,i,v):return .65*float(v@pv[i])+.35*relsim(tags(t),pt[i])
 # Static pair = two medoids of the teaching pool, not selected against evaluation claims/results.
 static=sorted(pairs,key=lambda pair:(-np.mean([max(score(x['claim'],i,pv[k]) for i in pair) for k,x in enumerate(pool)]),pair))[0]
 def serialized(i):return canonical(dict(proposition=pool[i]['claim'],reference=pool[i]['reference'],physician_label=pool[i]['physician_label']))
 fixed_chars=sum(len(serialized(i)) for i in static)
 pairs=[p for p in pairs if .9<=sum(len(serialized(i)) for i in p)/fixed_chars<=1.1]
 assert static in pairs
 prefix='\n\n## Clinician-labeled examples from four other patients\nEach example contains a proposition, EHR reference, and physician label. Examples are not evidence about the patient in the actual task. For the actual task use only its supplied reference.\n'
 suffix='\nTwo additional clinician-labeled examples from other patients:\n'
 template=next(j['body'] for j in lines(ROOT/'outputs/053_thinking_prior_validation/main_jobs.jsonl') if j['condition']=='T-S')
 jobs=[];selection=[]
 for t in targets:
  tv=vectors[text_hash(t['claim'])];eligible=[p for p in pairs if all(difflib.SequenceMatcher(None,clean(t['claim']),clean(pool[i]['claim'])).ratio()<.85 for i in p)]
  assert eligible
  dynamic=sorted(eligible,key=lambda p:(-sum(score(t['claim'],i,tv) for i in p)+.10*float(pv[p[0]]@pv[p[1]]),p))[0]
  stage='pilot' if t['sid'] in old['pilot_patients'] else 'confirmation'
  b=copy.deepcopy(template);b['messages'][-1]['content']=canonical(dict(proposition=t['claim'],reference=t['reference']))
  f4=copy.deepcopy(b);f4['messages'][0]['content']+=prefix+'\n'.join(serialized(i) for i in range(4))+'\n'
  f6=copy.deepcopy(f4);f6['messages'][0]['content']+=suffix+'\n'.join(serialized(i) for i in static)+'\n'
  h6=copy.deepcopy(f4);h6['messages'][0]['content']+=suffix+'\n'.join(serialized(i) for i in dynamic)+'\n'
  for arm,body in [('B',b),('F4',f4),('F6',f6),('H6',h6)]:
   h=digest(body);jobs.append(dict(request_id='074_'+stage+'_'+h[:24],stage=stage,id=t['id'],sid=t['sid'],arm=arm,body=body,body_sha256=h))
  selection.append(dict(id=t['id'],sid=t['sid'],stage=stage,target_tags=sorted(tags(t['claim'])),static_ids=[pool[i]['proposition_id'] for i in static],dynamic_ids=[pool[i]['proposition_id'] for i in dynamic],dynamic_scores=[score(t['claim'],i,tv) for i in dynamic],dynamic_tags=[sorted(pt[i]) for i in dynamic],dynamic_labels=[pool[i]['physician_label'] for i in dynamic],added_length_ratio=sum(len(serialized(i)) for i in dynamic)/fixed_chars))
 jl(OUT/'target_blind.jsonl',targets);jl(OUT/'target_gt.jsonl',gold);jl(OUT/'example_pool.jsonl',pool);jl(OUT/'selections.jsonl',selection);jl(OUT/'all_arm_jobs.jsonl',jobs);jl(OUT/'sampling.jsonl',sampling)
 pilot=[j for j in jobs if j['stage']=='pilot'];jl(OUT/'pilot_aliases.jsonl',pilot);unique={j['request_id']:j for j in pilot};jl(OUT/'pilot_jobs.jsonl',sorted(unique.values(),key=lambda j:text_hash('074/order:'+j['request_id'])))
 fallback={x['proposition_id']:x['U2'] for x in csv.DictReader((ROOT/'outputs/034_same_data_comparison/predictions_common.csv').open(encoding='utf-8-sig'))};assert all(t['id'] in fallback for t in targets);put(OUT/'fallback_u2.json',{t['id']:fallback[t['id']] for t in targets})
 summary=dict(target_n=len(targets),gt=dict(Counter(x['GT'] for x in gold)),gt_by_author=dict(Counter(mats[x['id']]['author']+'/'+x['GT'] for x in gold)),pilot_logical=len(pilot),pilot_unique=len(unique),pool_size=len(pool),static_extra=[dict(id=pool[i]['proposition_id'],claim=pool[i]['claim'],label=pool[i]['physician_label'],tags=sorted(pt[i])) for i in static],extra_chars=fixed_chars,dynamic_distinct_pairs=len({tuple(x['dynamic_ids']) for x in selection}),dynamic_same_as_fixed=sum(x['dynamic_ids']==x['static_ids'] for x in selection),embedding_API_calls=0)
 put(OUT/'offline_summary.json',summary)
 artifacts=[p for p in OUT.iterdir() if p.is_file()]
 source_files=[TASK/n for n in ['prepare074.py','common074.py','run074.py','analyze074.py','decide074.py','README.md']]+[ROOT/rel for rel in MATERIALS]+[ROOT/'outputs/073_clinical_example_matching/manifest.json',ROOT/'outputs/053_thinking_prior_validation/freeze.json',ROOT/'outputs/053_thinking_prior_validation/main_jobs.jsonl',ROOT/'outputs/034_same_data_comparison/predictions_common.csv',ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv']
 put(OUT/'freeze.json',dict(status='FROZEN_BEFORE_074_API',created_utc=now(),cap_cny=20.,model=template['model'],pilot_patients=old['pilot_patients'],confirmation_patients=old['confirmation_patients'],teaching_patients=old['teaching_patients'],pilot_n=36,confirmation_n=60,source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in source_files},artifact_sha256={p.name:sha(p) for p in artifacts}))
 print(canonical(summary))
if __name__=='__main__':main()
