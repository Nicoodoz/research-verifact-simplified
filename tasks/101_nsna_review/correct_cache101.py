"""Reject endpoint-unverified097 uniformly, preserving original inventory/freezes and successes."""
from collections import defaultdict,Counter
import json
import common101 as c,prompts101 as p
def main():
 original=c.read(c.OUT/'cache_inventory.json');rows=c.lines(c.OUT/'cohort.jsonl');materials={r['id']:r for r in c.lines(c.PRIVATE/'materials.jsonl')};template=c.read(c.PRIVATE/'template.json')
 expected={r['id']:p.body(template,materials[r['id']]['claim'],materials[r['id']]['reference'],'verifact_ref') for r in rows};candidates=defaultdict(list)
 for task in ['098_p90_native_confirmation','100_preregistered_followup']:
  filename='attempt_ledger.jsonl' if task.startswith('098') else 'confirmation_attempt_ledger.jsonl'
  for line in c.lines(c.ROOT/'outputs'/task/filename):
   if line['status']!=200:continue
   fp=c.ROOT/line['folder'];req=c.read(fp/'request.json');j=req['job'];pid=j['id']
   if pid not in expected or j['body']!=expected[pid] or req.get('endpoint')!=c.ENDPOINT:continue
   rec=c.read(fp/'receipt.json');tr=rec['transport'];assert c.sha(fp/'request.json')==line['request_sha256'] and c.sha(fp/'receipt.json')==line['receipt_sha256'] and rec['request_sha256']==line['request_sha256']
   candidates[pid].append(dict(request_path=(fp/'request.json').relative_to(c.ROOT).as_posix(),receipt_path=(fp/'receipt.json').relative_to(c.ROOT).as_posix(),request_sha256=line['request_sha256'],receipt_sha256=line['receipt_sha256'],utc=tr['started_utc'],body_sha256=c.digest(c.canonical(j['body'])),source=task,parsed=p.parse(tr,'verifact_ref','')))
 cache={pid:dict(min(cc,key=lambda x:(x['utc'],x['request_path'])),candidate_count=len(cc)) for pid,cc in candidates.items()}
 already={j['id'] for j in c.lines(c.PRIVATE/'baseline_jobs.jsonl')};extra=[c.job(r,'verifact_ref',expected[r['id']]) for r in rows if r['stage']=='confirmation' and r['id'] not in cache and r['id'] not in already]
 rejected=[pid for pid,b in original['selected'].items() if c.read(c.ROOT/b['request_path']).get('endpoint')!=c.ENDPOINT]
 assert len(rejected)==15,dict(rejected=len(rejected),extra=len(extra))
 # The official098 first answers are exactly preserved, without selecting their quality.
 official=c.lines(c.ROOT/'outputs/098_p90_native_confirmation/predictions.jsonl')
 assert all(cache[r['id']]['parsed']['verdict']==r['predictions']['O'] for r in official)
 c.put(c.OUT/'cache_inventory_corrected.json',dict(selected=cache,scope='Explicit current endpoint only; same body, earliest successful098/100; all097 absent-endpoint records uniformly excluded',cached=len(cache),additional_missing=len(extra)))
 c.putl(c.PRIVATE/'baseline_extra_jobs.jsonl',extra)
 c.put(c.OUT/'cache_engineering_amendment.json',dict(utc=c.utc(),reason='prepare101 incorrectly defaulted an absent endpoint to current endpoint. Reject every absent endpoint record irrespective of verdict.',original_artifacts_preserved=True,rejected_IDs=rejected,extra_baseline_IDs=[j['id'] for j in extra],all_confirmation_IDs_unchanged=True,prompts_unchanged=True,review_confirmation_not_started=True,original098_labels_preserved=True,historical_confusion_common_panels=37,historical_confusion_own_baseline_valid=38,historical_patients=28,files={x.relative_to(c.ROOT).as_posix():c.sha(x) for x in [c.OUT/'cache_inventory_corrected.json',c.PRIVATE/'baseline_extra_jobs.jsonl',c.TASK/'correct_cache101.py']}))
 print(c.canonical(dict(rejected=len(rejected),extra=len(extra),cache_sources=dict(Counter(x['source'] for x in cache.values())))))
if __name__=='__main__':main()
