"""Run only after all frozen API first answers; no interim ranking."""
import sys,json,itertools,statistics
from collections import Counter,defaultdict
import common103 as c
import runtime103 as rt
from parse103 import parse
sys.path.insert(0,str(c.ROOT/'tasks/099_judge_selection'))
from analyze099 import panel,metric,pair
def main():
 initial=c.lines(c.PRIVATE/'jobs_selected.jsonl');repair=c.lines(c.PRIVATE/'jobs_label_capacity.jsonl') if (c.PRIVATE/'jobs_label_capacity.jsonl').exists() else [];repeats=c.lines(c.PRIVATE/'jobs_repeats.jsonl') if (c.PRIVATE/'jobs_repeats.jsonl').exists() else [];done=rt.completed()
 required=([j for j in initial if j['mode']=='native']+repair if repair else initial)+repeats
 assert all(j['request_id'] in done for j in required),'No interim quality analysis'
 jobs=[j for j in initial if j['request_id'] in done]+repair+repeats
 sample={r['id']:r for r in c.lines(c.OUT/'cohort240.jsonl')};records={};usage=[];attempts=[];repeated=[]
 con=rt.db();db=con.execute('SELECT rid,num,model,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close()
 for rid,num,m,charge,status,folder in db:attempts.append(dict(request_id=rid,attempt=num,model=m,cost_or_reserve_cny=charge,status=status))
 for j in jobs:
  folder=done[j['request_id']];tr=c.read(folder/'receipt.json')['transport'];response=json.loads(tr['body_text']);u=response['usage'];parsed=parse(tr)
  r=records.setdefault(j['id'],dict(sample[j['id']],predictions={'Original':sample[j['id']]['paper_r1']},arms={}))
  variant='label128_diagnostic' if repair and j['mode']=='label' and j['body']['max_tokens']==128 else j['mode']
  key=j['model']+'__'+variant
  if j['repeat']:repeated.append(dict(id=j['id'],model=j['model'],parsed=parsed))
  else:r['predictions'][key]=parsed['verdict'];r['arms'][key]=parsed
  ip,op,cp=rt.price(j['model'],u['prompt_tokens']);cached=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0);charged=(u['prompt_tokens']*ip+u['completion_tokens']*op)/1e6
  actual=((u['prompt_tokens']-cached)*ip+cached*(cp if cp is not None else ip)+u['completion_tokens']*op)/1e6
  usage.append(dict(id=j['id'],request_id=j['request_id'],model=j['model'],mode=variant,answer_cap=j['body']['max_tokens'],panel=j['panel'],repeat=j['repeat'],prompt_tokens=u['prompt_tokens'],completion_tokens=u['completion_tokens'],reasoning_tokens=(u.get('completion_tokens_details') or {}).get('reasoning_tokens'),cached_tokens=cached,uncached_cny=charged,official_usage_cny=actual,seconds=tr['elapsed_seconds'],finish_reason=parsed.get('finish_reason'),valid=parsed['valid']))
 rows=list(records.values());native=[m+'__native' for m in c.MODELS];label=[m+'__label' for m in c.MODELS]
 result={}
 for p in ['natural','pressure']:
  rr=[r for r in rows if r['panel']==p];result[p]=panel(rr,native);print('evaluated',p,flush=True)
 direct=[r for r in rows if r['direct48']];result['direct48']=panel(direct,label);result['native_same48']=panel(direct,native)
 joint_ids={r['id'] for r in direct if all(r['predictions'].get(k) in c.LABELS for k in native+label)}
 result['mode_common_native']=panel(direct,native,common_ids=joint_ids)
 result['mode_common_label']=panel(direct,label,common_ids=joint_ids)
 result['mode_pairs']={m:pair([r for r in direct if r['predictions'][m+'__native'] and r['predictions'][m+'__label']],m+'__native',m+'__label') for m in c.MODELS}
 for p in ['natural','pressure']:
  result['direct48_'+p]=panel([r for r in direct if r['panel']==p],label)
 result['capacity_diagnostic']={m:dict(original128_observed=sum(m+'__label128_diagnostic' in r['predictions'] for r in direct),original128_valid=sum(r['predictions'].get(m+'__label128_diagnostic') in c.LABELS for r in direct),revised768_valid=sum(r['predictions'].get(m+'__label') in c.LABELS for r in direct),labels_changed_among_both_valid=sum(r['predictions'].get(m+'__label128_diagnostic')!=r['predictions'].get(m+'__label') for r in direct if r['predictions'].get(m+'__label128_diagnostic') in c.LABELS and r['predictions'].get(m+'__label') in c.LABELS),not_a_training_effect=True) for m in c.MODELS}
 result['cost_by_model']={m:{mode:dict(N=len(v),total_official_cny=sum(r['official_usage_cny'] for r in v),total_uncached_cny=sum(r['uncached_cny'] for r in v),mean_input=statistics.mean(r['prompt_tokens'] for r in v),mean_output=statistics.mean(r['completion_tokens'] for r in v),mean_seconds=statistics.mean(r['seconds'] for r in v),thought_at_cap=sum((r['reasoning_tokens'] or 0)>=4096 for r in v)) for mode in ['native','label'] if (v:=[r for r in usage if r['model']==m and r['mode']==mode and r['repeat']==0])} for m in c.MODELS}
 # Predefined practical proximity; direct-mode reversal is reported explicitly.
 tables=result['natural']['tables'];ranked=sorted(c.MODELS,key=lambda m:(-tables[m+'__native']['mcc'],tables[m+'__native']['false_S'],-tables[m+'__native']['percent_agreement']))
 leader=ranked[0];near=[m for m in ranked if tables[m+'__native']['mcc']>=tables[leader+'__native']['mcc']-.02 and tables[m+'__native']['percent_agreement']>=max(tables[x+'__native']['percent_agreement'] for x in c.MODELS)-.02]
 direct_rank=sorted(c.MODELS,key=lambda m:(-result['direct48']['tables'][m+'__label']['mcc'],result['direct48']['tables'][m+'__label']['false_S']))
 reversal=[]
 for a,b in itertools.combinations(c.MODELS,2):
  na=result['mode_common_native']['tables'][a+'__native'];nb=result['mode_common_native']['tables'][b+'__native'];la=result['mode_common_label']['tables'][a+'__label'];lb=result['mode_common_label']['tables'][b+'__label']
  if (na['mcc']-nb['mcc'])*(la['mcc']-lb['mcc'])<0 and (abs(la['mcc']-lb['mcc'])>=.05 or abs(la['correct']-lb['correct'])>=3):reversal.append(dict(a=a,b=b,native_delta_mcc=na['mcc']-nb['mcc'],label_delta_mcc=la['mcc']-lb['mcc'],label_net_correct=la['correct']-lb['correct']))
 result['selection_evidence']=dict(native_rank=ranked,practical_neighbours=near,direct48_rank=direct_rank,material_mode_reversals=reversal,training_not_run=True,not_unique_best_base_claim=True)
 result['repeats']={m:dict(N=len(v),label_flips=sum(x['parsed']['verdict']!=records[x['id']]['predictions'][m+'__native'] for x in v),first_correct=sum(records[x['id']]['predictions'][m+'__native']==sample[x['id']]['GT'] for x in v),second_correct=sum(x['parsed']['verdict']==sample[x['id']]['GT'] for x in v)) for m in c.MODELS if (v:=[r for r in repeated if r['model']==m])}
 c.putl(c.OUT/'repeat_predictions.jsonl',repeated)
 c.putl(c.OUT/'predictions.jsonl',rows);c.putl(c.OUT/'usage.jsonl',usage);c.putl(c.OUT/'attempt_ledger.jsonl',attempts);c.put(c.OUT/'analysis.json',result)
 c.put(c.OUT/'api_cost_ledger.json',dict(utc=c.utc(),cap_cny=30,attempts=len(db),HTTP200=sum(r[4]==200 for r in db),official_usage_cny=sum(r['official_usage_cny'] for r in usage),uncached_budget_used_cny=sum(r[3] for r in db),unknown_or_failure_reserved_cny=sum(r[3] for r in db if r[4]!=200),gpu_cost_cny=0))
 print(c.canonical(result['selection_evidence']))
if __name__=='__main__':main()
