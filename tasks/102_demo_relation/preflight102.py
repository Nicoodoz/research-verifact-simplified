"""Zero-paid-API construction, identity checks, exact input lengths and full-task budget."""
from collections import Counter,defaultdict
from pathlib import Path
import copy,csv,difflib,itertools,json,os,statistics,subprocess,sys
import numpy as np
import common102 as c
import selector102 as s
sys.path.insert(0,str(c.ROOT/'tasks/097_native_judge_source_dependence'))
from prepare_a import original_style_prompt,SYSTEM
from verifact_research.inference.aliyun import load_config

HEADER='''## Historical annotated examples:
The following are fixed examples from other patients. Their verdicts are historical physician annotations. Use them only as examples of the same three-class task; they are not evidence about the current patient. Classify only the current Input JSON below.
'''
class Tokens:
 def __init__(self):
  self.process=subprocess.Popen([str(c.ROOT/'.local_models/085a_tokenizer_venv/Scripts/python.exe'),str(c.ROOT/'tasks/100_preregistered_followup/token_count_worker100.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1,env=dict(os.environ,TOKENIZERS_PARALLELISM='false'))
  self.cache={}
 def counts(self,texts):
  keys=[c.digest(t) for t in texts];missing={k:t for k,t in zip(keys,texts) if k not in self.cache}
  items=list(missing.items())
  for lo in range(0,len(items),16):
   batch=items[lo:lo+16];self.process.stdin.write(json.dumps(dict(texts=[t for k,t in batch]),ensure_ascii=False)+'\n');self.process.stdin.flush()
   result=json.loads(self.process.stdout.readline());assert len(result)==len(batch);self.cache.update((k,v) for (k,t),v in zip(batch,result))
  return [self.cache[k] for k in keys]
 def count(self,text):return self.counts([text])[0]
 def close(self):self.process.stdin.close();self.process.wait(timeout=30);assert self.process.returncode==0
def source_match(example,source):
 pid=example['proposition_id'];matching=[r for r in source if r.get('proposition_id',r.get('id'))==pid];assert len(matching)==1,(pid,len(matching))
 r=matching[0];claim=r.get('claim',r.get('text'));ref=r.get('reference',r.get('base'));sid=str(r.get('sid',r.get('subject_id')))
 if isinstance(ref,dict):ref=ref.get('reference')
 assert claim==example['claim'] and ref==example['reference'] and sid==str(example['sid']),('source mismatch',pid)
 return dict(source_file=example['source_file'],source_file_sha256=c.sha(c.ROOT/example['source_file']),source_reference_sha256=c.digest(ref))
def make_body(template,target,teachers,chosen):
 prompt=original_style_prompt(target['claim'],target['reference'])
 if chosen:
  block=HEADER+''.join(c.canonical(dict(text=teachers[i]['claim'],reference=teachers[i]['reference'],verdict=teachers[i]['label']))+'\n' for i in chosen)+'\n'
  prompt=prompt.replace('## Input JSON:\n',block+'## Input JSON:\n')
 b=copy.deepcopy(template);b['messages']=[dict(role='system',content=SYSTEM),dict(role='user',content=prompt)];return b
def job(target,arm,body,repeat=False):
 h=c.digest(c.canonical(body));rid=c.digest(c.canonical(['102/v1',target['id'],repeat,h]))[:28]
 return dict(id=target['id'],sid=target['sid'],panel=target['panel'],arm=arm,repeat=repeat,body=body,body_sha256=h,request_id=rid)

def main():
 assert not (c.OUT/'preflight.json').exists(),'Single construction, no posthoc method revisions'
 c.PRIVATE.mkdir(parents=True,exist_ok=True)
 cfg=load_config(c.ROOT/'.env.aliyun');assert cfg.base_url.rstrip('/')=='https://maas.qianwenaiapi.com/compatible-mode/v1' and cfg.model=='deepseek-v4-flash-0731'
 raw=c.lines(c.ROOT/'.local_models/098_p90_native_confirmation/sample.jsonl');public098=c.lines(c.ROOT/'outputs/098_p90_native_confirmation/cohort.jsonl');pub={r['id']:r for r in public098}
 targets=[dict(id=r['id'],sid=str(r['sid']),panel=r['panel'],claim=r['claim'],reference=r['published_reference']) for r in raw]
 assert len(targets)==len({r['id'] for r in targets})==500
 target_patients={r['sid'] for r in targets};assert len(target_patients)==40
 for r in targets:assert c.digest(r['claim'])==pub[r['id']]['claim_sha256'] and c.digest(r['reference'])==pub[r['id']]['published_reference_id']
 original={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')}
 old=c.lines(c.ROOT/'outputs/073_clinical_example_matching/example_pool.jsonl');teachers=[];audit=[];sources={}
 for e in old:
  if e['selection']!='full_final_reference':continue
  pid=e['proposition_id'];o=original[pid];sid=str(e['sid']);assert sid not in target_patients and sid==str(o['sid']) and e['physician_label']==o['GT']
  ann=e['annotation'];assert ann['initial_agreement']=='3' and ann['second_round_anomaly']=='False' and ann['time_metadata_conflict']=='False'
  source=e['source_file']
  if source not in sources:sources[source]=c.lines(c.ROOT/source)
  verification=source_match(e,sources[source]);rh=c.digest(e['reference'])
  if e.get('full_final_reference_sha256'):assert e['full_final_reference_sha256']==rh
  teachers.append(dict(id=pid,sid=sid,label=e['physician_label'],claim=e['claim'],reference=e['reference']))
  audit.append(dict(id=pid,sid=sid,label=e['physician_label'],claim_sha256=c.digest(e['claim']),reference_sha256=rh,reference_chars=len(e['reference']),full_existing_reference=True,**verification))
 assert Counter(r['label'] for r in teachers)=={'Supported':10,'Not Supported':5,'Not Addressed':8}
 teachers.sort(key=lambda r:(c.LABELS.index(r['label']),r['id']))
 selector=s.Selector(teachers);combos=list(itertools.product(*[[i for i,t in enumerate(teachers) if t['label']==label] for label in c.LABELS]));combos=[ix for ix in combos if len({teachers[i]['sid'] for i in ix})==3]
 tok=Tokens()
 try:
  serialize=lambda ix:HEADER+''.join(c.canonical(dict(text=teachers[i]['claim'],reference=teachers[i]['reference'],verdict=teachers[i]['label']))+'\n' for i in ix)+'\n'
  combo_tokens=tok.counts([serialize(ix) for ix in combos]);median=float(statistics.median(combo_tokens));band=[ix for ix,n in zip(combos,combo_tokens) if median*.98<=n<=median*1.02]
  assert band,'No common length-matched candidate triples'
  example_token={tuple(ix):n for ix,n in zip(combos,combo_tokens)}
  template=c.read(c.ROOT/'.local_models/101_nsna_review/template.json');assert template['model']=='deepseek-v4-flash-0731' and template['max_tokens']==8192
  selections=[];jobs=[];feature_records=[];counterfactual=[]
  repeat_ids={r['id'] for r in sorted([r for r in targets if r['panel']=='natural'],key=lambda r:c.digest('102/repeat/v1/'+r['id']))[:24]}
  for k,t in enumerate(targets):
   eligible=[ix for ix in band if all(difflib.SequenceMatcher(None,s.topic_text(t['claim']),s.topic_text(teachers[i]['claim'])).ratio()<.85 for i in ix)]
   assert eligible,('No matched nonduplicate triples',t['id'])
   topic,relation,features=selector.scores(t['claim'],t['reference']);_,claim_only,_=selector.scores(t['claim'],t['reference'],claim_only=True)
   it=s.choose(topic,eligible,teachers);ir=s.choose(relation,eligible,teachers);ic=s.choose(claim_only,eligible,teachers)
   selections.append(dict(id=t['id'],sid=t['sid'],panel=t['panel'],demo_topic=[teachers[i]['id'] for i in it],demo_relation=[teachers[i]['id'] for i in ir],topic_demo_tokens=example_token[it],relation_demo_tokens=example_token[ir],eligible_triples=len(eligible),same_examples=it==ir,replaced_slots=sum(x!=y for x,y in zip(it,ir)),relation_changed_without_reference=ir!=ic,claim_only_examples=[teachers[i]['id'] for i in ic]))
   feature_records.append(dict(id=t['id'],**features))
   for arm,ix in [('verifact_ref',()),('demo_topic',it),('demo_relation',ir)]:
    body=make_body(template,t,teachers,ix);jobs.append(job(t,arm,body))
    if t['id'] in repeat_ids:jobs.append(job(t,arm,body,True))
   if (k+1)%100==0:print(c.canonical(dict(zero_API_targets_constructed=k+1,total=500)),flush=True)
  bodies={j['body_sha256']:j['body'] for j in jobs};body_tokens={}
  keys=list(bodies);contents=[m['content'] for h in keys for m in bodies[h]['messages']];counts=tok.counts(contents)
  for i,h in enumerate(keys):body_tokens[h]=sum(counts[i*2:i*2+2])+128
  for j in jobs:j['input_token_forecast']=body_tokens[j['body_sha256']]
  # Historical usage only, no target correctness/predictions used for design or selection.
  hist=c.lines(c.ROOT/'outputs/098_p90_native_confirmation/usage.jsonl');histmeans={}
  for panel in ['natural','pressure']:
   pp=[u for u in hist if not u['repeat'] and u['panel']==panel]
   baseline=statistics.mean(u['completion_tokens'] for u in pp if u['arm']=='O')
   demo=max(statistics.mean(u['completion_tokens'] for u in pp if u['arm']==arm) for arm in ['P','Q','F'] if any(u['arm']==arm for u in pp))
   histmeans[panel]=dict(verifact_ref=baseline,demo_topic=demo,demo_relation=demo)
  for j in jobs:j['output_token_forecast']=histmeans[j['panel']][j['arm']]
  first={(j['id'],j['arm']):j for j in jobs if not j['repeat']};gaps=[abs(first[r['id'],'demo_topic']['input_token_forecast']-first[r['id'],'demo_relation']['input_token_forecast'])/min(first[r['id'],'demo_topic']['input_token_forecast'],first[r['id'],'demo_relation']['input_token_forecast']) for r in targets]
  unique={j['request_id']:j for j in jobs}
  mean_cost=lambda jj:sum((j['input_token_forecast']*1.5+j['output_token_forecast']*4.5)/1e6 for j in jj)
  prudent_cost=lambda jj:sum((j['input_token_forecast']*1.5+j['output_token_forecast']*1.25*4.5)/1e6 for j in jj)
  fees=dict(logical_calls=len(jobs),unique_physical_calls=len(unique),same_body_calls_saved=len(jobs)-len(unique),idle_mean_no_cache_cny=mean_cost(unique.values()),idle_prudent_no_cache_cny=prudent_cost(unique.values()),recovery_reserve_cny=2.,required_idle_budget_cny=prudent_cost(unique.values())+2,busy_prudent_plus_reserve_cny=2*prudent_cost(unique.values())+2,hard_cap_cny=35,shortfall_cny=max(0,prudent_cost(unique.values())+2-35),no_cache_hits_assumed=True,historical_output_means=histmeans,mean_input_by_arm={arm:statistics.mean(j['input_token_forecast'] for j in jobs if not j['repeat'] and j['arm']==arm) for arm in c.ARMS},full500_not_reduced=True)
  synthetic_claim='The patient received the medication after surgery.'
  synth1=s.relation_features(synthetic_claim,'The patient received the medication after surgery.')[0];synth2=s.relation_features(synthetic_claim,'The medication was planned before surgery but was not administered.')[0]
  gates=dict(source_identity=True,patient_isolation=not target_patients&{t['sid'] for t in teachers},three_classes_min3=min(Counter(t['label'] for t in teachers).values())>=3,selection_difference=sum(not r['same_examples'] for r in selections)>=250,reference_ablation_changes=sum(r['relation_changed_without_reference'] for r in selections)>=125,window_coverage=sum(r['reference_used'] for r in feature_records)>=400,length_matching=max(gaps)<=.05,enough_feasible_triples=sum(r['eligible_triples']>=3 for r in selections)>=400,synthetic_reference_sensitivity=synth1!=synth2,budget=fees['required_idle_budget_cny']<=35)
  result=dict(utc=c.utc(),paid_calls=0,checks=gates,construction_pass=all(v for k,v in gates.items() if k!='budget'),paid_execution_allowed=all(gates.values()),teachers=len(teachers),teacher_patients=len({r['sid'] for r in teachers}),teacher_labels=dict(Counter(r['label'] for r in teachers)),target_patients=40,target_natural=400,target_pressure=100,triples_before_length=len(combos),common_length_band=len(band),median_demo_tokens=median,same_example_inputs=sum(r['same_examples'] for r in selections),changed_examples=sum(not r['same_examples'] for r in selections),replaced_slot_distribution=dict(Counter(r['replaced_slots'] for r in selections)),reference_ablation_changed=sum(r['relation_changed_without_reference'] for r in selections),windows_available=sum(r['reference_used'] for r in feature_records),max_relative_input_gap=max(gaps),mean_relative_input_gap=statistics.mean(gaps),budget=fees,current_endpoint=cfg.base_url,current_model=cfg.model,no_confirm_predictions_or_errors_loaded=True)
  c.putl(c.PRIVATE/'teachers.jsonl',teachers);c.putl(c.PRIVATE/'targets.jsonl',targets);c.putl(c.PRIVATE/'jobs.jsonl',jobs)
  c.putl(c.OUT/'teaching_provenance.jsonl',audit);c.putl(c.OUT/'selections.jsonl',selections);c.putl(c.OUT/'target_features.jsonl',feature_records)
  c.putl(c.OUT/'teacher_features.jsonl',[dict(id=t['id'],**z) for t,z in zip(teachers,selector.audit)])
  c.put(c.OUT/'budget_plan.json',fees);c.put(c.OUT/'preflight.json',result)
  # Only now attach the frozen targets' original GT for evaluation; selectors have no GT inputs.
  c.putl(c.OUT/'cohort.jsonl',[dict(id=t['id'],sid=t['sid'],panel=t['panel'],author=pub[t['id']]['author'],GT=pub[t['id']]['GT'],paper_r1=pub[t['id']]['Original'],claim_sha256=c.digest(t['claim']),reference_sha256=c.digest(t['reference']),repeat_subset=t['id'] in repeat_ids) for t in targets])
  files=[c.TASK/x for x in ['protocol.md','selector102.py','preflight102.py','common102.py']]+[c.PRIVATE/x for x in ['teachers.jsonl','targets.jsonl','jobs.jsonl']]+[c.OUT/x for x in ['cohort.jsonl','selections.jsonl','budget_plan.json','preflight.json','teaching_provenance.jsonl','target_features.jsonl','teacher_features.jsonl']]
  c.put(c.OUT/'construction_freeze.json',dict(utc=c.utc(),start_main='b05ebba61246e8bd5d1da0dab63ee10be2120752',files={x.relative_to(c.ROOT).as_posix():c.sha(x) for x in files},tokenizer_sha256=c.sha(c.ROOT/'.local_models/100_preregistered_followup/sources/tokenizer.json'),teacher_patients=sorted({r['sid'] for r in teachers}),evaluation_patients=sorted(target_patients),all_patients_historically_exposed=True,prepaid_gate_passed=all(gates.values()),paid_calls=0))
  print(c.canonical(result),flush=True)
 finally:tok.close()
if __name__=='__main__':main()
