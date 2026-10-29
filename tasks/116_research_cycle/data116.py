"""CPU-only fixed 32/8 patient split and 768/128 real-data manifests.

No new model prediction, tokenization, GPU, API or clinical reinterpretation.
All inputs are original training40 assets. Output files are private and immutable
under the same algorithm; the single-token worker must render its own interface.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,sys

R=Path(__file__).resolve().parents[2]
P=R/'.local_models/116_research_cycle'
LABELS=('Supported','Not Supported','Not Addressed')
TRAIN_QUOTAS=dict(zip(LABELS,(384,192,192)))
VAL_QUOTAS=dict(zip(LABELS,(64,32,32)))
LONG_INPUT_MARKER=12701

def digest(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def rank(scope,value):return digest('116/data_v1/'+scope+'/'+str(value))
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def rows(path):
 with path.open(encoding='utf-8-sig') as f:
  for line in f:
   if line.strip():yield json.loads(line)
def canonical(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def frozen(path,value,lines=False):
 payload=(''.join(canonical(x)+'\n' for x in value) if lines else json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
 if path.exists():
  if path.read_bytes()!=payload:
   if '--replace-preparation' not in sys.argv:raise ValueError('Frozen data artifact changed: '+path.name)
   path.write_bytes(payload)
 else:path.write_bytes(payload)
def input_key(row):return str(row['sid']),row['claim_sha256'],row['reference_sha256']
def choose(pool,quotas,scope):
 selected=[]
 for gt,target in quotas.items():
  bags=defaultdict(list)
  for row in pool:
   if row['GT']==gt:bags[str(row['sid'])].append(row)
  for sid in bags:bags[sid].sort(key=lambda r:rank(scope+'/item',r['id']))
  order=sorted(bags,key=lambda sid:rank(scope+'/patient',sid))
  available=sum(len(x) for x in bags.values())
  if available<target:raise ValueError(f'{scope}/{gt}: available {available}, requested {target}; do not borrow selection20')
  chosen=[];cursor=defaultdict(int)
  while len(chosen)<target:
   changed=False
   for sid in order:
    if cursor[sid]<len(bags[sid]):
     chosen.append(bags[sid][cursor[sid]]);cursor[sid]+=1;changed=True
     if len(chosen)==target:break
   if not changed:raise AssertionError('Unexpected quota exhaustion')
  selected.extend(chosen)
 # The returned order is a frozen presentation list, not a model-derived rank.
 selected.sort(key=lambda r:rank(scope+'/order',r['id']))
 return selected
def describe(rr):
 lengths=sorted(r['input_tokens'] for r in rr)
 return dict(N=len(rr),patients=len({str(r['sid']) for r in rr}),GT=dict(Counter(r['GT'] for r in rr)),author=dict(Counter(r['author'] for r in rr)),
             by_GT_author={g:dict(Counter(r['author'] for r in rr if r['GT']==g)) for g in LABELS},
             source_semantic_status=dict(Counter(r['semantic104_status'] for r in rr)),
             original104_prompt_tokens=dict(sum=sum(lengths),min=min(lengths),max=max(lengths),mean=sum(lengths)/len(lengths)),
             by_patient={sid:dict(Counter(r['GT'] for r in rr if str(r['sid'])==sid)) for sid in sorted({str(r['sid']) for r in rr})})
def main():
 P.mkdir(parents=True,exist_ok=True)
 meta=list(rows(R/'outputs/106_label_preparation/data_pool_index.jsonl'));assert len(meta)==3675
 original_train=set(map(str,read(R/'outputs/103_lora_selection/patient_roles.json')['patients']['train']))
 assert len(original_train)==40 and {str(r['sid']) for r in meta}==original_train and all(r['role']=='train' for r in meta)
 old_exclusions=list(rows(R/'outputs/109_boundary_replay/exclusions.jsonl'));flagged={r['id'] for r in old_exclusions};assert len(flagged)==101
 # The cycle uses confirmed input gaps only. Historical interpretive doubts are
 # retained as flags and never treated as new evidence that physician GT is wrong.
 explicit_gaps=[r for r in old_exclusions if 'known_actual_input_gap_104_106' in r['reasons']]
 excluded={r['id'] for r in explicit_gaps};assert len(excluded)==15
 eligible=[r for r in meta if r['id'] not in excluded];assert len(eligible)==3660
 # Observe legacy-long rows, but do not exclude them on an old capacity limit.
 long=[r for r in eligible if r['input_tokens']>LONG_INPUT_MARKER]
 key_labels=defaultdict(set)
 for row in eligible:key_labels[input_key(row)].add(row['GT'])
 assert all(len(v)==1 for v in key_labels.values()) and len(key_labels)==len(eligible),'Existing109 exclusion/dedup prerequisite failed'
 # The split is independent of predictions, teacher agreement and selected methods.
 order=sorted(original_train,key=lambda sid:digest('116/internal-v1/'+sid))
 val_patients=set(order[:8]);gradient_patients=original_train-val_patients
 gradient_pool=[r for r in eligible if str(r['sid']) in gradient_patients]
 validation_pool=[r for r in eligible if str(r['sid']) in val_patients]
 train=choose(gradient_pool,TRAIN_QUOTAS,'gradient')
 val=choose(validation_pool,VAL_QUOTAS,'validation')
 assert len(train)==768 and len(val)==128 and not {r['id'] for r in train}&{r['id'] for r in val}
 assert not {str(r['sid']) for r in train}&{str(r['sid']) for r in val}
 ids={r['id'] for r in train+val};raw={}
 for row in rows(R/'.local_models/106_label_preparation/training_pool.jsonl'):
  if row['id'] in ids:
   if row['id'] in raw:raise ValueError('Duplicate source ID')
   raw[row['id']]=row
 assert set(raw)==ids
 fields=('id','sid','author','GT','claim','reference','reference_id','reference_sha256','claim_sha256')
 for part,label in [(train,'gradient_train'),(val,'internal_validation')]:
  exported=[]
  for pos,m in enumerate(part):
   source=raw[m['id']];assert source['GT']==m['GT'] and str(source['sid'])==str(m['sid'])
   assert digest(source['claim'])==m['claim_sha256'] and digest(source['reference'])==m['reference_sha256']
   record={k:source[k] if k in source else m[k] for k in fields};record['sid']=str(record['sid'])
   record.update(role='train',cycle_role=label,reference_prompt_tokens_104=m['input_tokens'],original104_prompt_token_sha256=m['input_token_sha256'])
   exported.append(record)
  filename='data_train768' if label=='gradient_train' else 'data_validation128'
  frozen(P/(filename+'.jsonl'),exported,lines=True)
  old_flags={r['id']:r['reasons'] for r in old_exclusions}
  manifest=[dict(position=i,id=m['id'],sid=str(m['sid']),GT=m['GT'],author=m['author'],reference_sha256=m['reference_sha256'],claim_sha256=m['claim_sha256'],original104_prompt_tokens=m['input_tokens'],original104_prompt_token_sha256=m['input_token_sha256'],semantic104_status=m['semantic104_status'],existing_review_flags=old_flags.get(m['id'],[]),selection_reason='fixed_GT_patient_round_robin_SHA256_quota',GT_changed=False) for i,m in enumerate(part)]
  frozen(P/(filename+'_manifest.jsonl'),manifest,lines=True)
 split=dict(algorithm='patient_SHA256_116/internal-v1',gradient_patients=sorted(gradient_patients),internal_validation_patients=sorted(val_patients),selection20_accessed=False,confirmation40_accessed=False,selection_criteria='fixed patient-round-robin within each GT; fixed SHA item/order; no predictions or teacher scores')
 frozen(P/'data_split.json',split)
 by_id={r['id']:r for r in meta};train_ids={r['id'] for r in train};val_ids={r['id'] for r in val};reasons_by_id={r['id']:r['reasons'] for r in old_exclusions}
 exclusion_counts=Counter(reason for row in old_exclusions for reason in row['reasons'])
 exclusive=Counter('known_actual_input_gap' if 'known_actual_input_gap_104_106' in row['reasons'] else 'existing_unresolved_review' if 'unresolved104_not_promoted_by_current_error' in row['reasons'] else 'other_existing_review_uncertainty' for row in old_exclusions)
 status=[]
 for row in meta:
  identifier=row['id'];why=reasons_by_id.get(identifier,[])
  decision='excluded_confirmed_actual_input_gap' if identifier in excluded else 'selected_gradient' if identifier in train_ids else 'selected_internal_validation' if identifier in val_ids else 'eligible_not_selected_by_fixed_quota'
  status.append(dict(id=identifier,sid=str(row['sid']),GT=row['GT'],author=row['author'],cycle_role='internal_validation' if str(row['sid']) in val_patients else 'gradient_train',decision=decision,
                     reasons=['confirmed_actual_input_gap'] if identifier in excluded else ['fixed_GT_patient_round_robin_SHA256_quota'] if identifier in train_ids|val_ids else ['outside_fixed_quota_after_SHA256_patient_round_robin'],existing_review_flags=why,
                     original104_prompt_tokens=row['input_tokens'],legacy_long_input_observed=row['input_tokens']>LONG_INPUT_MARKER,GT_changed=False,wrong_GT_inferred_from_exclusion=False))
 frozen(P/'data_candidate_status.jsonl',status,lines=True)
 frozen(P/'data_exclusion_manifest.jsonl',[dict(row,source_semantic_status=by_id[row['id']]['semantic104_status'],inherited_from_task109=True,wrong_GT_inferred=False) for row in explicit_gaps],lines=True)
 frozen(P/'data_review_flags.jsonl',[dict(row,source_semantic_status=by_id[row['id']]['semantic104_status'],excluded_in_this_cycle=row['id'] in excluded,wrong_GT_inferred=False) for row in old_exclusions],lines=True)
 summary=dict(algorithm_version='116/data_v2_gap_only',metadata_revision='gap_only_no_legacy_length_filter',original_pool_N=3675,inherited109_flagged_N=101,excluded_confirmed_input_gap_N=15,retained_previously_flagged_N=86,inherited109_reasons_nonexclusive=dict(exclusion_counts),inherited109_basis_exclusive=dict(exclusive),
              long_input_observations=[dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],original104_prompt_tokens=r['input_tokens'],cycle_role='internal_validation' if str(r['sid']) in val_patients else 'gradient_train',selected_in_final_manifest=r['id'] in train_ids|val_ids) for r in long],
              input_length_exclusions=[],no_input_truncation=True,old_length_marker_not_a_selection_rule=True,
              eligible_pool=describe(eligible),gradient_pool=describe(gradient_pool),validation_pool=describe(validation_pool),gradient_train=describe(train),internal_validation=describe(val),
              schedule_suggestion=dict(epochs=1,gradient_accumulation=8,updates=96,validation_checkpoints=[32,64,96],fixed_validation_N=128,extra_training_epochs_not_preselected=True),
              tokens_are_original104_interface_not_single_token_render=True,training_initializer='original base recommended;107 already has supervised exposure to all40, including these validation8',
              selected_previously_flagged=dict(gradient=sum(r['id'] in flagged for r in train),validation=sum(r['id'] in flagged for r in val)),
              original_GT_and_reference_preserved=True,new_clinical_labels=False,new_API_calls=0,new_GPU_calls=0)
 # The sample IDs stay frozen. This summary incorporates the requested precise
 # exclusion taxonomy and clarifies that no legacy length filter is applied.
 (P/'data_summary.json').write_bytes((json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))
 print(canonical({k:summary[k] for k in ('original_pool_N','inherited109_flagged_N','excluded_confirmed_input_gap_N','retained_previously_flagged_N','inherited109_reasons_nonexclusive','inherited109_basis_exclusive','long_input_observations','gradient_train','internal_validation','selected_previously_flagged','schedule_suggestion')}))
if __name__=='__main__':main()
