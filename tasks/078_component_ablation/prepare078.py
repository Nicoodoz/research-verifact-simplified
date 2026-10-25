"""Bind old receipts, build missing factorial cells, freeze before new task078 API."""
import copy,csv,statistics
from collections import Counter,defaultdict
import common078 as c
def main():
 source={};checks=0
 def bind(p):source[str(p.relative_to(c.ROOT)).replace('\\','/')]=c.sha(p)
 for p in [c.TASK/'README.md',c.TASK/'common078.py',c.TASK/'prepare078.py',c.TASK/'run078.py',c.OUT/'inventory.json',c.OUT/'primary_blind.jsonl',c.OUT/'bridge_blind.jsonl',c.OUT/'f4_blind.jsonl']:bind(p)
 primary=c.lines(c.OUT/'primary_blind.jsonl');bridge=c.lines(c.OUT/'bridge_blind.jsonl');f4=c.lines(c.OUT/'f4_blind.jsonl');ids={x['id'] for x in primary};by={x['id']:x for x in primary}
 alias=[];new=[];cache=[];native={};usage=defaultdict(list)
 for task,folder in [('052','052_first_tier_validation'),('053','053_thinking_prior_validation'),('071','071_judge_icl_feasibility')]:
  for p in sorted((c.ROOT/'outputs'/folder/'attempts').glob('*/request.json')):
   rq=c.read(p);j=rq['job'];rp=p.parent/'receipt.json'
   if j.get('id') not in ids or not rp.exists():continue
   rc=c.read(rp);assert rc['request_sha256']==c.sha(p);tr=rc['transport']
   if tr['http_status']!=200:continue
   # Ignore all preflight/repeat/recovery alternative answers, except fixed 071 E below.
   if task in ['052','053']:
    if rq.get('stage') not in ['main','qwen']:continue
    cond=j['condition'];sc=j['scored'];th=j['thinking']
   else:
    if j.get('arm')!='E':continue
    cond='F4';sc=th=True
   z=c.c53.parse_response(tr,sc,th);assert z.get('model_returned')==j['body']['model'];key=(task,j['id'],cond)
   assert key not in native,key
   rec=dict(id=j['id'],source_task=task,condition=cond,body=j['body'],body_sha256=c.digest(j['body']),parsed=z,request_source=p.relative_to(c.ROOT).as_posix(),receipt_source=rp.relative_to(c.ROOT).as_posix(),request_id=j['request_id'])
   native[key]=rec;bind(p);bind(rp);checks+=2
   if z.get('usage'):usage[cond].append(z['usage'])
 sysE=next(r['body']['messages'][0]['content'] for (t,i,a),r in native.items() if a=='F4')
 def add(x,arm,scored,thinking,reference,oldkey=None,system=None):
  nonlocal checks
  b=c.c53.judge_body(x['claim'],reference,scored,thinking)
  if system:b['messages'][0]['content']=system
  rid='078_'+arm+'_'+c.digest(x['id'])[:24];j=dict(request_id=rid,id=x['id'],sid=x['sid'],arm=arm,stage='main',body=b,body_sha256=c.digest(b),scored=scored,thinking=thinking)
  if oldkey in native:
   rr=native[oldkey];assert c.canon(rr['body'])==c.canon(b),(arm,x['id'],'body mismatch');cache.append(dict(arm=arm,**rr));mode='reused';checks+=1
  else:new.append(j);mode='new'
  alias.append(dict(id=x['id'],sid=x['sid'],arm=arm,body_sha256=c.digest(b),request_id=rid,mode=mode))
 for x in primary:
  for arm,cond,sc,th in [('NS','N-S',True,False),('TS','T-S',True,True),('NV','N-V',False,False),('TV','T-V',False,True)]:add(x,arm,sc,th,x['reference'],(x['source_task'],x['id'],cond))
 for x in bridge:
  assert c.sha(c.OUT/'bridge_blind.jsonl')==source['outputs/078_component_ablation/bridge_blind.jsonl']
  import hashlib
  assert hashlib.sha256(x['author_reference'].encode()).hexdigest()==x['author_reference_id']
  for arm,th in [('RN',False),('RT',True)]:add(x,arm,True,th,x['author_reference'])
 for x in f4:add(x,'F4',True,True,x['reference'],('071',x['id'],'F4'),sysE)
 # Cached Qwen and patient-out Gate models; no new fits or Qwen API.
 gm_path=c.ROOT/'outputs/052_first_tier_validation/gate_patient_out_mapping.json';gm=c.read(gm_path)['models'];bind(gm_path);gate=[];models={}
 for x in primary:
  mp=gm[x['sid']];p=c.ROOT/mp['source'];assert c.sha(p)==mp['sha256'];m=c.read(p);assert x['sid'] not in mp['training_patients'];assert x['sid'] not in m['final_fit']['training_patients'];assert x['sid'] in m['excluded_patients'];bind(p)
  for fold in m.get('inner_folds',[]):
   if isinstance(fold,dict):assert x['sid'] not in fold.get('training_patients',[])
  models[x['sid']]=dict(source=mp['source'],sha256=c.sha(p),threshold=m['threshold'],final_fit=m['final_fit'],excluded_patients=m['excluded_patients'])
  ns=native[x['source_task'],x['id'],'N-S']['parsed'];assert ns['status'] in c.c53.VALID and ns.get('scores') is not None
  u0=c.c53.decision(ns['scores'],0);u2=c.c53.decision(ns['scores'],2)
  if u0!='Supported' and u2=='Supported':
   candidates=[r for (t,i,cond),r in native.items() if t==x['source_task'] and i==x['id'] and r['body']['model']=='qwen3.8-27b'];assert len(candidates)==1
   q=candidates[0];assert q['parsed']['status'] in c.c53.VALID and q['parsed'].get('scores') is not None;gate.append(q)
 frozen=c.ROOT/'outputs/053_thinking_prior_validation/freeze.json';bind(frozen)
 c.put(c.OUT/'postprocessing_frozen.json',c.read(frozen));c.put(c.OUT/'gate_models.json',models);c.jl(c.OUT/'gate_peers.jsonl',gate)
 c.jl(c.OUT/'reused_answers.jsonl',cache);c.jl(c.OUT/'aliases.jsonl',alias)
 # Hash order randomizes conditions; completion does not depend on observed accuracy.
 new.sort(key=lambda j:c.digest('078/order/v1:'+j['id']+j['arm']));c.jl(c.OUT/'main_jobs.jsonl',new)
 cost=defaultdict(float)
 for j in new:
  body=j['body'];textchars=sum(len(m['content']) for m in body['messages']);cond={'RN':'N-S','RT':'T-S','NV':'N-V','TV':'T-V','F4':'F4'}[j['arm']]
  uu=usage.get(cond) or usage['T-S' if j['thinking'] else 'N-S'];completion=statistics.mean(u['completion_tokens'] for u in uu)
  cost[j['arm']]+=(textchars*.40*3+completion*9)/1e6
 price=dict(checked_utc=c.now(),source_url='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',model=c.MODEL,region='Beijing',input_cny_per_million=3,output_cny_per_million=9,interpretation='0731 snapshot busy-hours list price; no cache/off-peak discount assumed',cap_cny=c.CAP)
 c.put(c.OUT/'pricing.json',price)
 artifacts={p.name:c.sha(p) for p in c.OUT.iterdir() if p.is_file() and p.name!='freeze.json'}
 freeze=dict(status='FROZEN_BEFORE_078_API',created_utc=c.now(),model=c.MODEL,cap_cny=c.CAP,new_jobs=len(new),reused_answers=len(cache),new_by_arm=dict(Counter(j['arm'] for j in new)),reused_by_arm=dict(Counter(j['arm'] for j in cache)),expected_cost_by_arm=dict(cost),expected_total_cny=sum(cost.values()),source_sha256=source,artifact_sha256=artifacts,checks=checks,gate_patient_out=True,GT_not_used_for_selection=True)
 assert sum(cost.values())<27,('Expected expense too close to cap',cost)
 c.put(c.OUT/'freeze.json',freeze);print(c.canon({k:v for k,v in freeze.items() if k not in ['source_sha256','artifact_sha256']}))
if __name__=='__main__':main()
