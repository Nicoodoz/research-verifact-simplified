"""Freeze700 confirmation IDs and one prompt before new target answers; verify cached bodies."""
from collections import Counter,defaultdict
import copy,json,statistics,sys
import duckdb,pandas as pd
import common101 as c
import prompts101 as p

def proportional(pool,n,seed):
 groups=defaultdict(list)
 for r in pool:groups[r['GT'],r['author']].append(r)
 exact={k:n*len(v)/len(pool) for k,v in groups.items()};quotas={k:int(v) for k,v in exact.items()}
 for k in sorted(groups,key=lambda k:(-(exact[k]-quotas[k]),k))[:n-sum(quotas.values())]:quotas[k]+=1
 chosen=[r for k,v in groups.items() for r in sorted(v,key=lambda r:c.digest(seed+r['id']))[:quotas[k]]]
 assert len(chosen)==n
 return chosen

def main():
 assert not (c.OUT/'execution_freeze.json').exists()
 c.PRIVATE.mkdir(parents=True,exist_ok=True)
 original=c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')
 pool=[dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],author=r['author'],paper_r1=r['original'],historical_role=r['historical_role']) for r in original]
 byid={r['id']:r for r in pool}
 old098=c.lines(c.ROOT/'outputs/098_p90_native_confirmation/cohort.jsonl')
 old100=c.lines(c.ROOT/'outputs/100_preregistered_followup/confirmation_predictions.jsonl')
 confirmation_patients=set(c.read(c.ROOT/'outputs/098_p90_native_confirmation/execution_freeze.json')['evaluation_patients'])
 development_patients=set(c.read(c.ROOT/'outputs/100_preregistered_followup/execution_freeze.json')['confirmation_patients'])
 assert len(confirmation_patients)==40 and len(development_patients)==32 and not confirmation_patients&development_patients
 oldids={r['id'] for r in old098};assert len(oldids)==500
 new=proportional([r for r in pool if r['sid'] in confirmation_patients and r['id'] not in oldids],200,'101/additional/v1/')
 rows=[dict(byid[r['id']],stage='confirmation',panel=r['panel'],origin='098_frozen') for r in old098]
 rows +=[dict(r,stage='confirmation',panel='natural',origin='additional200') for r in new]
 # All224 archived cases available for offline development; only12 fixed triggers paid.
 dev=[dict(byid[r['id']],stage='development',panel=r['panel'],origin='100_confirmation') for r in old100]
 assert len(dev)==224 and {r['sid'] for r in dev}==development_patients
 allrows=rows+dev;ids={r['id'] for r in allrows};assert len(ids)==len(allrows)
 inputs={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl') if r['proposition_id'] in ids}
 with duckdb.connect() as db:
  db.register('wanted',pd.DataFrame({'proposition_id':sorted(ids)}))
  links=db.execute('SELECT proposition_id,reference_id,verdict FROM read_parquet(?) JOIN wanted USING(proposition_id) WHERE rater_alias=?',[str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet'),'v1.1.0-rater-121']).fetchall()
  assert len(links)==len(ids)
  db.register('refs',pd.DataFrame({'reference_id':sorted({x[1] for x in links})}))
  refs=dict(db.execute('SELECT reference_id,reference FROM read_parquet(?) JOIN refs USING(reference_id)',[str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/reference_payloads.parquet')]).fetchall())
 links={pid:(ref,v) for pid,ref,v in links}
 template=next(j['body'] for j in c.lines(c.ROOT/'.local_models/098_p90_native_confirmation/jobs.jsonl') if j['arm']=='O' and not j['repeat'])
 template={k:copy.deepcopy(v) for k,v in template.items() if k!='messages'}
 assert template==dict(model=c.MODEL,enable_thinking=True,reasoning_effort='high',temperature=0,max_tokens=8192,n=1,stream=False)
 materials=[];wanted={}
 for row in allrows:
  ref,verdict=links[row['id']];claim=inputs[row['id']]['text'];reference=refs[ref]
  assert c.digest(reference)==ref and verdict==row['paper_r1']
  m=dict(id=row['id'],sid=row['sid'],claim=claim,reference=reference);materials.append(m)
  row.update(claim_sha256=c.digest(claim),reference_sha256=ref,reference_chars=len(reference))
  b=p.body(template,claim,reference,'verifact_ref');wanted[row['id']]=c.job(row,'verifact_ref',b)
 # Inventory every same-patient published-native first/repeat request in098/100 and097.
 # Earliest success wins even if invalid; no outcome-dependent cache selection.
 candidates=defaultdict(list)
 for task,file in [('098_p90_native_confirmation','attempt_ledger.jsonl'),('100_preregistered_followup','confirmation_attempt_ledger.jsonl'),('097_native_judge_source_dependence','a_request_ledger.jsonl')]:
  for line in c.lines(c.ROOT/'outputs'/task/file):
   if line.get('status',line.get('http_status'))!=200:continue
   folder=c.ROOT/line['folder'];reqpath=folder/'request.json';recpath=folder/'receipt.json';req=c.read(reqpath)
   job=req.get('job',req);body=job.get('body',req.get('body'));pid=job.get('id',req.get('id'))
   if pid not in wanted or body!=wanted[pid]['body']:continue
   if req.get('endpoint',c.ENDPOINT)!=c.ENDPOINT:continue
   if line.get('request_sha256'):assert c.sha(reqpath)==line['request_sha256']
   if line.get('receipt_sha256'):assert c.sha(recpath)==line['receipt_sha256']
   rec=c.read(recpath);tr=rec['transport'];assert tr['http_status']==200
   if rec.get('request_sha256'):assert rec['request_sha256']==c.sha(reqpath)
   candidates[pid].append(dict(request_path=reqpath.relative_to(c.ROOT).as_posix(),receipt_path=recpath.relative_to(c.ROOT).as_posix(),request_sha256=c.sha(reqpath),receipt_sha256=c.sha(recpath),utc=tr['started_utc'],body_sha256=c.digest(c.canonical(body)),source=task))
 cache={};history_usage=[]
 for pid,cc in candidates.items():
  chosen=min(cc,key=lambda x:(x['utc'],x['request_path']));tr=c.read(c.ROOT/chosen['receipt_path'])['transport'];parsed=p.parse(tr,'verifact_ref','')
  cache[pid]=dict(chosen,parsed=parsed,candidate_count=len(cc))
  u=json.loads(tr['body_text'])['usage'];history_usage.append(u)
 assert all(r['id'] in cache for r in old098+old100)
 devselected=[]
 for label in c.LABELS[1:]:
  pp=[r for r in dev if cache[r['id']]['parsed']['verdict']==label]
  devselected.extend(sorted(pp,key=lambda r:c.digest('101/development/interface/v1/'+r['id']))[:6])
 assert len(devselected)==12
 devselected_ids={r['id'] for r in devselected}
 for row in dev:row['interface_selected']=row['id'] in devselected_ids
 mm={m['id']:m for m in materials};newbaseline=[wanted[r['id']] for r in rows if r['id'] not in cache]
 devjobs=[c.job(r,a,p.body(template,mm[r['id']]['claim'],mm[r['id']]['reference'],a)) for r in devselected for a in c.REVIEW_ARMS]
 c.put(c.PRIVATE/'template.json',template);c.putl(c.PRIVATE/'materials.jsonl',materials)
 c.putl(c.PRIVATE/'baseline_jobs.jsonl',newbaseline);c.putl(c.PRIVATE/'development_jobs.jsonl',devjobs)
 c.putl(c.OUT/'cohort.jsonl',allrows);c.put(c.OUT/'cache_inventory.json',dict(selected=cache,scope='098/100/097 published-native exact full body, endpoint; earliest success including invalid',cached=len(cache),new_baseline_calls=len(newbaseline)))
 known_trigger=sum(cache[r['id']]['parsed']['verdict'] in c.LABELS[1:] for r in rows if r['id'] in cache)
 natural_cached=[r for r in rows if r['panel']=='natural' and r['id'] in cache]
 rate=sum(cache[r['id']]['parsed']['verdict'] in c.LABELS[1:] for r in natural_cached)/len(natural_cached)
 pending=len(newbaseline);expected_trigger=known_trigger+pending*rate
 avg_input=statistics.mean(u['prompt_tokens'] for u in history_usage);avg_output=statistics.mean(u['completion_tokens'] for u in history_usage)
 baseline_est=pending*(avg_input*3+max(600,avg_output*1.25)*9)/1e6
 # Different prompt/output costs forecast conservatively from actual native usage.
 per_plain=((avg_input+300)*3+max(700,avg_output*1.5)*9)/1e6
 per_review=((avg_input+500)*3+max(1100,avg_output*2)*9)/1e6
 estimated=baseline_est+(expected_trigger+12+24)*(per_plain+per_review)
 budget=dict(utc=c.utc(),hard_cap=30,known_confirmation_triggers=known_trigger,expected_additional_trigger_rate=rate,new_baseline_calls=pending,expected_review_triggers=expected_trigger,expected_cost_cny=estimated,recovery_margin=30-estimated,historical_mean_input=avg_input,historical_mean_output=avg_output,per_plain=per_plain,per_review=per_review,baseline_estimate=baseline_est,no_cache_discount_assumed=True,maximum8192_reserved_per_attempt_not_whole_task_forecast=True)
 c.put(c.OUT/'budget_plan.json',budget)
 files=[c.TASK/x for x in ['protocol.md','prompts101.py','common101.py','prepare101.py','runtime101.py','test101.py']]+[c.OUT/'cohort.jsonl',c.OUT/'cache_inventory.json',c.OUT/'budget_plan.json']+[c.PRIVATE/x for x in ['template.json','materials.jsonl','baseline_jobs.jsonl','development_jobs.jsonl']]
 assert estimated<30,('Forecast needs optimization before calls',estimated)
 c.put(c.OUT/'execution_freeze.json',dict(utc=c.utc(),start_main='f0e2b4b996d427176afb05d2ec67e33e6448b8ea',files={x.relative_to(c.ROOT).as_posix():c.sha(x) for x in files},development_patients=sorted(development_patients),confirmation_patients=sorted(confirmation_patients),confirmation_natural=600,confirmation_pressure=100,development_offline=224,development_interface=12,new_additional_GT=dict(Counter(r['GT'] for r in new)),new_additional_author=dict(Counter(r['author'] for r in new)),no_new_answer_before_freeze=True,history_exposed=True))
 print(c.canonical(budget),flush=True)

if __name__=='__main__':main()
