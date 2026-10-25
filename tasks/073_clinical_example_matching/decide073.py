"""Apply pre-registered pilot selection once; freeze confirmation before sending."""
import json,hashlib
from collections import Counter
from materials073 import ROOT,OUT,read,lines,sha,put,jl,digest
import run073 as r
def main():
 a=read(OUT/'pilot_analysis.json');m=a['final_metrics'];raw=a['raw_metrics']
 eligible=[k for k in ['L4','M4'] if m[k]['correct']>=max(m['B']['correct'],m['F4']['correct']) and m[k]['falseS']<=m['F4']['falseS']+1 and raw[k]['correct']>=raw['B']['correct']-1]
 selected=sorted(eligible,key=lambda k:(-m[k]['correct'],-m[k]['MCC'],m[k]['falseS'],k))[0] if eligible else None
 arms=['B','F4',selected] if selected else (['B','F4'] if m['F4']['correct']>m['B']['correct'] else [])
 attempts,_=r.attempt_state();used=sum(x['cost_cny'] for x in attempts)
 jobs=[j for j in lines(OUT/'all_arm_jobs.jsonl') if j['stage']=='confirmation' and j['arm'] in arms]
 unique=sorted({j['request_id']:j for j in jobs}.values(),key=lambda j:digest('073/order:'+j['request_id']))
 # Same scheme, similar references; use pilot observed per-arm mean plus 25% margin.
 forecast=used+sum((a['tokens_by_arm'][arm]['prompt_mean']*3+a['tokens_by_arm'][arm]['completion_mean']*9)/1e6*60 for arm in arms)*1.25
 d=dict(created_utc=r.now(),eligible=eligible,selected_dynamic=selected,confirmation_arms=arms,pilot_analysis_sha256=sha(OUT/'pilot_analysis.json'),used_cny=used,forecast_with_25pct_future_margin_cny=forecast,cap_cny=20.,decision='confirm' if arms and forecast<19.5 else 'stop',reason='pre_registered_effect_screen' if not arms else ('forecast_budget' if forecast>=19.5 else 'selected_on_pilot_only'))
 put(OUT/'confirmation_decision.json',d)
 if d['decision']=='confirm':
  jl(OUT/'confirmation_aliases.jsonl',jobs);jl(OUT/'confirmation_jobs.jsonl',unique)
  put(OUT/'confirmation_freeze.json',dict(stage='confirmation',created_utc=r.now(),source_freeze_sha256=sha(OUT/'freeze.json'),jobs_sha256=sha(OUT/'confirmation_jobs.jsonl'),aliases_sha256=sha(OUT/'confirmation_aliases.jsonl'),decision_file='confirmation_decision.json',decision_sha256=sha(OUT/'confirmation_decision.json'),selector_unchanged=True,target_GT_used_for_selection=False))
 print(json.dumps(d,ensure_ascii=False))
if __name__=='__main__':main()
