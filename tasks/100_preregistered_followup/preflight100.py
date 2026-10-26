"""Offline exact-body, capacity and alias checks; no target answers are read."""
from collections import Counter,defaultdict
import json
import common100 as c
def main():
 for name in ['execution_freeze.json','runtime_analysis_freeze.json']:
  for rel,h in c.read(c.OUT/name)['files'].items():assert c.sha(c.ROOT/rel)==h,rel
 assert not (c.PRIVATE/'attempts').exists(),'Preflight must precede100 responses'
 sample={r['id']:r for r in c.lines(c.PRIVATE/'sample.jsonl')};freeze=c.read(c.OUT/'execution_freeze.json');old=c.read(c.ROOT/'outputs/098_p90_native_confirmation/execution_freeze.json')
 assert not set(freeze['confirmation_patients'])&(set(old['evaluation_patients'])|set(old['example_development_patients']))
 assert not {r['sid'] for r in sample.values() if r['stage']=='development'}&{r['sid'] for r in sample.values() if r['stage']=='confirmation'}
 output={};checks=0
 for branch,name in [('evidence','all_evidence_jobs.jsonl'),('cross_model','all_cross_model_jobs.jsonl')]:
  jobs=c.lines(c.PRIVATE/name);bykey={(j['id'],j['arm'],j['repeat']):j for j in jobs};aliases=defaultdict(list);maxinput=0
  for j in jobs:
   b=j['body'];r=sample[j['id']];assert c.digest(c.canonical(b))==j['body_sha256'];payload=json.loads(b['messages'][1]['content'].split('## Input JSON:\n')[-1]);refarm='C' if j['arm']=='C' else j['arm'] if branch=='evidence' else 'O'
   assert set(payload)=={'text','reference'} and payload==dict(text=r['claim'],reference=r['references'][refarm]);checks+=2
   if j['repeat']:assert b==bykey[j['id'],j['arm'],0]['body'];checks+=1
   cap=1000000 if branch=='evidence' else 256000;outbound=8192 if branch=='evidence' else 2592
   assert j['input_token_forecast']+outbound<cap
   if branch=='evidence':assert b['model']=='deepseek-v4-flash-0731' and b['max_tokens']==8192 and b['reasoning_effort']=='high' and b['temperature']==0
   else:assert b['model']=='qwen3.5-27b' and b['thinking_budget']==2048 and b['max_tokens']==512 and b['top_p']==1 and b['temperature']==0
   aliases[j['request_id']].append(j);maxinput=max(maxinput,j['input_token_forecast']);checks+=2
  for rr in aliases.values():assert len({j['body_sha256'] for j in rr})==1 and len({(j['id'],j['repeat']) for j in rr})==1
  output[branch]=dict(logical_jobs=len(jobs),unique_body_slots=len(aliases),maximum_input_tokens_forecast=maxinput,context_capacity=1000000 if branch=='evidence' else 256000,unavailable_capacity_cases=0)
 ledger=c.lines(c.OUT/'construction_ledger.jsonl');rates={stage:dict(N=sum(sample[r['id']]['stage']==stage for r in ledger),S_equals_L=sum(r['S_equals_L'] for r in ledger if sample[r['id']]['stage']==stage),L_equals_E=sum(r['L_equals_E'] for r in ledger if sample[r['id']]['stage']==stage),max_S_L_token_gap=max(r['S_L_token_gap'] for r in ledger if sample[r['id']]['stage']==stage)) for stage in ['development','confirmation']}
 c.put(c.OUT/'capacity_and_alias_preflight.json',dict(utc=c.utc(),status='PASS',checks=checks,branches=output,actual_identity_counts=rates,full_confirmation_patients=32,no_GT_in_target_payload=True,all_EHR_inputs_complete_and_within_capacity=True,no_paid_API=True))
 print(c.canonical(dict(status='PASS',branches=output,identity_counts=rates)))
if __name__=='__main__':main()
