"""One frozen pilot decision; no post-result annotation rewriting."""
from common075 import *
import run075 as r
def main():
 a=read(OUT/'pilot_analysis.json');m=a['final_metrics'];v=a['core_valid_final_metrics'];raw=a['raw_metrics']
 checks={
  'increment_vs_F4':raw['R4']['correct']>=raw['F4']['correct'] and m['R4']['correct']>=m['F4']['correct'] and (raw['R4']['correct']>raw['F4']['correct'] or m['R4']['correct']>m['F4']['correct']),
  'core_valid_same_direction':v['R4']['correct']>=v['F4']['correct'] and (raw['R4']['correct']>raw['F4']['correct'] or v['R4']['correct']>v['F4']['correct']),
  'not_below_B':m['R4']['correct']>=m['B']['correct'] and v['R4']['correct']>=v['B']['correct'] and raw['R4']['correct']>=raw['B']['correct'],
  'falseS_within_one':all(m['R4']['falseS']<=m[k]['falseS']+1 for k in ['B','F4'])
 }
 attempts,_=r.attempt_state();used=sum(x['cost_cny'] for x in attempts)
 expected=used+sum((t['prompt_mean']*3+t['completion_mean']*9)/1e6*60 for t in a['tokens_by_arm'].values())
 d=dict(created_utc=now(),decision='confirm' if all(checks.values()) and expected+.75<=20 else 'stop',checks=checks,used_cny=used,expected_task_total_cny=expected,retry_margin_cny=.75,reason='annotation_screen_failed' if not all(checks.values()) else ('budget_forecast' if expected+.75>20 else 'annotation_increment'),pilot_analysis_sha256=sha(OUT/'pilot_analysis.json'),annotations_revised_after_pilot=False)
 put(OUT/'confirmation_decision.json',d)
 if d['decision']=='confirm':
  aliases=[j for j in lines(OUT/'all_arm_jobs.jsonl') if j['stage']=='confirmation'];jobs=sorted({j['request_id']:j for j in aliases}.values(),key=lambda j:text_hash('075/order:'+j['request_id']))
  jl(OUT/'confirmation_aliases.jsonl',aliases);jl(OUT/'confirmation_jobs.jsonl',jobs)
  put(OUT/'confirmation_freeze.json',dict(stage='confirmation',created_utc=now(),source_freeze_sha256=sha(OUT/'freeze.json'),jobs_sha256=sha(OUT/'confirmation_jobs.jsonl'),aliases_sha256=sha(OUT/'confirmation_aliases.jsonl'),decision_file='confirmation_decision.json',decision_sha256=sha(OUT/'confirmation_decision.json')))
 print(canonical(d))
if __name__=='__main__':main()
