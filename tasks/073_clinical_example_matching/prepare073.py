"""Freeze two deployable claim-only selectors, controls and patient-disjoint stages."""
import copy,csv,difflib,json,hashlib,re,sys
from collections import Counter
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from materials073 import ROOT,OUT,read,lines,sha,put,jl,digest
sys.path.insert(0,str(ROOT/'tasks/072_adaptive_judge_examples'))
import prepare072 as old
KEEP=list(range(1,13))+[13,14,16,17,19,20,23,28,29,30,32,33,36]
STOP=set('a an the patient patients pt pts he she his her him their they was were is are be been being of and or to for with in on at by as it its this that these those mr mrs ms s'.split())
def tokens(text):
 text=re.sub(r'\[\*\*.*?\*\*\]',' ',text.lower())
 return [t for t in re.findall(r'\d+(?:\.\d+)?|[a-z]+',text) if t not in STOP]
def clean(text):return ' '.join(tokens(text))
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def bodyhash(x):return digest(canonical(x))
PREFIX='\n\n## Clinician-labeled examples from four other patients\nEach example contains a proposition, EHR reference, and physician label. Examples are not evidence about the patient in the actual task. For the actual task use only its supplied reference.\n'
def make_body(base,pool,chosen):
 b=copy.deepcopy(base)
 if chosen:b['messages'][0]['content']+=PREFIX+'\n'.join(canonical(dict(proposition=pool[k]['claim'],reference=pool[k]['reference'],physician_label=pool[k]['physician_label'])) for k in chosen)+'\n'
 return b
def select(t,pool,scores):
 chosen=[];used=set();log=[]
 for label in ['Supported','Not Supported','Supported','Not Addressed']:
  cand=[i for i,x in enumerate(pool) if x['physician_label']==label and x['sid'] not in used and difflib.SequenceMatcher(None,clean(x['claim']),clean(t['claim'])).ratio()<.85]
  assert cand
  # Old fixed exemplars win zero-score ties; deterministic, never target label based.
  i=sorted(cand,key=lambda k:(-float(scores[k]),k))[0]
  chosen.append(i);used.add(pool[i]['sid']);log.append(dict(example_id=pool[i]['proposition_id'],score=float(scores[i]),zero_overlap=float(scores[i])<=1e-12,shared_tokens=sorted(set(tokens(t['claim']))&set(tokens(pool[i]['claim'])))))
 return chosen,log
