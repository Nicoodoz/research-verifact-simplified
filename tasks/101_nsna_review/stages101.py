"""Parse development engineering status and freeze trigger/repeat jobs without outcome selection."""
from collections import Counter
import argparse,json,statistics
import common101 as c,prompts101 as p,runtime101 as rt

def development():
 done=rt.completed();jobs=c.lines(c.PRIVATE/'development_jobs.jsonl');assert all(j['request_id'] in done for j in jobs)
 materials={r['id']:r for r in c.lines(c.PRIVATE/'materials.jsonl')};rows=[]
 for j in jobs:
  folder=done[j['request_id']];tr=c.read(folder/'receipt.json')['transport'];m=materials[j['id']]
  parsed=p.parse(tr,j['arm'],m['reference']);rows.append(dict(id=j['id'],arm=j['arm'],parsed=parsed,receipt_sha256=c.sha(folder/'receipt.json')))
 c.put(c.OUT/'development_interface_check.json',dict(utc=c.utc(),N_ids=12,logical_calls=len(jobs),HTTP200=len(jobs),by_arm={a:dict(valid=sum(r['parsed']['valid'] for r in rows if r['arm']==a),invalid=sum(not r['parsed']['valid'] for r in rows if r['arm']==a)) for a in c.REVIEW_ARMS},rows=rows,method_changed=False,target_confirm_quality_not_read=True,no_response_retries_for_content=True))
 print(c.canonical({a:sum(r['parsed']['valid'] for r in rows if r['arm']==a) for a in c.REVIEW_ARMS}))

def triggers():
 assert not (c.PRIVATE/'run.lock').exists()
 c.read(c.OUT/'development_interface_check.json')
 rows=c.lines(c.OUT/'cohort.jsonl');cache=c.read(c.OUT/'cache_inventory_corrected.json')['selected'];done=rt.completed()
 for rel,h in c.read(c.OUT/'cache_engineering_amendment.json')['files'].items():assert c.sha(c.ROOT/rel)==h
 materials={r['id']:r for r in c.lines(c.PRIVATE/'materials.jsonl')};template=c.read(c.PRIVATE/'template.json')
 for j in c.lines(c.PRIVATE/'baseline_jobs.jsonl')+c.lines(c.PRIVATE/'baseline_extra_jobs.jsonl'):
  assert j['request_id'] in done
  folder=done[j['request_id']];req=c.read(folder/'request.json');tr=c.read(folder/'receipt.json')['transport'];assert req['job']==j
  cache[j['id']]=dict(request_path=(folder/'request.json').relative_to(c.ROOT).as_posix(),receipt_path=(folder/'receipt.json').relative_to(c.ROOT).as_posix(),request_sha256=c.sha(folder/'request.json'),receipt_sha256=c.sha(folder/'receipt.json'),body_sha256=j['body_sha256'],source='101_new',utc=tr['started_utc'],parsed=p.parse(tr,'verifact_ref',''))
 confirmed=[r for r in rows if r['stage']=='confirmation'];assert len(confirmed)==700 and all(r['id'] in cache for r in confirmed)
 triggered=[r for r in confirmed if cache[r['id']]['parsed']['verdict'] in c.LABELS[1:]]
 repeat=sorted(triggered,key=lambda r:c.digest('101/repeat/v1/'+r['id']))[:24];assert len(repeat)==24;repeatids={r['id'] for r in repeat}
 jobs=[]
 for r in triggered:
  m=materials[r['id']]
  for arm in c.REVIEW_ARMS:
   b=p.body(template,m['claim'],m['reference'],arm);jobs.append(c.job(r,arm,b))
   if r['id'] in repeatids:jobs.append(c.job(r,arm,b,True))
 c.putl(c.PRIVATE/'confirmation_jobs.jsonl',jobs)
 c.put(c.OUT/'baseline_bindings.json',cache)
 public=[dict(id=r['id'],sid=r['sid'],panel=r['panel'],origin=r['origin'],baseline_label=cache[r['id']]['parsed']['verdict'],triggered=r in triggered,repeat_subset=r['id'] in repeatids,claim_sha256=r['claim_sha256'],reference_sha256=r['reference_sha256']) for r in confirmed]
 c.putl(c.OUT/'trigger_panel.jsonl',public)
 # Updated cost uses only aggregate usage, no new review labels/quality.
 hist={a:[] for a in c.REVIEW_ARMS}
 for j in c.lines(c.PRIVATE/'development_jobs.jsonl'):
  u=json.loads(c.read(done[j['request_id']]/'receipt.json')['transport']['body_text'])['usage'];hist[j['arm']].append(u)
 plan=c.read(c.OUT/'budget_plan.json');expected=0;forecast_details=[]
 for j in jobs:
  avg=statistics.mean(u['completion_tokens'] for u in hist[j['arm']])
  binding=cache[j['id']];tr=c.read(c.ROOT/binding['receipt_path'])['transport'];u=json.loads(tr['body_text'])['usage']
  req=c.read(c.ROOT/binding['request_path']);basebody=req.get('job',req).get('body',req.get('body'))
  oldchars=sum(len(m['content']) for m in basebody['messages']);newchars=sum(len(m['content']) for m in j['body']['messages'])
  input_est=u['prompt_tokens']+max(0,newchars-oldchars)*max(.35,u['prompt_tokens']/oldchars)
  estimate=(input_est*3+max(avg*1.25,700 if j['arm']=='nsna_plain' else 1100)*9)/1e6;expected+=estimate
  forecast_details.append(dict(id=j['id'],arm=j['arm'],repeat=j['repeat'],actual_baseline_prompt_tokens=u['prompt_tokens'],actual_prompt_char_delta=newchars-oldchars,input_token_estimate=input_est,cost_estimate_cny=estimate))
 c.putl(c.OUT/'remaining_forecast.jsonl',forecast_details)
 c.put(c.OUT/'trigger_freeze.json',dict(utc=c.utc(),files={x.relative_to(c.ROOT).as_posix():c.sha(x) for x in [c.PRIVATE/'confirmation_jobs.jsonl',c.OUT/'baseline_bindings.json',c.OUT/'trigger_panel.jsonl',c.OUT/'remaining_forecast.jsonl',c.TASK/'stages101.py',c.TASK/'analyze101.py']},triggered=len(triggered),by_panel=dict(Counter(r['panel'] for r in triggered)),repeat_N=24,logical_calls=len(jobs),review_calls_equal=True,expected_remaining_peak_cny=expected,current_ledger=rt.summary(),expected_total=expected+rt.summary()['used_or_reserved_cny'],review_labels_not_used_for_selection=True))
 print(c.canonical(c.read(c.OUT/'trigger_freeze.json')))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['development','triggers']);args=ap.parse_args()
 development() if args.mode=='development' else triggers()
