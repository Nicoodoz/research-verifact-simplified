"""Offline invariants, immutable history and realistic task forecast."""
import ast,collections,json
from common074 import *
import run074 as r
from prepare074 import tags,clean
def main():
 f=r.check_frozen('pilot');n=0
 old=read(ROOT/'outputs/073_clinical_example_matching/manifest.json')
 for rel,h in old['files'].items():assert sha(ROOT/rel)==h,rel;n+=1
 blind=lines(OUT/'target_blind.jsonl');gold=lines(OUT/'target_gt.jsonl');pool=lines(OUT/'example_pool.jsonl')
 assert len(blind)==len(gold)==96 and len({x['id'] for x in blind})==96;n+=1
 old_ids=set()
 for rel in ['outputs/072_adaptive_judge_examples/target_blind.jsonl','outputs/073_clinical_example_matching/target_blind.jsonl']:old_ids|={x['id'] for x in lines(ROOT/rel)}
 assert not old_ids&{x['id'] for x in blind};n+=1
 assert not {x['sid'] for x in blind}&{x['sid'] for x in pool};n+=1
 jobs=lines(OUT/'all_arm_jobs.jsonl');by={(x['id'],x['arm']):x for x in jobs};sels={x['id']:x for x in lines(OUT/'selections.jsonl')}
 for t in blind:
  for arm in ['B','F4','F6','H6']:
   j=by[t['id'],arm];b=j['body']
   assert j['body_sha256']==digest(b) and b['model']==r.MODEL and b['enable_thinking'] and b['reasoning_effort']=='high';n+=1
   assert json.loads(b['messages'][-1]['content'])==dict(proposition=t['claim'],reference=t['reference']);n+=1
  p4=by[t['id'],'F4']['body']['messages'][0]['content']
  for arm in ['F6','H6']:
   text=by[t['id'],arm]['body']['messages'][0]['content'];assert text.startswith(p4) and len(text)>len(p4);n+=1
  s=sels[t['id']];assert .9<=s['added_length_ratio']<=1.1 and len(set(s['dynamic_ids']))==2;n+=1
 unique=r.jobs_for('pilot');aliases=lines(OUT/'pilot_aliases.jsonl');assert len(unique)==len({x['body_sha256'] for x in aliases});n+=1
 assert 'time' in tags('on [CLINICAL_LITERAL_REMOVED]') and '2153' in clean('on [CLINICAL_LITERAL_REMOVED]');n+=1
 assert {'causal','quantity','negation'}<=tags('No improvement due to 5 mg medication.');n+=1
 assert r.CAP==20 and r.charge({'http_status':0},.2)==.2;n+=1
 # Forecast from the entire 073 B/F4 observed usage, scaled by actual serialized body length.
 pred=lines(ROOT/'outputs/073_clinical_example_matching/pilot_predictions.jsonl')+lines(ROOT/'outputs/073_clinical_example_matching/confirmation_predictions.jsonl')
 j73={(x['id'],x['arm']):x for x in lines(ROOT/'outputs/073_clinical_example_matching/all_arm_jobs.jsonl')}
 ratio=max(x['usage']['prompt_tokens']/len(canonical(j73[x['id'],x['arm']]['body'])) for x in pred if x['arm'] in ['B','F4'])
 means={a:sum(x['usage']['completion_tokens'] for x in pred if x['arm']==a)/sum(x['arm']==a for x in pred) for a in ['B','F4']}
 forecast=sum((len(canonical(j['body']))*ratio*3+means['B' if j['arm']=='B' else 'F4']*9)/1e6 for j in jobs)
 assert forecast+.75<=20,forecast;n+=1
 for p in TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'));n+=1
 put(OUT/'preflight_checks.json',dict(status='PASS',checks=n,prior073_manifest_verified=True,expected_cny=forecast,retry_reserve=.75,budget_cap=20,price_url='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',price_checked_utc=now(),billing='3/9 peak uncached CNY per million; actual usage/unknown and inflight reserved at each send'))
 print(canonical(dict(status='PASS',checks=n,expected_cny=forecast,max_inflight_per_request=max(r.bound(j['body']) for j in jobs))))
if __name__=='__main__':main()
