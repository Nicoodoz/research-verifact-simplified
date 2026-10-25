"""Independent raw receipt decoding/accounting for019/020, without task parsers."""
from pathlib import Path
from collections import Counter
import json,csv,hashlib,math,sys
ROOT=Path.cwd();DEST=Path(sys.argv[1])
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def fp(v):return hashlib.sha256(canon(v).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(scores,lam):
 labels=['Not Supported','Not Addressed','Supported']
 return max(labels,key=lambda k:max(scores[k]/100,1e-6)*(math.exp(lam) if k=='Supported' else 1))
results={}
for task in ['019_support_boundary_screen','020_lambda2_patient_validation']:
 o=ROOT/'outputs'/task;ledger=read(o/'live_ledger.json');known=unknown=0.;physical=set();answers={};status=Counter();total_attempts=0;times=[];byphase={}
 is19=task.startswith('019')
 for phase,state in ledger['phases'].items():
  prep=o/((phase+'/preparation') if is19 else {'new10_embedding':'new10/preparation_002','new10_rerank':'new10/candidates_001','new10_judge':'new10/base_preparation_001'}[phase])
  jobs={j['request_id']:j for j in jl(prep/'jobs.jsonl')};n=0
  for rid,progress in state['jobs'].items():
   assert progress['status']=='received';j=jobs[rid];b=j['body'];success=0
   for ptr in progress['receipts']:
    p=o/ptr['file'];assert sha(p)==ptr['sha256'];assert str(p) not in physical;physical.add(str(p))
    r=read(p);tr=r['transport'];assert r['job_sha256']==fp(j) and r['actual_body']==b and r['actual_body_sha256']==fp(b)
    assert r['provider']=='siliconflow' and r['account']=='account_2'
    status[str(tr['http_status'])]+=1;times.append(tr['started_utc']);total_attempts+=1
    v=json.loads(tr['body_text']) if tr['body_text'].lstrip().startswith('{') else {}
    u=v.get('usage',{});chat=is19 or j['kind']=='chat'
    if tr['http_status']==200:
     assert v.get('model',b['model'])==b['model'];success+=1;n+=1
     if chat:
      pi,po=u['prompt_tokens'],u['completion_tokens'];assert u.get('total_tokens',pi+po)==pi+po
      fee=(pi*3+po*9)/1e6
      ch=v['choices'][0];assert len(v['choices'])==1 and ch['finish_reason']=='stop' and not ch['message'].get('reasoning_content')
      assert u.get('completion_tokens_details',{}).get('reasoning_tokens',0)==0
      ans=json.loads(ch['message']['content']);assert ans['verdict'] in ['Supported','Not Supported','Not Addressed']
      if j['arm']=='S':
       sc=ans['label_scores'];assert set(sc)=={'Supported','Not Supported','Not Addressed'} and all(type(x)is int and 0<=x<=100 for x in sc.values()) and sum(sc.values())==100
      answers[(j.get('proposition_id',rid),j['arm'],j['repeat'])]=ans
     else:
      n_tokens=u.get('prompt_tokens',u.get('total_tokens'))
      if n_tokens is None:n_tokens=v.get('meta',{}).get('billed_units',{}).get('input_tokens')
      if n_tokens is None:n_tokens=v.get('meta',{}).get('tokens',{}).get('input_tokens')
      assert isinstance(n_tokens,int);fee=n_tokens*.07/1e6
     known+=fee
    else:
     assert chat
     fee=((len(canon(b).encode())+2000)*3+b['max_tokens']*9)/1e6;unknown+=fee
    assert abs(fee-ptr['charge_cny'])<1e-10
   assert success==1
   for a in progress.get('unreceipted_attempts',[]):
    fee=((len(canon(b).encode())+2000)*3+b['max_tokens']*9)/1e6
    assert abs(a['reserved_cny']-fee)<1e-10;unknown+=fee;total_attempts+=1
  byphase[phase]=dict(jobs=len(jobs),success=n)
 # Enumerate primary live receipts; recovered backups remain snapshots, not extra attempts.
 disk={str(p) for phase in ledger['phases'] for p in (o/(phase+'/live' if is19 else phase+'/live')).glob('receipt_*.json')}
 assert disk==physical,(task,len(disk),len(physical))
 assert abs(known+unknown-ledger['used_or_reserved_cny'])<1e-8
 counted={};decoded=0
 for rep in ([0] if is19 else [0,1]):
  path=o/('selection/analysis_001' if is19 else 'analysis_001')/f'predictions_r{rep}.csv'
  pred=rows(path);assert len(pred)==(650 if is19 else 879)
  for row in pred:
   b=answers[row['proposition_id'],'B',rep];s=answers[row['proposition_id'],'S',rep]
   assert row['B']==b['verdict'] and row['V_raw']==s['verdict']
   for lam in ([0,.5,1,1.5,2,3,4] if is19 else [0,2]):
    key=('U0' if lam==0 else f'U_lambda_{lam:g}') if is19 else f'U{lam}'
    assert row[key]==decode(s['label_scores'],lam);decoded+=1
  methods=['B','U0','U_lambda_2','O'] if is19 else ['B','U0','U2','O']
  counted[str(rep)]={m:dict(correct=sum(r[m]==r['human_gt'] for r in pred),false_S=sum(r[m]=='Supported' and r['human_gt']!='Supported' for r in pred)) for m in methods}
 assert read(o/'authority.json')['created_utc']<min(times)
 results[task]=dict(receipts=len(physical),attempts=total_attempts,status_counts=status,phases=byphase,known_estimate_cny=known,unknown_reserved_cny=unknown,total_cny=known+unknown,decoded_labels=decoded,counts=counted,authority_before_first_send=True,first_send_utc=min(times),last_send_utc=max(times))
DEST.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(results,ensure_ascii=False))
