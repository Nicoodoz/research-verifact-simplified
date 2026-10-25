"""Before API: verify annotation sources, one-variable intervention and budget."""
import ast,json
from common075 import *
import run075 as r
def main():
 r.check_frozen('pilot');n=1
 for rel in ['outputs/073_clinical_example_matching/manifest.json','outputs/074_anchor_dynamic_examples/manifest.json']:
  for p,h in read(ROOT/rel)['files'].items():assert sha(ROOT/p)==h,p;n+=1
 targets=lines(OUT/'target_blind.jsonl');jobs=lines(OUT/'all_arm_jobs.jsonl');by={(j['id'],j['arm']):j for j in jobs}
 first_system=next(j['body']['messages'][0]['content'] for j in lines(ROOT/'outputs/071_judge_icl_feasibility/main_jobs.jsonl') if j['arm']=='E')
 suffixes=set()
 for t in targets:
  b,f,x=[by[t['id'],arm]['body'] for arm in ['B','F4','R4']]
  assert f['messages'][0]['content']==first_system;n+=1
  assert x['messages'][0]['content'].startswith(f['messages'][0]['content']);n+=1
  suffix=x['messages'][0]['content'][len(f['messages'][0]['content']):];suffixes.add(suffix)
  for arm in ['B','F4','R4']:
   j=by[t['id'],arm];q=j['body'];assert j['body_sha256']==digest(q) and q['model']==r.MODEL and q['enable_thinking'] and q['reasoning_effort']=='high';n+=1
   assert json.loads(q['messages'][-1]['content'])==dict(proposition=t['claim'],reference=t['reference']);n+=1
   assert {k:v for k,v in q.items() if k!='messages'}=={k:v for k,v in b.items() if k!='messages'};n+=1
  # Only system teaching material changes; the target and message roles do not.
  assert f['messages'][1:]==x['messages'][1:]==b['messages'][1:];n+=1
 assert len(suffixes)==1 and 'label_scores' not in next(iter(suffixes));n+=1
 checks=read(OUT/'annotation_evidence_checks.json');assert len(checks)==5 and all(x['matched'] for x in checks);n+=1
 assert len(r.jobs_for('pilot'))==108;n+=1
 # Use historic observed prompt-token / serialized-character ratio, same frozen Judge.
 pred=lines(ROOT/'outputs/073_clinical_example_matching/pilot_predictions.jsonl')+lines(ROOT/'outputs/073_clinical_example_matching/confirmation_predictions.jsonl')
 old={(j['id'],j['arm']):j for j in lines(ROOT/'outputs/073_clinical_example_matching/all_arm_jobs.jsonl')}
 ratio=max(x['usage']['prompt_tokens']/len(canonical(old[x['id'],x['arm']]['body'])) for x in pred if x['arm'] in ['B','F4'])
 output_mean={arm:sum(x['usage']['completion_tokens'] for x in pred if x['arm']==arm)/sum(x['arm']==arm for x in pred) for arm in ['B','F4']}
 forecast=sum((len(canonical(j['body']))*ratio*3+output_mean['B' if j['arm']=='B' else 'F4']*9)/1e6 for j in jobs)
 assert forecast+.75<20;n+=1
 for p in TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'));n+=1
 put(OUT/'preflight_checks.json',dict(status='PASS',checks=n,expected_cny=forecast,cap_cny=20,verified_source_quotes=5,old_F4_system_exact=True,only_static_annotation_suffix_added=True,no_annotation_scores=True,historical073_074_files_unchanged=True,price_checked_utc=now(),price_url='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',price_cny_per_million=[3,9]))
 print(canonical(dict(status='PASS',checks=n,expected_cny=forecast,annotation_characters=len(next(iter(suffixes))))))
if __name__=='__main__':main()
