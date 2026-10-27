"""Offline final analysis of frozen103 data; no networking, models or new inference."""
import json,sys,hashlib,statistics,datetime
from collections import Counter
from pathlib import Path
import common103 as c
sys.path.insert(0,str(c.ROOT/'tasks/099_judge_selection'))
from analyze099 import metric,pair

def main():
 cohort=[r for r in c.lines(c.OUT/'cohort240.jsonl') if r['local180']];assert len(cohort)==180
 records=c.lines(c.OUT/'gpu_predictions_sanitized.jsonl');index={(r['model'],r['arm'],r['id']):r for r in records};assert len(index)==1080
 variants={'nine_native':('qwen3.5-9b','native_base'),'nine_direct':('qwen3.5-9b','label_base'),'nine_lora':('qwen3.5-9b','lora_label'),'moe_native_api':('qwen3.6-35b-a3b','native_api'),'moe_direct':('qwen3.6-35b-a3b','label_base'),'moe_lora':('qwen3.6-35b-a3b','lora_label')}
 comparisons=[('nine_direct','nine_lora'),('nine_native','nine_lora'),('moe_direct','moe_lora'),('moe_native_api','moe_lora'),('nine_lora','moe_lora')]
 patients=c.read(c.OUT/'patient_roles.json')['patients'];assert not set(patients['train'])&set(patients['selection']);assert not set(patients['confirmation'])&(set(patients['train'])|set(patients['selection']))
 training=c.lines(c.OUT/'train512_ids.jsonl');assert len(training)==512 and {r['sid'] for r in training}<=set(patients['train']);assert {r['sid'] for r in cohort}<=set(patients['selection'])
 assert Counter(r['GT'] for r in training)=={'Supported':320,'Not Supported':96,'Not Addressed':96}
 rows=[];transitions=[]
 for r in cohort:
  preds={'paper_r1':r['paper_r1']};arms={}
  for name,(model,arm) in variants.items():
   v=index[model,arm,r['id']];assert v['parsed']['verdict'] in c.LABELS and v['parsed']['finish_reason']=='stop';preds[name]=v['parsed']['verdict'];arms[name]=v['parsed']
  for model in ['qwen3.5-9b','qwen3.6-35b-a3b']:
   a=index[model,'label_base',r['id']];b=index[model,'lora_label',r['id']]
   assert a['prompt_sha256']==b['prompt_sha256'] and a['batch_ids']==b['batch_ids']
  row=dict(r,predictions=preds,arms=arms);rows.append(row)
  for base,new in comparisons:
   if preds[base]==preds[new]:continue
   transitions.append(dict(id=r['id'],sid=r['sid'],author=r['author'],panel=r['panel'],GT=r['GT'],base=base,candidate=new,before=preds[base],after=preds[new],rescue=preds[base]!=r['GT'] and preds[new]==r['GT'],harm=preds[base]==r['GT'] and preds[new]!=r['GT'],false_S_added=r['GT']!='Supported' and preds[base]!='Supported' and preds[new]=='Supported',false_S_prevented=r['GT']!='Supported' and preds[base]=='Supported' and preds[new]!='Supported'))
 result={'variants':{k:dict(model=m,arm=a) for k,(m,a) in variants.items()},'panels':{},'paired_comparison_roles':{'nine_lora__vs__nine_direct':'same local input/precision/batch training increment','moe_lora__vs__moe_direct':'same local input/precision/batch training increment','nine_lora__vs__nine_native':'local practical baseline, different thinking/format','moe_lora__vs__moe_native_api':'cross-interface reference, NOT pure training increment','moe_lora__vs__nine_lora':'post-training absolute development comparison'}}
 for name in ['natural','pressure']:
  rr=[r for r in rows if r['panel']==name];part=dict(N=len(rr),patients=len({r['sid'] for r in rr}),GT=dict(Counter(r['GT'] for r in rr)),metrics={},pairs={},by_author={})
  for key in ['paper_r1']+list(variants):part['metrics'][key]=metric(rr,key)
  for base,new in comparisons:
   p=pair(rr,base,new);p['by_GT']={g:dict(rescue=sum(x['rescue'] for x in transitions if x['panel']==name and x['base']==base and x['candidate']==new and x['GT']==g),harm=sum(x['harm'] for x in transitions if x['panel']==name and x['base']==base and x['candidate']==new and x['GT']==g)) for g in c.LABELS};part['pairs'][new+'__vs__'+base]=p
  for author in sorted({r['author'] for r in rr}):
   sub=[r for r in rr if r['author']==author];part['by_author'][author]=dict(N=len(sub),metrics={key:metric(sub,key) for key in ['paper_r1']+list(variants)},pairs={new+'__vs__'+base:pair(sub,base,new) for base,new in comparisons[:4]})
  result['panels'][name]=part
  print('Evaluated',name,flush=True)
 # Format and thoughts are observations, never repairs/replacements of successful answers.
 result['format_and_compute']={name:dict(N=180,strict_json_valid=sum(v['parsed'].get('strict_json_valid',v['parsed']['valid']) for v in values),exact_label_normalized=sum(v['parsed'].get('exact_label_normalized',False) for v in values),invalid=sum(not v['parsed']['valid'] for v in values),forced_thinking_boundary=sum(v.get('forced_thinking_boundary',False) for v in values),thinking_tokens=sum(v.get('thinking_tokens',0) for v in values),output_tokens=sum(v.get('output_tokens',0) for v in values),seconds=sum(v.get('seconds',0) for v in values)) for name,(m,a) in variants.items() if (values:=[index[m,a,r['id']] for r in cohort])}
 # Native bridge uses existing6 local speed replies only; no model calls or new target selection.
 private=c.PRIVATE/'gpu_final_evidence/results';local=c.lines(private/'qwen3.6-35b-a3b/eval/native_base_speed.jsonl');gt={r['id']:r['GT'] for r in cohort}
 result['moe_native_bridge6']=dict(N=len(local),disagree=sum(r['parsed']['verdict']!=index['qwen3.6-35b-a3b','native_api',r['id']]['parsed']['verdict'] for r in local),local_correct=sum(r['parsed']['verdict']==gt[r['id']] for r in local),API_correct=sum(index['qwen3.6-35b-a3b','native_api',r['id']]['parsed']['verdict']==gt[r['id']] for r in local),equivalence_not_established=True)
 result['bootstrap_scope']='1000 patient-cluster resamples by unified evaluator; fixed predictions on20 historically exposed selection patients; does not cover retraining, prior research exposure, model selection or new hospitals.'
 result['selfcheck']=dict(all180_complete=True,paired_inputs_and_batches_equal=True,patient_roles_disjoint=True,train512_GT_counts_unchanged=True,confirmation_new_evaluation=False,raw_source_sha256=c.sha(c.OUT/'gpu_predictions_sanitized.jsonl'),cohort_sha256=c.sha(c.OUT/'cohort240.jsonl'),independent_review=False)
 c.put(c.OUT/'final_analysis.json',result);c.putl(c.OUT/'final_transitions.jsonl',transitions);c.putl(c.OUT/'final_paired_predictions.jsonl',rows)
 for name,p in result['panels'].items():
  print(name)
  for key,v in p['metrics'].items():print(key,round(v['mcc'],4),round(v['percent_agreement'],4),v['correct'],str(v['false_S'])+'/'+str(v['true_non_S']))
if __name__=='__main__':main()
