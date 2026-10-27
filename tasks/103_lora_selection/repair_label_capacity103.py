"""Uniform answer-capacity repair before any correctness inspection; preserve128 arm."""
import json,statistics
from collections import defaultdict
import common103 as c
import runtime103 as rt
from run_api103 import guarded
def main():
 assert not (c.OUT/'analysis.json').exists()
 jobs=c.lines(c.PRIVATE/'jobs_selected.jsonl');done=rt.completed();usage=defaultdict(list);truncated=[]
 for j in jobs:
  if j['request_id'] not in done:continue
  response=json.loads(c.read(done[j['request_id']]/'receipt.json')['transport']['body_text']);u=response['usage'];usage[j['model'],j['mode']].append(u['completion_tokens'])
  if response['choices'][0]['finish_reason']=='length':truncated.append(dict(request_id=j['request_id'],model=j['model'],mode=j['mode'],answer_cap=j['body']['max_tokens'],completion_tokens=u['completion_tokens']))
 assert truncated and all(x['mode']=='label' for x in truncated)
 lengths={(r['id'],r['model']):r for r in c.lines(c.OUT/'api_token_lengths.jsonl')};repair=[];remaining_forecast=0;repair_forecast=0
 for j in jobs:
  ip,op,_=rt.price(j['model'],lengths[j['id'],j['model']][j['mode']]+128)
  if j['request_id'] not in done:remaining_forecast+=((lengths[j['id'],j['model']][j['mode']]+128)*ip+statistics.mean(usage[j['model'],j['mode']])*1.2*op)/1e6
  if j['mode']=='label':
   b=dict(j['body'],max_tokens=768);h=c.digest(c.canonical(b));new=dict(j,body=b,body_sha256=h,request_id=c.digest(c.canonical(['103/label_capacity_repair/v1',j['id'],j['model'],h]))[:28],replaces_request_id=j['request_id'])
   repair.append(new);repair_forecast+=((lengths[j['id'],j['model']]['label']+128)*ip+768*op)/1e6
 current=rt.summary()['used_or_reserved_cny'];forecast=current+remaining_forecast+repair_forecast+.4
 assert forecast<=30,f'Uniform engineering repair budget forecast {forecast}'
 c.putl(c.PRIVATE/'jobs_label_capacity.jsonl',repair)
 paths=[c.PRIVATE/'jobs_label_capacity.jsonl',c.TASK/'repair_label_capacity103.py']
 c.put(c.OUT/'label_capacity_amendment.json',dict(utc=c.utc(),before_correctness_analysis=True,original_max_tokens=128,revised_max_tokens=768,all_four_models_same48_replayed=True,original_results_preserved=True,reason='One direct response emitted prose and was truncated; test sufficient capacity uniformly, no label-driven retry',truncated_observed=truncated,used_or_reserved_cny=current,remaining_original_forecast_cny=remaining_forecast,repair_all_max_output_forecast_cny=repair_forecast,total_forecast_with_margin_cny=forecast,optional_repeats_lower_priority=True,files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths}))
 print(c.canonical(c.read(c.OUT/'label_capacity_amendment.json')),flush=True)
 rt.reconcile=lambda:None;rt.process=guarded;rt.run(repair,workers=12)
if __name__=='__main__':main()
