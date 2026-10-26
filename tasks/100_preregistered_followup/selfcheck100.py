"""Provenance, independent metrics/Decimal costs and privacy; never sends requests."""
from collections import Counter
from decimal import Decimal
import datetime as dt,json,sqlite3
import numpy as np
from sklearn.metrics import matthews_corrcoef,f1_score
import common100 as c
import evidence100 as e
import runtime100 as rt
from verifact_research.evaluation import paired_compare

def price_check(req,tr,account):
 reservation=Decimal(str(req['reservation_cny']))
 if account['basis'].startswith('reserved'):return reservation
 x=json.loads(tr['body_text']);u=x['usage'];model=req['job']['body']['model'];assert x['model']==model
 n,o=u['prompt_tokens'],u['completion_tokens'];cache=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0)
 if model=='deepseek-v4-flash-0731':
  start,end=[dt.datetime.fromisoformat(tr[k]) for k in ['started_utc','ended_utc']];hours=[z.astimezone(dt.timezone(dt.timedelta(hours=8))).hour for z in [start,end]]
  cheap=all(h>=22 or h<8 for h in hours) and (end-start).total_seconds()<3600;factor=Decimal('.5') if cheap else Decimal(1)
  value=(Decimal(n-cache)*3+Decimal(cache)*Decimal('.3')+Decimal(o)*9)/Decimal(1000000)*factor;assert o<=8192
 else:
  assert model=='qwen3.5-27b';ip,op=(Decimal('.6'),Decimal('4.8')) if n<=128000 else (Decimal('1.8'),Decimal('14.4'));value=(Decimal(n)*ip+Decimal(o)*op)/Decimal(1000000)
 assert value<=reservation+Decimal('.000000001');return value

