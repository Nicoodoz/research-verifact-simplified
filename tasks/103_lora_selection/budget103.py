"""Single score-blind decision after 24 reusable usage probes."""
import statistics
from collections import defaultdict
import common103 as c
import runtime103 as rt
from parse103 import parse
def main():
 done=rt.completed();jobs=c.lines(c.PRIVATE/'jobs_all.jsonl');freeze=c.read(c.OUT/'data_freeze.json');assert all(x in done for x in freeze['usage_probe_ids'])
 usage=[]
 for j in jobs:
  if j['request_id'] not in done:continue
  tr=c.read(done[j['request_id']]/'receipt.json')['transport'];response=__import__('json').loads(tr['body_text']);u=response['usage'];p=parse(tr)
  usage.append(dict(request_id=j['request_id'],model=j['model'],mode=j['mode'],panel=j['panel'],input=u['prompt_tokens'],output=u['completion_tokens'],valid_format=p['valid'],finish_reason=p.get('finish_reason'),reason_present=p.get('reason_present'),seconds=tr['elapsed_seconds']))
 c.put(c.OUT/'usage_preflight.json',dict(rows=usage,correctness_not_computed=True,cost=rt.summary()))
 assert all(x['valid_format'] and x['finish_reason']=='stop' for x in usage),'Engineering inspection needed before classification'
 lengths={(r['id'],r['model']):r for r in c.lines(c.OUT/'api_token_lengths.jsonl')}
 # 099 observed native output (2048 thinking cap), no correctness columns.
 old=c.lines(c.ROOT/'outputs/099_judge_selection/usage.jsonl')
 print('historical usage schema',sorted(old[0]),flush=True)
 # Native 4096: allow above both current probes and published099 native averages.
 floors={'qwen3.5-27b':1731,'qwen3.5-35b-a3b':1720,'qwen3.8-27b':674,'qwen3.6-35b-a3b':1720}
 means={}
 for m in c.MODELS:
  for mode in ['native','label']:
   for panel in ['natural','pressure']:
    vals=[x['output'] for x in usage if x['model']==m and x['mode']==mode and x['panel']==panel]
    if not vals:vals=[x['output'] for x in usage if x['model']==m and x['mode']==mode]
    means[m,mode,panel]=max(statistics.mean(vals),floors[m] if mode=='native' else 24)
 alternatives=[]
 for n,repeats in [(240,True),(240,False),(180,False)]:
  chosen=[j for j in jobs if (n==240 or j['local180']) and (repeats or j['repeat']==0)]
  estimates={m:0 for m in c.MODELS};mean_est={m:0 for m in c.MODELS}
  for j in chosen:
   inp=lengths[j['id'],j['model']][j['mode']]+128;ip,op,_=rt.price(j['model'],inp);out=means[j['model'],j['mode'],j['panel']]
   estimates[j['model']]+=(inp*ip+out*1.2*op)/1e6;mean_est[j['model']]+=(inp*ip+out*op)/1e6
  estimate=sum(estimates.values())+.6
  alternatives.append(dict(main_n=n,repeats24_per_model=repeats,requests=len(chosen),mean_cny=sum(mean_est.values()),with_output20pct_and_recovery06_cny=estimate,by_model=estimates))
  if estimate<=c.CAP:break
 else:raise RuntimeError('Even180 exceeds budget; keep all preflight responses and report gap')
 c.putl(c.PRIVATE/'jobs_selected.jsonl',chosen)
 c.put(c.OUT/'budget_plan.json',dict(utc=c.utc(),alternatives=alternatives,chosen=alternatives[-1],cap_cny=30,no_cache_assumed=True,correctness_not_computed=True,output_forecasts=[dict(model=m,mode=mode,panel=p,output_mean=v) for (m,mode,p),v in means.items()]))
 paths=[c.PRIVATE/'jobs_selected.jsonl',c.TASK/'runtime103.py',c.TASK/'parse103.py',c.OUT/'budget_plan.json',c.OUT/'model_metadata.json',c.TASK/'protocol.md']
 c.put(c.OUT/'api_execution_freeze.json',dict(utc=c.utc(),chosen=alternatives[-1],files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},preflight_answers_reused=True,no_correctness_inspected=True))
 print(c.canonical(alternatives))
if __name__=='__main__':main()
