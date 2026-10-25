"""Independent017 raw receipts, costs, stable outcomes and frozen-scope checks. No task imports."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timedelta,timezone
import json,csv,hashlib,sys,math
ROOT=Path.cwd();O=ROOT/'outputs/017_verification_supervised_evidence_utility'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def fp(v):return hashlib.sha256(canon(v).encode()).hexdigest()
jobs={j['request_id']:j for j in jl(O/'preparation_001/jobs.jsonl')}
inputs=jl(O/'preparation_001/inputs.jsonl');assign=rows(O/'preparation_001/assignments.csv')
cohort={r['proposition_id']:r for r in rows(O/'evaluation_cohort.csv')}
ats=rows(O/'analysis_001/attempts.csv')
files={str((ROOT/a['receipt']).resolve()).lower() for a in ats}
assert files=={str(p.resolve()).lower() for p in (O/'live/headroom').glob('receipt_*.json')}
assert len(files)==len(ats)==1574
success={};known=unknown=0.;usage=Counter();status=Counter();errors=[];providers=set()
for a in ats:
 p=ROOT/a['receipt'];assert sha(p)==a['sha256'];r=read(p);j=jobs[a['request_id']];tr=r['transport'];b=r['actual_body']
 assert r['original_job_sha256']==fp(j) and r['actual_body_sha256']==fp(b)
 assert b==j['body'] and r['provider']=='siliconflow' and r['account']=='account_2'
 status[str(tr['http_status'])]+=1;assert str(tr['http_status'])==a['http_status']
 n=json.loads(tr['body_text'])
 if tr['http_status']==200:
  u=n['usage'];pi,po=u['prompt_tokens'],u['completion_tokens'];assert pi+po==u['total_tokens']
  hit=u.get('prompt_cache_hit_tokens',u.get('prompt_tokens_details',{}).get('cached_tokens',0)) or 0
  hr=datetime.fromisoformat(tr['ended_utc']).astimezone(timezone(timedelta(hours=8))).hour
  fee=((pi-hit)*3+hit*.3+po*9)*(.5 if 2<=hr<8 else 1)/1e6;known+=fee
  usage['input_tokens']+=pi;usage['output_tokens']+=po
  assert n['model']==b['model'] and len(n['choices'])==1
  ch=n['choices'][0];assert ch['finish_reason']=='stop' and not ch['message'].get('reasoning_content')
  assert u.get('completion_tokens_details',{}).get('reasoning_tokens',0)==0
  label=json.loads(ch['message']['content'])['verdict'];assert label in ('Supported','Not Supported','Not Addressed')
  assert a['request_id'] not in success;success[a['request_id']]=label
 else:
  assert tr['http_status']==400
  fee=((len(canon(b).encode())+2000)*3+b['max_tokens']*9)/1e6;unknown+=fee
  errors.append(dict(request_id=a['request_id'],body_sha256=fp(b),error=n))
 assert abs(fee-float(a['charge_cny']))<1e-10
assert len(success)==len(jobs)==1572
labels={};seenbody={}
for a in assign:
 rid=a['request_id'];j=jobs[rid];k=(a['proposition_id'],a['arm'],int(a['repeat']))
 assert k not in labels;labels[k]=success[rid]
 assert a['body_sha256']==fp(j['body']) and ':r'+a['repeat']+':' in rid
 unique=(a['repeat'],a['body_sha256']);assert seenbody.setdefault(unique,rid)==rid
assert len(labels)==1920
expectedids={x['proposition_id'] for x in inputs};assert set(cohort)==expectedids
plan=read(O/'preparation_001/sampling.json')
assert not set(plan['train_patients'])&set(plan['selection_patients'])
assert Counter((x['subject_id'],x['author_type']) for x in inputs)==Counter({(p,a):8 for p in plan['train_patients']+plan['selection_patients'] for a in ['llm','human']})
arms=('baseline','c48_local','c48_crossnote','wide_swap','wide_relevance');swaps=arms[1:4]
stable_wrong=stable_correct=flips=rescue=harm=nonzero=trainpairs=eligible=0
rescue_sids=set();rescue_auth=Counter();samepool=0;samepool_sids=set();train_sids=set();by_author={}
core=Counter();swaps_checked=0
casecsv={r['proposition_id']:r for r in rows(O/'analysis_001/cases.csv')}
for item in inputs:
 pid=item['proposition_id'];gt=cohort[pid]['human_gt'];author=item['author_type']
 assert cohort[pid]['invalid']=='False' and cohort[pid]['proposition_type']=='claim'
 before=set(item['baseline']['selected_ids'])
 for arm in swaps:
  v=item['interventions'][arm]
  if v['eligible']:
   after=set(v['selected_ids']);assert after-before=={v['added']} and before-after=={v['removed']}
   assert len(before)==len(after)<=16 and v['body_characters']<=8000
   assert .9<=v['body_characters']/item['baseline']['body_characters']<=1.1
   assert len(v['features_in'])==len(v['features_out'])==8;swaps_checked+=1
 for arm in arms:
  b0=jobs[next(a['request_id'] for a in assign if a['proposition_id']==pid and a['arm']==arm and a['repeat']=='0')]['body']
  b1=jobs[next(a['request_id'] for a in assign if a['proposition_id']==pid and a['arm']==arm and a['repeat']=='1')]['body']
  assert b0==b1 and b0['enable_thinking']==False and b0['temperature']==0 and b0['max_tokens']==2048
  payload=json.loads(b0['messages'][1]['content']);assert set(payload)=={'proposition','reference'}
  assert payload['proposition']==item['text'] and payload['reference']==item['interventions'][arm]['reference']
  for repeat in (0,1):core[(repeat,author,arm)]+=labels[pid,arm,repeat]==gt
 b=[labels[pid,'baseline',k] for k in (0,1)];stable=b[0]==b[1];wrong=stable and b[0]!=gt;correct=stable and b[0]==gt
 stable_wrong+=wrong;stable_correct+=correct;flips+=not stable
 cr=ch=sp=False
 for arm in swaps:
  v=[labels[pid,arm,k] for k in (0,1)];valid=item['interventions'][arm]['eligible']
  rr=wrong and v[0]==v[1]==gt and valid;hh=correct and v[0]==v[1] and v[0]!=gt and valid
  cr|=rr;ch|=hh
  if arm!='wide_swap':sp|=rr
  if rr or hh:
   nonzero+=1
   if item['split']=='train':trainpairs+=1;train_sids.add(item['subject_id'])
 eligible+=any(item['interventions'][a]['eligible'] for a in swaps)
 rescue+=cr;harm+=ch;samepool+=sp
 if cr:rescue_sids.add(item['subject_id']);rescue_auth[author]+=1
 if sp:samepool_sids.add(item['subject_id'])
 for key,val in [('stable_wrong',wrong),('stable_correct',correct),('baseline_label_flip',not stable),('rescued',cr),('harmed',ch)]:
  assert casecsv[pid][key]==str(val)
for r in rows(O/'analysis_001/core_results.csv'):assert core[int(r['repeat']),r['author'],r['arm']]==int(r['correct'])
conditions=dict(complete=len(labels)==1920,eligible=eligible>=144,stable_error_coverage=stable_wrong>=24,stable_correct_coverage=stable_correct>=80,
 substantial_rescue=rescue>=max(12,math.ceil(.25*stable_wrong)),rescue_patients=len(rescue_sids)>=4,both_authors_rescue=all(rescue_auth[a]>=3 for a in ['llm','human']),
 same_pool_rescue=samepool>=6 and len(samepool_sids)>=3,harm_rate=harm<=.2*stable_correct,baseline_flip_rate=flips<=.15*len(inputs),
 train_pairs=trainpairs>=16 and len(train_sids)>=3)
assert conditions==read(O/'analysis_001/gate.json')['conditions']
prep=read(O/'preparation_001/manifest.json')['created_utc'];auth=read(O/'authority_001.json')['created_utc'];first=min(a['started_utc'] for a in ats)
assert prep<auth<first
analysis_plan=read(O/'analysis_plan_001.json')['created_utc']
assert not (O/'learning_001').exists() and not (O/'confirmation_001').exists()
summary=dict(status='PASS',receipt_attempts=len(ats),status_counts=status,valid_responses=len(success),logical_conditions=len(labels),claims=len(inputs),
 stable_wrong=stable_wrong,stable_correct=stable_correct,baseline_flips=flips,stable_rescue=rescue,stable_harm=harm,nonzero_events=nonzero,training_events=trainpairs,
 eligible_cases=eligible,legal_single_swaps_checked=swaps_checked,gate_conditions=conditions,gate_passed=all(conditions.values()),
 known_usage_cny=known,unknown_reserved_cny=unknown,total_cny=known+unknown,actual_usage=usage,
 timeline=dict(preparation=prep,authority=auth,first_send=first,analysis_code_registered=analysis_plan,last_return=max(a['ended_utc'] for a in ats)),
 failed_responses=errors,external_calls=0)
dest=Path(sys.argv[1]);dest.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
