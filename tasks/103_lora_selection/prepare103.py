import sys,json,subprocess
from collections import defaultdict,Counter
import duckdb,pandas as pd
import common103 as c
sys.path.insert(0,str(c.ROOT/'tasks/097_native_judge_source_dependence'))
from prepare_a import SYSTEM,original_style_prompt
def messages(claim,ref,mode):
 p=original_style_prompt(claim,ref)
 if mode=='label':
  start=p.index('4. Provide a reason');end=p.index('\n\n## Input JSON:')
  p=p[:start]+'4. Format your response as a JSON object with only the key "verdict". Return only JSON; do not include a reason.'+p[end:]
 return [dict(role='system',content=SYSTEM),dict(role='user',content=p)]
def body(model,r,mode):
 b=dict(model=model,messages=messages(r['claim'],r['reference'],mode),temperature=0,top_p=1,repetition_penalty=1,n=1,stream=False,enable_thinking=mode=='native',max_tokens=c.ANSWER if mode=='native' else 128)
 if mode=='native':b['thinking_budget']=c.THINKING
 return b
def strat(rows,n,seed,keys=('GT','author')):
 g=defaultdict(list)
 for r in rows:g[tuple(r[k] for k in keys)].append(r)
 exact={k:n*len(v)/len(rows) for k,v in g.items()};q={k:int(v) for k,v in exact.items()}
 for k in sorted(g,key=lambda k:(-(exact[k]-q[k]),k))[:n-sum(q.values())]:q[k]+=1
 assert all(q[k]<=len(g[k]) for k in q)
 return sorted([r for k,v in g.items() for r in sorted(v,key=lambda r:c.digest(seed+r['id']))[:q[k]]],key=lambda r:c.digest(seed+'order'+r['id']))
def dispersed(rows,n,seed):
 by=defaultdict(list)
 for r in sorted(rows,key=lambda r:c.digest(seed+r['id'])):by[r['sid']].append(r)
 patients=sorted(by,key=lambda s:c.digest(seed+s));out=[]
 while len(out)<n:
  for sid in patients:
   if by[sid] and len(out)<n:out.append(by[sid].pop(0))
 return out
