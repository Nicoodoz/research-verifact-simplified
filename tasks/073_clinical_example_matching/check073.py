"""Offline invariants and transport/accounting edge cases; no API."""
import sys,json,collections
from pathlib import Path
from materials073 import ROOT,OUT,read,lines,sha,put
import run073 as r
from prepare073 import tokens,clean
def main():
 f=r.check_frozen('pilot');checks=[]
 def ck(name,value):
  assert value,name
  checks.append(name)
 oldids={x['id'] for x in lines(ROOT/'outputs/072_adaptive_judge_examples/target_blind.jsonl')}
 target={x['id']:x for x in lines(OUT/'target_blind.jsonl')};pool={x['proposition_id']:x for x in lines(OUT/'example_pool.jsonl')}
 ck('new96_ids',len(target)==96 and not oldids&target.keys())
 ck('patient_split',not set(f['teaching_patients'])&set(f['pilot_patients']+f['confirmation_patients']))
 jobs=lines(OUT/'all_arm_jobs.jsonl');sels={(x['id'],x['arm']):x for x in lines(OUT/'selections.jsonl')}
 for j in jobs:
  ck('body_digest:'+j['request_id'],j['body_sha256']==r.digest(j['body']))
  ck('target_reference:'+j['request_id'],json.loads(j['body']['messages'][-1]['content'])==dict(proposition=target[j['id']]['claim'],reference=target[j['id']]['reference']))
  ex=sels[j['id'],j['arm']]['example_ids']
  ck('example_roles:'+j['request_id'],not ex or ([pool[k]['physician_label'] for k in ex]==['Supported','Not Supported','Supported','Not Addressed'] and len({pool[k]['sid'] for k in ex})==4))
  ck('model_settings:'+j['request_id'],j['body']['model']==r.MODEL and j['body']['enable_thinking'] and j['body']['reasoning_effort']=='high')
 unique=r.jobs_for('pilot');aliases=lines(OUT/'pilot_aliases.jsonl')
 ck('dedup_exact_bodies',len(unique)==len({j['body_sha256'] for j in aliases}) and {j['request_id'] for j in aliases}=={j['request_id'] for j in unique})
 ck('keep_clinical_tokens',set('no not before after 45 mm hg 2.5 mg stopped planned'.split())<=set(tokens('patient no not before after 45 mm Hg 2.5 mg stopped planned')))
 ck('remove_generic_tokens',not set(tokens('the patient pt patients was')))
 ck('unknown_reserved',r.charge(None,.2)==.2 and r.charge({'http_status':0},.2)==.2)
 ck('usage_cost',abs(r.charge({'http_status':200,'body_text':json.dumps({'usage':{'prompt_tokens':1000,'completion_tokens':2000}})},.2)-.021)<1e-12)
 ck('ordinary_faults_retry', {0,429,500,502,503,504}<=r.RETRYABLE and r.MAX_ATTEMPTS==3)
 ck('budget',r.CAP==20 and all(r.bound(j['body'])<.25 for j in unique))
 diag={}
 for arm in ['D4','L4','M4']:
  ss=[s for s in sels.values() if s['arm']==arm]
  diag[arm]={'distinct_sets':len({tuple(s['example_ids']) for s in ss}),'identical_F4_bodies':sum(s['body_sha256']==sels[s['id'],'F4']['body_sha256'] for s in ss),'zero_or_fallback_slots':sum(z.get('zero_overlap',z.get('fallback_low_similarity',False)) for s in ss for z in s['diagnostics'])}
 result=dict(status='PASS',n=len(checks),checks=checks,selection_diagnostics=diag)
 put(OUT/'preflight_checks.json',result)
 print(json.dumps(dict(status='PASS',n=len(checks),selection_diagnostics=diag),ensure_ascii=False))
if __name__=='__main__':main()
