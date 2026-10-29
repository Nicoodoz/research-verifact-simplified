"""Fixed-budget second-pass refresh; metadata matching, no evaluation outcome selection."""
from pathlib import Path
from collections import Counter,defaultdict
import json,sys,hashlib
import numpy as np
from scipy.optimize import linear_sum_assignment
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/109_boundary_replay'));import common109 as c
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));from data105 import encode,shared
from tokenizer_cpu105 import CPUPinnedTokenizer
P=R/'.local_models/114_matched_refresh';O=R/'outputs/114_matched_refresh'
def fingerprint(r):return str(r['sid']),r['claim_sha256'],r['reference_sha256']
def cell(r):return str(r['sid']),r['GT'],r['author'],int(r['length_quartile'])
def rank(i):return hashlib.sha256(('114/matched_refresh/'+i).encode()).hexdigest()
def main():
 P.mkdir(exist_ok=True);O.mkdir(parents=True,exist_ok=True)
 old=c.rows(R/'.local_models/107_support_aux/gpu_bundle_5090_run/data/train/label_only.jsonl');assert len(old)==196
 pool=c.rows(R/'outputs/106_label_preparation/data_pool_index.jsonl');meta={r['id']:r for r in pool};oldids={r['id'] for r in old};assert len(oldids)==196 and all(meta[i]['retained104'] for i in oldids)
 iso={r['id'] for name in ['data_isolation.jsonl','data_additional_isolation.jsonl'] for r in c.rows(R/'outputs/106_label_preparation'/name)}
 oldprints={fingerprint(meta[i]) for i in oldids};gtsets=defaultdict(set)
 for r in pool:gtsets[fingerprint(r)].add(r['GT'])
 maxlen=max(meta[i]['input_tokens'] for i in oldids);available={};exclusions=Counter()
 for r in sorted(pool,key=lambda r:rank(r['id'])):
  reason=None
  if r['id'] in oldids:reason='original196'
  elif r['id'] in iso or r['additional106_current_input_gap'] or r['semantic104_status']=='reference_gap':reason='known_input_gap'
  elif fingerprint(r) in oldprints:reason='same_original_input'
  elif len(gtsets[fingerprint(r)])>1:reason='identical_input_conflicting_GT'
  elif r['input_tokens']>maxlen:reason='above_original_max_length'
  elif fingerprint(r) in available:reason='duplicate_new_input'
  if reason:exclusions[reason]+=1
  else:available[fingerprint(r)]=r
 groups=defaultdict(list);slots=defaultdict(list)
 for r in available.values():groups[cell(r)].append(r)
 for n,r in enumerate(old):slots[cell(meta[r['id']])].append(n)
 second_ids=[r['id'] for r in old];assignments=[]
 for group,indices in slots.items():
  candidates=sorted(groups[group],key=lambda r:rank(r['id']));n=len(indices);cost=np.full((n,len(candidates)+n),1e7,dtype=float)
  for j,idx in enumerate(indices):
   for k,r in enumerate(candidates):cost[j,k]=abs(meta[old[idx]['id']]['input_tokens']-r['input_tokens'])+k*1e-6
  ii,jj=linear_sum_assignment(cost)
  for a,b in zip(ii,jj):
   if b<len(candidates):second_ids[indices[a]]=candidates[b]['id']
 original_sum=sum(meta[r['id']]['input_tokens'] for r in old);delta=sum(meta[i]['input_tokens'] for i in second_ids)-original_sum;restored=0
 while abs(delta)>.02*(2*original_sum):
  candidates=[n for n,i in enumerate(second_ids) if i!=old[n]['id'] and (meta[i]['input_tokens']-meta[old[n]['id']]['input_tokens'])*delta>0]
  assert candidates
  n=max(candidates,key=lambda n:abs(meta[second_ids[n]]['input_tokens']-meta[old[n]['id']]['input_tokens']));delta-=meta[second_ids[n]]['input_tokens']-meta[old[n]['id']]['input_tokens'];second_ids[n]=old[n]['id'];restored+=1
 newids=set(second_ids)-oldids;assert len(newids)==sum(i!=old[n]['id'] for n,i in enumerate(second_ids))
 raw={r['id']:r for r in c.rows(R/'.local_models/103_lora_selection/eligible.jsonl') if r['id'] in newids};assert set(raw)==newids
 new={}
 for i in newids:
  r=raw[i];m=meta[i];assert r['GT']==m['GT'] and str(r['sid'])==str(m['sid']) and r['role']=='train'
  assert shared.digest(r['claim'])==m['claim_sha256'] and shared.digest(r['reference'])==m['reference_sha256']
  answer=c.canonical({'verdict':r['GT']});new[i]=dict(id=i,sid=str(r['sid']),author=r['author'],GT=r['GT'],claim=r['claim'],reference=r['reference'],reference_id=r['reference_id'],reference_sha256=m['reference_sha256'],claim_sha256=m['claim_sha256'],answer=answer,answer_text=answer,messages=shared.messages(r['claim'],r['reference']))
 oldmap={r['id']:r for r in old};second=[oldmap[i] if i in oldmap else new[i] for i in second_ids];train=old+second;tok=CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b');lengths=[]
 for idx,r in enumerate(train):
  e=encode(tok,r);assert e['prompt_tokens']==meta[r['id']]['input_tokens']
  lengths.append(dict(index=idx,id=r['id'],prompt_tokens=e['prompt_tokens'],total_tokens=len(e['input_ids']),prompt_token_sha256=e['prompt_token_sha256'],answer_sha256=e['answer_sha256']))
 for n,r in enumerate(second):
  before=old[n];assert cell(meta[before['id']])==cell(meta[r['id']]);assignments.append(dict(slot=n,old_id=before['id'],second_id=r['id'],replaced=r['id']!=before['id'],sid=str(r['sid']),GT=r['GT'],author=r['author'],length_quartile=meta[r['id']]['length_quartile'],old_tokens=meta[before['id']]['input_tokens'],second_tokens=meta[r['id']]['input_tokens'],old_semantic_status=meta[before['id']]['semantic104_status'],second_semantic_status=meta[r['id']]['semantic104_status']))
 plan=[]
 for epoch in range(2):
  for start in range(0,196,8):
   inds=list(range(epoch*196+start,epoch*196+min(start+8,196)));plan.append(dict(step=len(plan)+1,epoch=epoch+1,indices=inds,consumed=epoch*196+min(start+8,196),divisor=len(inds)))
 assert len(plan)==50 and plan[-1]['consumed']==392 and [p['divisor'] for p in plan if p['divisor']!=8]==[4,4]
 for a,b in zip(plan[:25],plan[25:]):assert [train[i]['GT'] for i in a['indices']]==[train[i]['GT'] for i in b['indices']]
 role=c.read(R/'outputs/103_lora_selection/patient_roles.json')['patients'];assert {str(r['sid']) for r in train}<=set(map(str,role['train'])) and not {str(r['sid']) for r in train}&set(map(str,role['selection']+role['confirmation']))
 for name,value in [('train.jsonl',train),('train_lengths.jsonl',lengths)]:c.putl(P/name,value)
 c.put(P/'plan.json',plan);c.putl(O/'second_pass_manifest.jsonl',assignments)
 review=[]
 for author in ['human','llm']:
  for g in ['Not Supported','Not Addressed']:
   group=[new[i] for i in sorted(newids,key=rank) if new[i]['author']==author and new[i]['GT']==g]
   if group:review.append(group[0])
 c.putl(P/'review_inputs.jsonl',review)
 summary=dict(task=114,original_unique=196,second_replaced=len(newids),second_repeated=196-len(newids),total_unique=len(oldids|newids),presentations=392,updates=50,per_pass_GT=dict(Counter(r['GT'] for r in old)),same_patient_GT_author_length_quartile_per_slot=True,same_GT_each_optimizer_batch=True,original_input_tokens=2*original_sum,new_input_tokens=2*original_sum+delta,input_tokens_relative_change=delta/(2*original_sum),max_prompt_tokens=maxlen,restored_for_token_budget=restored,exclusions=dict(exclusions),new_semantic_status=dict(Counter(meta[i]['semantic104_status'] for i in newids)),review_N=len(review),source='original40_train_patients_only',no_evaluation_outcomes_for_selection=True,not_independently_clinically_validated=True)
 c.put(O/'data_summary.json',summary);print(c.canonical(summary))
if __name__=='__main__':main()
