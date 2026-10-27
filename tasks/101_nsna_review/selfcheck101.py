"""Read-only scientific verification; writes only101 selfcheck, never changes frozen artifacts."""
from collections import Counter
from decimal import Decimal
import json,sqlite3
import numpy as np
import common101 as c,prompts101 as p,runtime101 as rt
from analyze101 import metric,compare
import prepare101

def main():
 checks=0
 def check(test,message):
  nonlocal checks
  assert test,message;checks+=1
 freeze=c.read(c.OUT/'execution_freeze.json');triggerfreeze=c.read(c.OUT/'trigger_freeze.json')
 for record in [freeze,triggerfreeze,c.read(c.OUT/'cache_engineering_amendment.json')]:
  for rel,h in record['files'].items():check(c.sha(c.ROOT/rel)==h,rel)
 check(not (c.PRIVATE/'run.lock').exists(),'active run')
 d=set(freeze['development_patients']);v=set(freeze['confirmation_patients']);check(len(d)==32 and len(v)==40 and not d&v,'patient isolation')
 cohort=c.lines(c.OUT/'cohort.jsonl');original={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')}
 old=c.lines(c.ROOT/'outputs/098_p90_native_confirmation/cohort.jsonl');oldids={r['id'] for r in old};oldmap={r['id']:r for r in old}
 newpool=[dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],author=r['author']) for r in original.values() if str(r['sid']) in v and r['id'] not in oldids]
 expected={r['id'] for r in prepare101.proportional(newpool,200,'101/additional/v1/')}
 check(expected=={r['id'] for r in cohort if r['origin']=='additional200'},'additional sample replay')
 conf=[r for r in cohort if r['stage']=='confirmation'];check(Counter(r['panel'] for r in conf)=={'natural':600,'pressure':100},'all700 frozen')
 for r in cohort:
  o=original[r['id']];check(r['GT']==o['GT'] and r['author']==o['author'] and r['sid']==str(o['sid']) and r['paper_r1']==o['original'],'original identity')
  if r['origin']=='098_frozen':check(r['panel']==oldmap[r['id']]['panel'],'098 panel untouched')
 materials={r['id']:r for r in c.lines(c.PRIVATE/'materials.jsonl')};bindings=c.read(c.OUT/'baseline_bindings.json');template=c.read(c.PRIVATE/'template.json')
 for r in cohort:
  m=materials[r['id']];check(c.digest(m['claim'])==r['claim_sha256'] and c.digest(m['reference'])==r['reference_sha256'],'source byte hashes')
 for r in conf:
  b=bindings[r['id']];req=c.read(c.ROOT/b['request_path']);rec=c.read(c.ROOT/b['receipt_path']);body=req.get('job',req).get('body',req.get('body'));m=materials[r['id']]
  check(c.sha(c.ROOT/b['request_path'])==b['request_sha256'] and c.sha(c.ROOT/b['receipt_path'])==b['receipt_sha256'],'baseline original bytes')
  check(body==p.body(template,m['claim'],m['reference'],'verifact_ref'),'full baseline contract')
  check(req.get('endpoint')==c.ENDPOINT,'explicit endpoint verified')
  check(p.parse(rec['transport'],'verifact_ref',m['reference'])==b['parsed'],'baseline parse unchanged')
 jobs=c.lines(c.PRIVATE/'confirmation_jobs.jsonl');first=[j for j in jobs if not j['repeat']];repeat=[j for j in jobs if j['repeat']]
 check(Counter(j['arm'] for j in first)['nsna_plain']==Counter(j['arm'] for j in first)['nsna_review'],'equal calls')
 triggerids={r['id'] for r in conf if bindings[r['id']]['parsed']['verdict'] in c.LABELS[1:]}
 for arm in c.REVIEW_ARMS:check({j['id'] for j in first if j['arm']==arm}==triggerids,'same trigger set')
 repids=set(sorted(triggerids,key=lambda pid:c.digest('101/repeat/v1/'+pid))[:24])
 check(len(repeat)==48 and all({j['id'] for j in repeat if j['arm']==a}==repids for a in c.REVIEW_ARMS),'repeat sampling')
 done=rt.completed()
 for j in jobs:
  m=materials[j['id']];check(j['body']==p.body(template,m['claim'],m['reference'],j['arm']),'blind unchanged inputs')
  payload=json.loads(j['body']['messages'][1]['content'].split('## Input JSON:\n')[1]);check(set(payload)=={'text','reference'},'no prior answer or GT fields')
  check(j['request_id'] in done,'all review HTTP200 present');req=c.read(done[j['request_id']]/'request.json');check(req['job']==j,'native request equality')
  check(j['body_sha256']==c.digest(c.canonical(j['body'])),'body hash')
  check({k:v for k,v in j['body'].items() if k!='messages'}==template,'identical generation settings')
 rows=c.lines(c.OUT/'predictions.jsonl');valid=[r for r in rows if r['baseline_valid']];analysis=c.read(c.OUT/'analysis.json')
 check(len(rows)==700 and len({r['id'] for r in rows})==700,'no dropped cases')
 for r in rows:
  b=r['predictions']['verifact_ref'];check(b==bindings[r['id']]['parsed']['verdict'],'no baseline replacement')
  for arm in c.REVIEW_ARMS:
   check((r['predictions'][arm]=='Supported')==(b=='Supported'),'S set invariant')
   if b in c.LABELS[1:]:
    j=next(j for j in first if j['id']==r['id'] and j['arm']==arm);parsed=p.parse(c.read(done[j['request_id']]/'receipt.json')['transport'],arm,materials[r['id']]['reference'])
    check(r['predictions'][arm]==(parsed['verdict'] if parsed['valid'] else b),'invalid retain base')
 for name,rr in [('natural',[r for r in valid if r['panel']=='natural']),('pressure',[r for r in valid if r['panel']=='pressure']),('additional200',[r for r in valid if r['origin']=='additional200'])]:
  for arm,reported in analysis['tables'][name].items():
   z=metric(rr,arm);check(z==reported,'official and sklearn metrics')
  for arm in c.REVIEW_ARMS:check(analysis['tables'][name][arm]['false_S']==analysis['tables'][name]['verifact_ref']['false_S'],'falseS exact equality')
  z=compare(rr,'verifact_ref','nsna_review');check(z==analysis['paired'][name]['nsna_review__vs__verifact_ref'],'patient bootstrap replay')
 # Independent sufficient-count MCC and PA (not a second label mapping).
 for name,tt in analysis['tables'].items():
  for arm,z in tt.items():
   cm=np.array(z['confusion_matrix'],dtype=float);n=cm.sum();a=cm.sum(0);b=cm.sum(1);correct=np.trace(cm);den=np.sqrt((n*n-(a*a).sum())*(n*n-(b*b).sum()));mcc=(n*correct-(a*b).sum())/den if den else 0.
   check(abs(mcc-z['mcc'])<1e-10 and abs(correct/n-z['percent_agreement'])<1e-10,'independent formula')
 con=rt.db();attempts=con.execute('SELECT rid,num,arm,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close();cost=Decimal(0);seen=set();unknown=Decimal(0)
 for rid,num,arm,charge,status,folder in attempts:
  fp=c.ROOT/folder;req=c.read(fp/'request.json');rec=c.read(fp/'receipt.json');tr=rec['transport'];check(c.sha(fp/'request.json')==rec['request_sha256'],'receipt binding')
  amount,basis=rt.account(req['job'],tr,req['reservation_cny']);check(abs(amount-charge)<1e-9,'cost ledger')
  check(req['prior_used_or_reserved_cny']+req['reservation_cny']<=30+1e-9,'transaction cap')
  if status==200:check(rid not in seen,'no successful request repeated');seen.add(rid)
  cost+=Decimal(str(amount))
  if 'reserved' in basis:unknown+=Decimal(str(amount))
 check(cost<=Decimal('30'),'whole task cap')
 result=dict(utc=c.utc(),status='PASS',checks=checks,independent_audit=False,confirmed_natural=600,confirmed_pressure=100,baseline_valid=len(valid),triggered=len(triggerids),repeated=24,all_S_predictions_identical=True,no_GT_or_first_answer_in_review_inputs=True,source_reference_SHA_preserved=True,patient_isolation=True,new_API_or_reserved_cny=str(cost),unknown_or_unverified_cny=str(unknown),history_not_rewritten=True)
 c.put(c.OUT/'selfcheck.json',result);print(c.canonical(result),flush=True)
if __name__=='__main__':main()
