"""Independent raw-receipt/count/cost/timeline audit; no executor cost or analysis import."""
from pathlib import Path
import json,csv,hashlib,collections,datetime,sys
ROOT=Path.cwd();O=ROOT/'outputs/016_disagreement_triggered_review_validation'
A=O/'completion_002/analysis_001'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def csvread(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
jobs={}
for p in O.rglob('jobs.jsonl'):
 if 'verification' in str(p):continue
 for line in p.read_text(encoding='utf-8').splitlines():
  j=json.loads(line);rid=j['request_id']
  if rid in jobs:assert jobs[rid]['body']==j['body']
  jobs[rid]=j
for p in [O/'real_request_check_001/request.json',O/'aliyun_real_request_check_001/job.json']:
 j=read(p);jobs[j['request_id']]=j
j=dict(request_id='service_check_001',kind='chat',role='service_probe',body=read(O/'service_check_001/request.json'))
jobs[j['request_id']]=j
ats=csvread(A/'attempts.csv');prov=csvread(A/'canonical_provenance.csv');trans=csvread(A/'transitions.csv')
listed={str((ROOT/x['receipt']).resolve()).lower() for x in ats if x['receipt']}
disk={str(p.resolve()).lower() for p in O.rglob('receipt*.json') if 'verification' not in str(p)}
assert listed==disk,(len(listed),len(disk),disk-listed,listed-disk)
assert len(listed)==sum(bool(x['receipt']) for x in ats)
known=unknown=0.;statuses=collections.Counter();success=collections.Counter()
for x in ats:
 j=jobs[x['request_id']];b=j['body'];statuses[x['http_status']]+=1
 if x['receipt']:
  p=ROOT/x['receipt'];assert sha(p)==x['sha256'];r=read(p);t=r.get('transport',r)
  assert str(t['http_status'])==x['http_status']
 else:t={}
 native=json.loads(t['body_text']) if t.get('body_text','').startswith('{') else {}
 u=native.get('usage',{})
 is_unknown=False
 if 'prompt_tokens' in u or 'total_tokens' in u or native.get('meta'):
  if j['kind']=='chat':
   pin,pout=u['prompt_tokens'],u['completion_tokens'];assert pin+pout==u['total_tokens']
   if 'qwen' in b['model'].lower():fee=(pin*3+pout*12)/1e6
   else:
    hit=u.get('prompt_cache_hit_tokens',u.get('prompt_tokens_details',{}).get('cached_tokens',0)) or 0
    hour=datetime.datetime.fromisoformat(t['ended_utc']).astimezone(datetime.timezone(datetime.timedelta(hours=8))).hour
    fee=((pin-hit)*3+hit*.3+pout*9)*(.5 if 2<=hour<8 else 1)/1e6
  else:
   n=u.get('prompt_tokens',u.get('total_tokens'))
   if n is None:n=native.get('meta',{}).get('billed_units',{}).get('input_tokens')
   if n is None:n=native.get('meta',{}).get('tokens',{}).get('input_tokens')
   assert isinstance(n,int) and n>0;fee=n*.07/1e6
 else:
  is_unknown=True
  if j['kind']=='chat':fee=((len(canon(b).encode('utf-8'))+2000)*3+b['max_tokens']*(12 if j.get('role')=='qwen' else 9))/1e6
  elif j['kind']=='embedding':fee=(sum(len(t.encode('utf-8'))+128 for t in b['input'])+2000)*.07/1e6
  else:fee=(sum(len(t.encode('utf-8'))+len(b['query'].encode('utf-8'))+256 for t in b['documents'])+2000)*.07/1e6
 assert abs(fee-float(x['charge_cny']))<1e-10,(x['request_id'],fee,x['charge_cny'])
 if is_unknown:unknown+=fee
 else:known+=fee
 if x['http_status']=='200':success[x['request_id']]+=1
assert max(success.values())==1
labels={};providers=collections.Counter()
for x in prov:
 p=ROOT/x['receipt'];assert sha(p)==x['receipt_sha256'];r=read(p);n=json.loads(r['transport']['body_text'])
 j=jobs[x['request_id']];assert hashlib.sha256(canon(j['body']).encode()).hexdigest()==x['body_sha256']
 assert n['model']==j['body']['model'];assert len(n['choices'])==1
 c=n['choices'][0];assert c['finish_reason']=='stop';msg=c['message'];assert not msg.get('reasoning_content')
 assert n['usage'].get('completion_tokens_details',{}).get('reasoning_tokens',0)==0
 ans=json.loads(msg['content']);assert ans['verdict'] in ('Supported','Not Supported','Not Addressed')
 key=(x['proposition_id'],x['role']);assert key not in labels;labels[key]=ans['verdict']
 if x['role']=='qwen':providers[x['provider']]+=1
cohort=csvread(O/'stage1/preparation_002/cohort.csv')
assert {x['proposition_id'] for x in cohort}=={x['proposition_id'] for x in trans}
assert len(cohort)==601
correct=collections.Counter();dis=set();by_author=collections.defaultdict(collections.Counter)
for x in trans:
 pid=x['proposition_id'];gt=x['human_gt']
 for role in ('v4_first','qwen'):assert x[role]==labels[pid,role]
 differ=labels[pid,'v4_first']!=labels[pid,'qwen']
 if differ:dis.add(pid)
 for raw,workflow in [('v4_repeat','cross_repeat'),('independent_review','cross_review')]:
  if differ:
   assert labels[pid,raw]==x[raw]==x[workflow]
  else:
   assert (pid,raw) not in labels and x[raw]=='' and x[workflow]==labels[pid,'v4_first']
 for role in ('v4_first','qwen','cross_repeat','cross_review'):
  correct[role]+=x[role]==gt;by_author[x['author_type']][role]+=x[role]==gt
assert correct==dict(v4_first=446,qwen=457,cross_repeat=451,cross_review=452)
assert len(dis)==92 and len(labels)==1386
assert providers==dict(siliconflow=127,aliyun=474)
timeline={}
for phase in ['base','review']:
 relevant=[x for x in ats if x['epoch']=='completion_002' and x['phase']==phase]
 freeze=read(O/'completion_002'/phase/'manifest.json')['created_utc'];start=min(x['started_utc'] for x in relevant)
 assert freeze<start
 timeline[phase]={'frozen_utc':freeze,'first_send_utc':start,'last_return_utc':max(x['ended_utc'] for x in relevant)}
assert read(O/'completion_002/protocol_amendment.json')['created_utc']<timeline['base']['first_send_utc']
assert timeline['base']['last_return_utc']<timeline['review']['first_send_utc']
assert read(O/'stage1/preparation_002/manifest.json')['created_utc']<min(x['started_utc'] for x in ats if x['started_utc'])
summary=dict(status='PASS',attempt_records=len(ats),physical_receipts=len(disk),unreceipted_reservations=len(ats)-len(disk),status_counts=statuses,
 canonical_judge_answers=len(labels),disagreements=len(dis),qwen_providers=providers,correct=correct,correct_by_author=dict(by_author),
 known_usage_or_determined_cny=known,unknown_reserved_cny=unknown,total_cny=known+unknown,timeline=timeline,
 external_calls=0,notes='Independent standard-library parsing; no executor normalizer, cost function or analysis imported. Full metric replay separately invokes unified evaluation.')
dest=Path(sys.argv[1]);dest.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
