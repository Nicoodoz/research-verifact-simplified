"""Replay zero-API matching, body equality and public/private boundaries without inference."""
from collections import Counter
import difflib,itertools,json
import numpy as np
import common102 as c,selector102 as s
from preflight102 import make_body
def main():
 freeze=c.read(c.OUT/'construction_freeze.json');checks=0
 def check(ok,why):
  nonlocal checks
  assert ok,why;checks+=1
 for rel,h in freeze['files'].items():check(c.sha(c.ROOT/rel)==h,rel)
 teachers=c.lines(c.PRIVATE/'teachers.jsonl');targets=c.lines(c.PRIVATE/'targets.jsonl');jobs=c.lines(c.PRIVATE/'jobs.jsonl');selection=c.lines(c.OUT/'selections.jsonl')
 source=c.lines(c.ROOT/'outputs/073_clinical_example_matching/example_pool.jsonl');old={r['proposition_id']:r for r in source}
 original={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')};cohort=c.lines(c.OUT/'cohort.jsonl')
 ti={r['id']:i for i,r in enumerate(teachers)};targetmap={r['id']:r for r in targets};choosemap={r['id']:r for r in selection}
 for t in teachers:
  e=old[t['id']];ann=e['annotation'];check(t['label']==original[t['id']]['GT'] and [ann[f'verdict{i}'] for i in [1,2,3]]==[t['label']]*3,'original unanimous labels')
  check(t['claim']==e['claim'] and t['reference']==e['reference'] and e['selection']=='full_final_reference','no synthetic or cropped teacher')
 check(not {r['sid'] for r in teachers}&{r['sid'] for r in targets},'patient separation')
 check(Counter(r['panel'] for r in targets)=={'natural':400,'pressure':100},'full500')
 for r in cohort:check(r['GT']==original[r['id']]['GT'] and r['sid']==str(original[r['id']]['sid']),'target identity')
 selector=s.Selector(teachers);template={k:v for k,v in jobs[0]['body'].items() if k!='messages'}
 for j in jobs:
  t=targetmap[j['id']];ix=[] if j['arm']=='verifact_ref' else [ti[pid] for pid in choosemap[j['id']][j['arm']]]
  check(j['body']==make_body(template,t,teachers,ix),'only real examples and target passed to Judge')
  check(j['body_sha256']==c.digest(c.canonical(j['body'])),'request bytes')
  check({k:v for k,v in j['body'].items() if k!='messages'}==template,'same model generation settings')
  if ix:check([teachers[i]['label'] for i in ix]==list(c.LABELS) and len({teachers[i]['sid'] for i in ix})==3,'identical quota and patient diversity')
 for r in c.lines(c.OUT/'target_features.jsonl'):
  t=targetmap[r['id']];features,audit=s.relation_features(t['claim'],t['reference']);check(audit=={k:v for k,v in r.items() if k!='id'},'feature exact replay')
  for w in r['windows']:check(c.digest(t['reference'][w['start']:w['end']])==w['sha256'],'raw window origin')
  for key in features:check(not any(z in key.lower() for z in ['supported','contradiction','verdict','ground_truth']),'no inferred outcome labels in features')
  topic,_,_=selector.scores(t['claim'],t['reference']);topic2,_,_=selector.scores(t['claim'],'');check(np.array_equal(topic,topic2),'topic actually claim only')
 # Strict fingerprint dedup across IDs confirms no missing free reuse.
 unique={(j['repeat'],j['body_sha256']):j for j in jobs};budget=c.read(c.OUT/'budget_plan.json')
 check(len(jobs)==1572 and len(unique)==1556,'full and deduplicated calls')
 prudent=sum((j['input_token_forecast']*1.5+j['output_token_forecast']*1.25*4.5)/1e6 for j in unique.values())+2
 check(abs(prudent-budget['required_idle_budget_cny'])<1e-8,'cost recomputation')
 check(not (c.PRIVATE/'attempts').exists() and not (c.PRIVATE/'budget.sqlite').exists(),'zero paid execution')
 audits=sorted(targets,key=lambda r:c.digest('102/sourceaudit/v1/'+r['id']))[:12]
 c.putl(c.PRIVATE/'source_audit_queue.jsonl',[dict(t,selection=choosemap[t['id']],features=s.relation_features(t['claim'],t['reference'])[1]) for t in audits])
 check(all(set(t)=={'id','sid','panel','claim','reference'} for t in targets),'selection input whitelist no targetGT')
 c.put(c.OUT/'selfcheck.json',dict(utc=c.utc(),status='PASS',checks=checks,independent_audit=False,paid_calls=0,source_authenticity=True,patient_isolation=True,full500_retained=True,three_class_quotas_identical=True,request_payload_replayed=True,reference_dependency_replayed=True,budget_recomputed=True,classification_executed=False))
 print(c.canonical(c.read(c.OUT/'selfcheck.json')))
if __name__=='__main__':main()
