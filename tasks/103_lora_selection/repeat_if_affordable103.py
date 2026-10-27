"""Optional already-frozen24 repeats, only if actual usage permits before scoring."""
import json
import common103 as c
import runtime103 as rt
from run_api103 import guarded
def main():
 assert not (c.OUT/'analysis.json').exists(),'No result-driven repetition'
 first=c.lines(c.PRIVATE/'jobs_selected.jsonl');done=rt.completed();repair=c.lines(c.PRIVATE/'jobs_label_capacity.jsonl') if (c.PRIVATE/'jobs_label_capacity.jsonl').exists() else []
 assert all(j['request_id'] in done for j in ([j for j in first if j['mode']=='native']+repair if repair else first))
 candidates=[j for j in c.lines(c.PRIVATE/'jobs_all.jsonl') if j['repeat']==1]
 originals={(j['id'],j['model']):j for j in first if j['mode']=='native'}
 forecast=0
 for j in candidates:
  orig=originals[j['id'],j['model']];assert orig['body']==j['body']
  response=json.loads(c.read(done[orig['request_id']]/'receipt.json')['transport']['body_text']);u=response['usage'];ip,op,_=rt.price(j['model'],u['prompt_tokens']);forecast+=(u['prompt_tokens']*ip+u['completion_tokens']*1.25*op)/1e6
 before=rt.summary();go=before['used_or_reserved_cny']+forecast+.5<=30
 c.put(c.OUT/'optional_repeat_decision.json',dict(utc=c.utc(),execute=go,frozen_repeats=len(candidates),used_cny=before['used_or_reserved_cny'],repeat_forecast_cny=forecast,recovery_cny=.5,cap_cny=30,correctness_not_inspected=True,reason='Original fixed optional IDs; actual no-cache usage determines affordability, no score-based selection'))
 if go:
  c.putl(c.PRIVATE/'jobs_repeats.jsonl',candidates);rt.process=guarded;rt.run(candidates,workers=16)
 print(c.canonical(c.read(c.OUT/'optional_repeat_decision.json')))
if __name__=='__main__':main()
