"""Focused executor checks. Never changes scores, GT, historical freezes or outputs."""
import ast,json,sqlite3,sys
from collections import Counter
import common103 as c
from prompt103 import messages
def main():
 count=0
 def check(ok,why):
  nonlocal count
  assert ok,why;count+=1
 for name in ['data_freeze.json','api_execution_freeze.json']:
  f=c.read(c.OUT/name)
  for rel,h in f['files'].items():check(c.sha(c.ROOT/rel)==h,rel)
 sample={r['id']:r for r in c.lines(c.PRIVATE/'sample240.jsonl')};train=c.lines(c.PRIVATE/'train512.jsonl');roles=c.read(c.OUT/'patient_roles.json')['patients']
 check(not {r['sid'] for r in train}&{r['sid'] for r in sample.values()},'patient isolation')
 check(not set(roles['confirmation'])&{r['sid'] for r in sample.values()},'no confirmation evaluation')
 check(Counter(r['GT'] for r in train)=={'Supported':320,'Not Supported':96,'Not Addressed':96},'training quotas')
 check(Counter(r['GT'] for r in train[:256])=={'Supported':160,'Not Supported':48,'Not Addressed':48},'nested256')
 check(len({r['id'] for r in train})==512,'unique training IDs')
 initial=c.lines(c.PRIVATE/'jobs_selected.jsonl');repair=c.lines(c.PRIVATE/'jobs_label_capacity.jsonl') if (c.PRIVATE/'jobs_label_capacity.jsonl').exists() else [];repeats=c.lines(c.PRIVATE/'jobs_repeats.jsonl') if (c.PRIVATE/'jobs_repeats.jsonl').exists() else [];jobs=initial+repair+repeats;seen=set();attempts=[]
 for j in jobs:
  r=sample[j['id']];check(j['body']['messages']==messages(r['claim'],r['reference'],j['mode']),'exact full reference task')
  check(c.digest(r['reference'])==r['reference_id'],'published reference source')
  check(c.digest(c.canonical(j['body']))==j['body_sha256'],'actual body SHA')
  check(j['request_id'] not in seen,'unique job');seen.add(j['request_id'])
 con=sqlite3.connect(c.PRIVATE/'budget.sqlite');db=con.execute('SELECT rid,num,charge,status,folder FROM attempts').fetchall();con.close()
 check(all(r[1]==1 for r in db),'no unintended duplicate dispatch/retry')
 requested={r[0] for r in db};required={j['request_id'] for j in ([j for j in initial if j['mode']=='native']+repair if repair else initial)+repeats}
 check(required<=requested<=seen,'all formal requests and only frozen requests; superseded128 diagnostics may be partial')
 check(all(r[3]==200 for r in db),'all API completed')
 check(sum(r[2] for r in db)<=30,'hard cap includes all attempts')
 for rid,num,charge,status,folder in db:
  receipt=c.read(c.ROOT/folder/'receipt.json');request=c.read(c.ROOT/folder/'request.json')
  check(receipt['request_sha256']==c.sha(c.ROOT/folder/'request.json'),'receipt binding');response=json.loads(receipt['transport']['body_text'])
  check(response['model']==request['job']['model'],'actual model identity')
  check(response['choices'][0]['finish_reason']=='stop' or (request['job']['mode']=='label' and request['job']['body']['max_tokens']==128),'no formal final truncation; original128 diagnostic retained')
 for p in c.TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'));count+=1
 frozen102=c.read(c.ROOT/'outputs/102_demo_relation/complete.json')
 check(c.sha(c.ROOT/'outputs/102_demo_relation/report.md')==frozen102['report_sha256'],'102 report unchanged')
 check(not (c.PRIVATE/'gpu_results').exists(),'GPU not started')
 c.put(c.OUT/'selfcheck.json',dict(utc=c.utc(),status='PASS',checks=count,independent_audit=False,data_isolation=True,full_reference=True,no_confirmation_evaluation=True,no_GPU_executed=True,api_cap_verified=True))
 print('PASS',count)
if __name__=='__main__':main()