def main():
 assert not (OUT/'freeze.json').exists()
 candidates=lines(OUT/'pool_candidates.jsonl');pool=[candidates[i-1] for i in KEEP]
 targets=lines(OUT/'target_blind.jsonl');f=read(ROOT/'outputs/072_adaptive_judge_examples/freeze.json')
 train=set(f['teaching_patients']);assert not train&{x['sid'] for x in targets}
 ann={x['proposition_id']:x for x in csv.DictReader((ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv').open(encoding='utf-8-sig'))}
 for x in pool:
  a=ann[x['proposition_id']];assert x['sid'] in train and a['initial_agreement']=='3' and a['invalid']=='False'
  assert [a[k] for k in ('verdict1','verdict2','verdict3')]==[x['physician_label']]*3
 assert not set().union(*(old.note_ids(x['reference']) for x in pool))&set().union(*(old.note_ids(x['reference']) for x in targets))
 # Fit lexical IDF only on teaching-patient claims, without their labels or references.
 corpus=[]
 for rel in ['outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl','outputs/019_support_boundary_screen/selection/preparation/inputs.jsonl','outputs/020_lambda2_patient_validation/new10/base_preparation_001/inputs.jsonl']:
  corpus += [clean(x['text']) for x in lines(ROOT/rel) if str(x['subject_id']) in train]
 corpus=sorted(set(corpus+[clean(x['claim']) for x in pool]))
 word=TfidfVectorizer(ngram_range=(1,2),token_pattern=r'(?u)\b\w+\b').fit(corpus)
 char=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5)).fit(corpus)
 wp=word.transform([clean(x['claim']) for x in pool]);cp=char.transform([clean(x['claim']) for x in pool])
 vectors=np.load(OUT/'claim_vectors.npy',allow_pickle=False);keys=read(OUT/'vector_ids.json');vm={k:v/np.linalg.norm(v) for k,v in zip(keys,vectors)}
 mp=np.array([vm[digest(x['claim'])] for x in pool])
 oldpool=candidates[:12];ov=TfidfVectorizer(ngram_range=(1,2),stop_words='english',token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z0-9]+\b');om=ov.fit_transform([x['claim'] for x in oldpool])
 template=next(j['body'] for j in lines(ROOT/'outputs/053_thinking_prior_validation/main_jobs.jsonl') if j['condition']=='T-S')
 jobs=[];selections=[]
 for t in targets:
  stage='pilot' if t['sid'] in f['pilot_patients'] else 'confirmation'
  b=copy.deepcopy(template);b['messages'][-1]['content']=canonical(dict(proposition=t['claim'],reference=t['reference']))
  lex=(.7*(word.transform([clean(t['claim'])])@wp.T).toarray()[0]+.3*(char.transform([clean(t['claim'])])@cp.T).toarray()[0])
  sem=mp@vm[digest(t['claim'])]
  l,ll=select(t,pool,lex);m,ml=select(t,pool,sem)
  dlog=old.select_dynamic(t,oldpool,om,ov,None);di=[next(i for i,x in enumerate(pool) if x['proposition_id']==z['proposition_id']) for z in dlog]
  for arm,sel,log in [('B',[],[]),('F4',[0,1,2,3],[]),('D4',di,dlog),('L4',l,ll),('M4',m,ml)]:
   body=make_body(b,pool,sel);h=bodyhash(body)
   jobs.append(dict(request_id='073_'+stage+'_'+h[:24],stage=stage,id=t['id'],sid=t['sid'],arm=arm,body=body,body_sha256=h))
   selections.append(dict(id=t['id'],sid=t['sid'],stage=stage,arm=arm,example_ids=[pool[i]['proposition_id'] for i in sel],diagnostics=log,body_sha256=h))
 jl(OUT/'example_pool.jsonl',pool);jl(OUT/'all_arm_jobs.jsonl',jobs);jl(OUT/'selections.jsonl',selections)
 pilot=[j for j in jobs if j['stage']=='pilot'];jl(OUT/'pilot_aliases.jsonl',pilot)
 unique={j['request_id']:j for j in pilot};actual=sorted(unique.values(),key=lambda j:digest('073/order:'+j['request_id']));jl(OUT/'pilot_jobs.jsonl',actual)
 fallback={x['proposition_id']:x['U2'] for x in csv.DictReader((ROOT/'outputs/034_same_data_comparison/predictions_common.csv').open(encoding='utf-8-sig'))}
 assert all(t['id'] in fallback for t in targets);put(OUT/'fallback_u2.json',{t['id']:fallback[t['id']] for t in targets})
 summary=dict(pool_n=len(pool),pool_labels=dict(Counter(x['physician_label'] for x in pool)),pilot_logical=len(pilot),pilot_unique=len(actual),corpus_size=len(corpus),kept_special_tokens=tokens('patient no not before after 45 mm Hg 2.5 mg stopped planned'))
 put(OUT/'offline_checks.json',summary)
 artifacts=['example_pool.jsonl','target_blind.jsonl','target_gt.jsonl','claim_vectors.npy','vector_ids.json','vector_sources.json','all_arm_jobs.jsonl','selections.jsonl','pilot_aliases.jsonl','pilot_jobs.jsonl','fallback_u2.json','offline_checks.json','pool_review_decision.json']
 sources=['tasks/073_clinical_example_matching/'+n for n in ['prepare073.py','run073.py','analyze073.py','README.md']]+['outputs/053_thinking_prior_validation/freeze.json','outputs/053_thinking_prior_validation/main_jobs.jsonl','outputs/072_adaptive_judge_examples/example_pool.jsonl','outputs/002_reproduce_paper_results/run_003/cohort_master.csv','outputs/034_same_data_comparison/predictions_common.csv']
 put(OUT/'freeze.json',dict(status='FROZEN_BEFORE_073_API',cap_cny=20.,model=template['model'],pilot_patients=f['pilot_patients'],confirmation_patients=f['confirmation_patients'],teaching_patients=f['teaching_patients'],pilot_n=36,confirmation_n=60,created_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),source_sha256={p:sha(ROOT/p) for p in sources},artifact_sha256={n:sha(OUT/n) for n in artifacts}))
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