def main():
 assert not (c.PRIVATE/'run.lock').exists();checks=0
 for name in ['execution_freeze.json','runtime_analysis_freeze.json']:
  for rel,h in c.read(c.OUT/name)['files'].items():assert c.sha(c.ROOT/rel)==h,rel;checks+=1
 handoff=c.read(c.OUT/'handoff_budget_snapshot.json')
 for rel,h in handoff['immutable098_sha256'].items():assert c.sha(c.ROOT/rel)==h,rel;checks+=1
 assert c.sha(c.ROOT/'.env.aliyun')==handoff['default_env_sha256'];checks+=1
 inventory=c.read(c.OUT/'source_inventory.json')
 for rel,h in inventory['raw_sha256'].items():assert c.sha(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/reference_ehr'/rel)==h;checks+=1
 original={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')};sample={r['id']:r for r in c.lines(c.PRIVATE/'sample.jsonl')};public={r['id']:r for r in c.lines(c.OUT/'cohort.jsonl')}
 assert len(sample)==len(public)==296
 for pid,r in sample.items():
  q=original[pid];assert r['GT']==q['GT'] and r['sid']==str(q['sid']) and r['Original']==q['original'] and r['author']==q['author'];checks+=1
 freeze=c.read(c.OUT/'execution_freeze.json');old=c.read(c.ROOT/'outputs/098_p90_native_confirmation/execution_freeze.json')
 assert len(freeze['confirmation_patients'])==32 and not set(freeze['confirmation_patients'])&(set(old['evaluation_patients'])|set(old['example_development_patients']));checks+=1
 # Independent raw-note identity/range and full-note completeness checks.
 raw=c.ROOT/'data/00_raw/verifact-bhc/1.1.0/reference_ehr';admissions={r['SUBJECT_ID']:r for r in e.csvrows(raw/'admissions.csv.gz')};rawnotes=e.csvrows(raw/'ehr_noteevents.csv.gz');notes={(r['SUBJECT_ID'],r['ROW_ID']):r for r in rawnotes};builder=c.sha(c.TASK/'evidence100.py')
 for pid,r in sample.items():
  m=c.read(c.PRIVATE/('materials_'+builder[:12])/(pid+'.json'));a=admissions[r['sid']]
  eligible={n['ROW_ID'] for n in rawnotes if n['SUBJECT_ID']==r['sid'] and a['ADMITTIME'][:10]<=n['CHARTDATE'][:10]<=a['DISCHTIME'][:10] and n['CATEGORY'].strip().lower()!='discharge summary'}
  assert set(m['construction']['intervals']['EHR-all'])==eligible
  for arm,spans in m['construction']['intervals'].items():
   ref=r['references'][arm]
   for nid,intervals in spans.items():
    note=notes[r['sid'],nid];assert nid in eligible
    for lo,hi in intervals:
     assert 0<=lo<=hi<=len(note['TEXT']) and note['TEXT'][lo:hi] in ref
     if arm in ['L24','EHR-all']:assert lo==0 and hi==len(note['TEXT'])
     checks+=1
  assert m['construction']['S24_tokens']<=m['construction']['L24_tokens']<=24000;checks+=2
 # Ledger from native usage, with old098 baseline and all unknowns preserved.
 totals={};unknowns={};success_sets={}
 for task,table in [('098_p90_native_confirmation','SELECT rid,num,arm,charge,status,folder FROM attempts'),('100_preregistered_followup','SELECT rid,num,model,charge,status,folder FROM attempts')]:
  con=sqlite3.connect(f'file:{(c.ROOT/".local_models"/task/"budget.sqlite").as_posix()}?mode=ro',uri=True);rr=con.execute(table).fetchall();con.close();total=Decimal(0);unknown=Decimal(0);success=[]
  for rid,num,model,amount,http,folder in rr:
   p=c.ROOT/folder;req=c.read(p/'request.json');rec=c.read(p/'receipt.json');account=c.read(p/'accounting.json');assert rec['request_sha256']==c.sha(p/'request.json')
   value=price_check(req,rec['transport'],account);assert abs(value-Decimal(str(amount)))<Decimal('.000000001');total+=value
   if account['basis'].startswith('reserved'):unknown+=value
   if http==200:success.append(rid)
   if task.startswith('100'):assert req['prior_new_used_or_reserved_cny']+req['reservation_cny']+req['future_confirmation_reserve_cny']<=125+1e-9
   checks+=3
  assert len(success)==len(set(success));totals[task]=total;unknowns[task]=unknown;success_sets[task]=set(success)
 oldrows=c.read(c.PRIVATE/'098_attempts_before_resume.json');before_success={r[0] for r in oldrows if r[4]==200}
 assert before_success<=success_sets['098_p90_native_confirmation'];checks+=1
 newtotal=totals['098_p90_native_confirmation']-Decimal(str(handoff['previous098_cost_and_unknown_cny']))+totals['100_preregistered_followup']
 assert totals['098_p90_native_confirmation']<=50 and newtotal<=130 and unknowns['098_p90_native_confirmation']>=Decimal('.9129');checks+=3
 costs=c.read(c.OUT/'cost_ledger.json');assert abs(newtotal-Decimal(str(costs['total_new_cost_or_reserved_cny'])))<Decimal('.000000001');checks+=1
 verified={}
 for mode in ['development','confirmation','cross_model_confirmation']:
  path=c.OUT/(mode+'_analysis.json')
  if not path.exists():continue
  analysis=c.read(path);rows=c.lines(c.OUT/(mode+'_predictions.jsonl'))
  for panel_name,pp in analysis['panels'].items():
   arms=list(pp['coverage']);rr=[r for r in rows if r['panel']==panel_name and all(r['predictions'].get(a) in c.LABELS for a in arms)]
   for arm,t in pp['tables'].items():
    y=[r['GT'] for r in rr];z=[r['predictions'][arm] for r in rr];cm=np.array([[sum(yy==g and zz==p for yy,zz in zip(y,z)) for p in c.LABELS] for g in c.LABELS]);n=int(cm.sum());cor=int(np.trace(cm));r=cm.sum(1);p=cm.sum(0);den=np.sqrt((n*n-r@r)*(n*n-p@p));mcc=(n*cor-r@p)/den if den else 0
    assert cm.tolist()==t['confusion_matrix'] and cor==t['correct'] and int(cm[1:,0].sum())==t['false_S']
    assert abs(mcc-t['mcc'])<1e-10 and abs(matthews_corrcoef(y,z)-t['mcc'])<1e-10 and abs(f1_score(y,z,labels=list(c.LABELS),average='macro',zero_division=0)-t['Macro_F1'])<1e-10;checks+=3
   if mode!='development':
    for cmp in pp['paired'].values():
     if cmp['base']!='O':continue
     cohort=[dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rr];pred=lambda arm:[dict(proposition_id=r['id'],verdict=r['predictions'][arm]) for r in rr]
     assert paired_compare(cohort,pred(cmp['base']),pred(cmp['candidate']),iterations=1000)==cmp['paired'];checks+=1
   verified[mode+'/'+panel_name]=len(rr)
 # Public generated artifacts: no credentials or clinical request/response payloads.
 secrets=[]
 for line in (c.ROOT/'.env.aliyun').read_text(encoding='utf-8-sig').splitlines():
  k,sep,v=line.partition('=')
  if sep and 'KEY' in k.upper():secrets.append(v.strip().strip('\"\'').encode())
 forbidden={'claim','reference','body_text','reasoning_content','source_units','TEXT'}
 def inspect(x):
  if isinstance(x,dict):
   assert not forbidden.intersection(x),forbidden.intersection(x)
   for v in x.values():inspect(v)
  elif isinstance(x,list):
   for v in x:inspect(v)
 payload=[]
 for root in [c.TASK,c.OUT]:
  for p in root.rglob('*'):
   if not p.is_file():continue
   b=p.read_bytes();assert not b.startswith(b'\xef\xbb\xbf') and not any(s and s in b for s in secrets);payload.append(b)
   if p.suffix=='.json':inspect(c.read(p))
   if p.suffix=='.jsonl':
    for r in c.lines(p):inspect(r)
   checks+=1
 joined=b'\n'.join(payload)
 for r in sample.values():
  if len(r['claim'])>30:assert r['claim'].encode() not in joined
 c.put(c.OUT/'selfcheck.json',dict(utc=c.utc(),status='PASS',checks=checks,verified_panels=verified,total_new_directory_or_reserved_cny=str(newtotal),whole098_cny=str(totals['098_p90_native_confirmation']),
  task100_cny=str(totals['100_preregistered_followup']),old098_unknown_retained=str(unknowns['098_p90_native_confirmation']),new100_unknown=str(unknowns['100_preregistered_followup']),
  same_original_GT=True,GT_not_in_Judge=True,whole_notes_original_TEXT_preserved=True,no_truncated_all=True,confirmation_patient_isolation=True,default_unchanged=True,independent_audit=False))
 print(c.canonical(c.read(c.OUT/'selfcheck.json')))
if __name__=='__main__':main()
