"""CPU-only join of existing selection20 inputs, keys and frozen107 receipts.

No new model calls, no confirmation-patient access and no GT enters model input.
Existing107 prompt-token hashes are authoritative; tokenize only if absent.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,sys

R=Path(__file__).resolve().parents[2];P=R/'.local_models/116_research_cycle'
LABELS={'Supported','Not Supported','Not Addressed'}
ADAPTER107='096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8'
def rows(path):
 with path.open(encoding='utf-8-sig') as f:
  for line in f:
   if line.strip():yield json.loads(line)
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def frozen(path,v,lines=False):
 payload=(''.join(canonical(r)+'\n' for r in v) if lines else json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
 if path.exists():
  if path.read_bytes()!=payload:raise ValueError('Existing frozen extension artifact differs: '+path.name)
 else:path.write_bytes(payload)
def main():
 cohort=list(rows(R/'.local_models/111_half_extension/cohort_keys.jsonl'));keys={r['id']:r for r in cohort}
 assert len(cohort)==len(keys)==1817 and all(r['GT'] in LABELS for r in cohort)
 roles=read(R/'outputs/103_lora_selection/patient_roles.json')['patients'];selection=set(map(str,roles['selection']))
 assert len(selection)==20 and {str(r['sid']) for r in cohort}==selection
 assert not selection&set(map(str,roles['train']))
 assert Counter(r['subset'] for r in cohort)=={'old500':500,'new':1317}
 assert Counter(r['old_panel'] for r in cohort if r['subset']=='old500')=={'natural':400,'pressure':100}
 assert all(r['old_panel'] is None for r in cohort if r['subset']=='new')
 raw_baseline=[r for r in rows(R/'outputs/111_half_extension/predictions_sanitized.jsonl') if r['arm']=='label_only107']
 baseline={r['id']:r for r in raw_baseline};assert len(raw_baseline)==len(baseline)==1817 and set(baseline)==set(keys)
 assert all(r['valid'] and r['checkpoint_adapter_sha256']==ADAPTER107 for r in baseline.values())
 for identifier,r in baseline.items():
  k=keys[identifier];assert r['GT']==k['GT'] and str(r['sid'])==str(k['sid']) and r['author']==k['author'] and r['subset']==k['subset']
 current_keys_path=P/'keys.jsonl'
 if not current_keys_path.exists():current_keys_path=R/'.local_models/113_label_path/keys.jsonl'
 ck={r['id']:r for r in rows(current_keys_path)};assert len(ck)==610 and set(ck)<=set(keys)
 for identifier,r in ck.items():
  k=keys[identifier];assert r['GT']==k['GT'] and str(r['sid'])==str(k['sid']) and r['author']==k['author']
 pilot={i:r['pilot_panel'] for i,r in ck.items() if r.get('pilot_panel') is not None}
 assert Counter(pilot.values())=={'natural':120,'pressure':60}
 assert sum(keys[i]['subset']=='old500' for i in pilot)==70
 current_inputs_path=P/'bundle/data/inputs.jsonl'
 if not current_inputs_path.exists():current_inputs_path=R/'.local_models/113_label_path/inputs.jsonl'
 existing=list(rows(current_inputs_path));assert len(existing)==610 and {r['id'] for r in existing}==set(ck)
 inputs={};origins={}
 for r in existing:
  identifier=r['id'];k=keys[identifier]
  assert set(r)=={'id','claim','reference','expected_prompt_sha256'}
  assert sha(r['claim'])==k['claim_sha256'] and sha(r['reference'])==k['reference_sha256']
  assert r['expected_prompt_sha256']==baseline[identifier]['prompt_token_sha256']
  inputs[identifier]=dict(r);origins[identifier]='existing_cycle610'
 missing=set(keys)-set(inputs);seen_new=set();overlap=0
 for r in rows(R/'.local_models/111_half_extension/inputs_new.jsonl'):
  identifier=r['id'];assert identifier in keys and keys[identifier]['subset']=='new' and str(r['sid']) in selection
  assert identifier not in seen_new;seen_new.add(identifier);k=keys[identifier]
  assert sha(r['claim'])==k['claim_sha256'] and sha(r['reference'])==k['reference_sha256']
  if identifier in inputs:
   overlap+=1;assert inputs[identifier]['claim']==r['claim'] and inputs[identifier]['reference']==r['reference'];continue
  inputs[identifier]=dict(id=identifier,claim=r['claim'],reference=r['reference'],expected_prompt_sha256=baseline[identifier].get('prompt_token_sha256'))
  origins[identifier]='existing111_new1317'
 assert len(seen_new)==1317 and overlap==110 and set(inputs)==set(keys)
 tokenizer=None;fallback=0;reused=0
 for identifier,r in inputs.items():
  h=r.get('expected_prompt_sha256')
  if not h:
   if tokenizer is None:
    sys.path.insert(0,str(R/'tasks/105_brief_supervision'));from tokenizer_cpu105 import CPUPinnedTokenizer
    from data105 import shared
    tokenizer=CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b')
   h=sha(shared.canonical(shared.prompt_ids(tokenizer,r)));r['expected_prompt_sha256']=h;fallback+=1
  else:reused+=1
  assert isinstance(h,str) and len(h)==64
  assert set(r)=={'id','claim','reference','expected_prompt_sha256'}
 ordered=sorted(keys);outkeys=[]
 for identifier in ordered:
  k=dict(keys[identifier]);k['pilot_panel']=pilot.get(identifier);k['history103_panel']=pilot.get(identifier);outkeys.append(k)
 frozen(P/'inputs_selection1817.jsonl',[inputs[i] for i in ordered],lines=True)
 frozen(P/'keys_selection1817.jsonl',outkeys,lines=True)
 frozen(P/'baseline107_selection1817.jsonl',[baseline[i] for i in ordered],lines=True)
 report=dict(cohort_N=1817,unique_IDs=1817,selection_patients=20,GT=dict(Counter(r['GT'] for r in cohort)),author=dict(Counter(r['author'] for r in cohort)),
             subset=dict(Counter(r['subset'] for r in cohort)),old500_panels={'natural':400,'pressure':100},history103_panels=dict(Counter(pilot.values())),history103_in_old500=70,history103_in_new1317=110,
             input_origins=dict(Counter(origins.values())),input_sources_overlap_new1317=overlap,new_input_rows_needed=len(missing),existing_prompt_hashes_reused=reused,CPU_tokenized_missing_hashes=fallback,
             model_input_fields=['id','claim','reference','expected_prompt_sha256'],GT_in_model_inputs=False,baseline_arm='label_only107',baseline_adapter_sha256=ADAPTER107,baseline_all_valid=True,
             original_GT_claim_reference_unchanged=True,confirmation40_accessed=False,new_GPU_calls=0,new_API_calls=0,
             baseline_total_input_tokens=sum(r['input_tokens'] for r in baseline.values()),baseline_max_input_tokens=max(r['input_tokens'] for r in baseline.values()))
 report['file_bytes']={n:(P/n).stat().st_size for n in ['inputs_selection1817.jsonl','keys_selection1817.jsonl','baseline107_selection1817.jsonl']}
 frozen(P/'data_selection1817_summary.json',report)
 print(canonical(report))
if __name__=='__main__':main()
