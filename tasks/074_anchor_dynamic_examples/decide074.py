"""Frozen pilot decision, no target/confirmation label-based adaptation."""
from common074 import *
import run074 as r
def main():
 a=read(OUT/'pilot_analysis.json');m=a['final_metrics'];v=a['core_valid_final_metrics'];raw=a['raw_metrics']
 checks={
  'full_net_positive_vs_F4_F6':all(m['H6']['correct']>m[k]['correct'] for k in ['F4','F6']),
  'core_valid_net_positive_vs_F4_F6':all(v['H6']['correct']>v[k]['correct'] for k in ['F4','F6']),
  'not_worse_than_B':m['H6']['correct']>=m['B']['correct'] and v['H6']['correct']>=v['B']['correct'],
  'falseS_within_one':all(m['H6']['falseS']<=m[k]['falseS']+1 for k in ['B','F4','F6']),
  'raw_not_materially_worse':all(raw['H6']['correct']>=raw[k]['correct']-1 for k in ['B','F4','F6']),
 }
 attempts,_=r.attempt_state();used=sum(x['cost_cny'] for x in attempts)
 expected=used+sum((t['prompt_mean']*3+t['completion_mean']*9)/1e6*60 for t in a['tokens_by_arm'].values())
 d=dict(created_utc=now(),decision='confirm' if all(checks.values()) and expected+.75<=20 else 'stop',checks=checks,used_cny=used,expected_task_total_cny=expected,retry_margin_cny=.75,reason='hybrid_screen_failed' if not all(checks.values()) else ('budget_forecast' if expected+.75>20 else 'hybrid_signal'),pilot_analysis_sha256=sha(OUT/'pilot_analysis.json'),new_strategy_after_pilot=False)
 put(OUT/'confirmation_decision.json',d)
 if d['decision']=='confirm':
  aliases=[j for j in lines(OUT/'all_arm_jobs.jsonl') if j['stage']=='confirmation'];jobs=sorted({j['request_id']:j for j in aliases}.values(),key=lambda j:text_hash('074/order:'+j['request_id']))
  jl(OUT/'confirmation_aliases.jsonl',aliases);jl(OUT/'confirmation_jobs.jsonl',jobs)
  put(OUT/'confirmation_freeze.json',dict(stage='confirmation',created_utc=now(),source_freeze_sha256=sha(OUT/'freeze.json'),jobs_sha256=sha(OUT/'confirmation_jobs.jsonl'),aliases_sha256=sha(OUT/'confirmation_aliases.jsonl'),decision_file='confirmation_decision.json',decision_sha256=sha(OUT/'confirmation_decision.json')))
 print(canonical(d))
if __name__=='__main__':main()