def main():
 cohort=c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')
 roles={'train':'development','selection':'exploration','confirmation':'reserved_test'}
 patients={k:sorted({str(r['sid']) for r in cohort if r['historical_role']==v}) for k,v in roles.items()}
 assert [len(patients[k]) for k in roles]==[40,20,40]
 c.put(c.OUT/'patient_roles.json',dict(patients=patients,all100_historically_exposed=True,confirmation_new_evaluation=False))
 inputs={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')}
 eligible=[r for r in cohort if r['historical_role']!='reserved_test']
 with duckdb.connect() as db:
  db.register('wanted',pd.DataFrame({'proposition_id':[r['id'] for r in eligible]}))
  vv=db.execute('SELECT proposition_id,reference_id,verdict FROM read_parquet(?) JOIN wanted USING(proposition_id) WHERE rater_alias=?',[str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet'),'v1.1.0-rater-121']).fetchall()
  db.register('refids',pd.DataFrame({'reference_id':list({v[1] for v in vv})}))
  refs=dict(db.execute('SELECT reference_id,reference FROM read_parquet(?) JOIN refids USING(reference_id)',[str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/reference_payloads.parquet')]).fetchall())
 assert len(vv)==len(eligible);vmap={pid:(ref,pred) for pid,ref,pred in vv};rows=[]
 for r in eligible:
  rid,pred=vmap[r['id']];assert pred==r['original'] and c.digest(refs[rid])==rid
  rows.append(dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],author=r['author'],paper_r1=pred,claim=inputs[r['id']]['text'],reference=refs[rid],reference_id=rid,role='train' if r['historical_role']=='development' else 'selection'))
 c.putl(c.PRIVATE/'eligible.jsonl',rows)
 pool=[r for r in rows if r['role']=='selection'];natural=strat(pool,120,'103/natural120/v1/');used={r['id'] for r in natural}
 for r in natural:r['panel']='natural';r['local180']=True
 pressure=[]
 for lab in c.LABELS[1:]:
  chosen=strat([r for r in pool if r['GT']==lab and r['id'] not in used],30,'103/pressure30/'+lab)
  for r in chosen:r['panel']='pressure';r['local180']=True
  pressure+=chosen;used|={r['id'] for r in chosen}
 more=strat([r for r in pool if r['id'] not in used],40,'103/natural40/v1/');used|={r['id'] for r in more}
 for r in more:r['panel']='natural';r['local180']=False
 natural+=more
 for lab in c.LABELS[1:]:
  chosen=strat([r for r in pool if r['GT']==lab and r['id'] not in used],10,'103/pressure10/'+lab)
  for r in chosen:r['panel']='pressure';r['local180']=False
  pressure+=chosen;used|={r['id'] for r in chosen}
 sample=natural+pressure;direct=[];repeat=[]
 for lab in c.LABELS:
  pp=dispersed([r for r in sample if r['local180'] and r['GT']==lab],16,'103/direct/'+lab);direct+=pp;repeat+=pp[:8]
 dids={r['id'] for r in direct};rids={r['id'] for r in repeat}
 for r in sample:r['direct48']=r['id'] in dids;r['repeat24']=r['id'] in rids
 training=[]
 for half in range(2):
  for lab,n in zip(c.LABELS,[160,48,48]):
   old={r['id'] for r in training};training+=dispersed([r for r in rows if r['role']=='train' and r['GT']==lab and r['id'] not in old],n,f'103/train/{half}/{lab}')
  start=half*256;training[start:]=sorted(training[start:],key=lambda r:c.digest('103/train/order/'+r['id']))
 c.putl(c.PRIVATE/'train512.jsonl',training);c.putl(c.PRIVATE/'sample240.jsonl',sample)
 public=lambda r:{k:v for k,v in r.items() if k not in ['claim','reference']}|dict(claim_sha256=c.digest(r['claim']),reference_sha256=c.digest(r['reference']))
 c.putl(c.OUT/'cohort240.jsonl',[public(r) for r in sample]);c.putl(c.OUT/'train512_ids.jsonl',[public(r) for r in training])
 jobs=[]
 for r in sample:
  for mode,rep in [('native',0)]+([('label',0)] if r['direct48'] else [])+([('native',1)] if r['repeat24'] else []):
   for m in c.MODELS:
    b=body(m,r,mode);sha=c.digest(c.canonical(b));rid=c.digest(c.canonical(['103',r['id'],m,mode,rep,sha]))[:28]
    jobs.append(dict(id=r['id'],sid=r['sid'],panel=r['panel'],local180=r['local180'],mode=mode,repeat=rep,model=m,request_id=rid,body_sha256=sha,body=b))
 c.putl(c.PRIVATE/'jobs_all.jsonl',jobs)
 probes=[]
 for panel in ['natural','pressure']:
  pp=sorted([r for r in sample if r['local180'] and r['panel']==panel],key=lambda r:c.digest('103/usage/'+r['id']))[:2]
  probes += [j['request_id'] for j in jobs if j['id'] in {r['id'] for r in pp} and j['mode']=='native' and j['repeat']==0]
 probes += [j['request_id'] for j in jobs if j['id'] in {r['id'] for r in direct[:2]} and j['mode']=='label']
 paths=[c.TASK/'protocol.md',c.TASK/'prepare103.py',c.TASK/'common103.py',c.OUT/'patient_roles.json',c.OUT/'cohort240.jsonl',c.OUT/'train512_ids.jsonl',c.PRIVATE/'jobs_all.jsonl',c.PRIVATE/'train512.jsonl',c.PRIVATE/'sample240.jsonl']
 c.put(c.OUT/'data_freeze.json',dict(utc=c.utc(),files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},usage_probe_ids=probes,no_new_answers=True,GT_natural=dict(Counter(r['GT'] for r in natural)),GT_training=dict(Counter(r['GT'] for r in training))))
 print(c.canonical(dict(rows=len(rows),selection=len(pool),sample=len(sample),training=len(training),training_patients=len({r['sid'] for r in training}),jobs=len(jobs),probes=len(probes))))
if __name__=='__main__':main()
