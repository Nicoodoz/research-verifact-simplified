"""Freeze both phases once, using source lengths and worst-candidate full-path costs only."""
from collections import Counter,defaultdict
import copy,json,sqlite3,sys
import duckdb,pandas as pd
import common100 as c
import evidence100 as e
sys.path.insert(0,str(c.ROOT/'tasks/098_p90_native_confirmation'))
import prepare098 as old

PROFILES=[dict(name='default',dev_n=60,dev_p=16,confirm_n=240,confirm_p=20,repeat=24),dict(name='reduced',dev_n=48,dev_p=12,confirm_n=192,confirm_p=16,repeat=16)]
NEW=['S24','L24','EHR-all']

def proportional(pool,n,seed):
 groups=defaultdict(list)
 for r in pool:groups[r['GT'],r['author']].append(r)
 quotas={k:int(n*len(v)/len(pool)) for k,v in groups.items()}
 for k in sorted(groups,key=lambda k:(-(n*len(groups[k])/len(pool)-quotas[k]),k))[:n-sum(quotas.values())]:quotas[k]+=1
 selected=[r for k,v in groups.items() for r in sorted(v,key=lambda r:c.digest(seed+r['id']))[:quotas[k]]]
 assert len(selected)==n
 return sorted(selected,key=lambda r:c.digest('100/order/v1/'+r['id']))

def design(pool,profile,confirmation):
 rows=[]
 for stage in ['development','confirmation']:
  pp=[r for r in pool if (r['sid'] in confirmation)==(stage=='confirmation')];prefix='dev' if stage=='development' else 'confirm'
  natural=proportional(pp,profile[prefix+'_n'],'100/'+stage+'/natural/v1/');ids={r['id'] for r in natural}
  repeat={r['id'] for r in sorted(natural,key=lambda r:c.digest('100/confirmation/repeat/v1/'+r['id']))[:profile['repeat']]} if stage=='confirmation' else set()
  rows.extend(dict(r,stage=stage,panel='natural',repeat_subset=r['id'] in repeat) for r in natural)
  for label in ['Not Supported','Not Addressed']:
   pressure=proportional([r for r in pp if r['id'] not in ids and r['GT']==label],profile[prefix+'_p'],'100/'+stage+'/pressure/'+label+'/v1/')
   rows.extend(dict(r,stage=stage,panel='pressure',repeat_subset=False) for r in pressure)
 assert len(rows)==len({r['id'] for r in rows})
 return rows

def body(claim,reference,template,demos=None,arm='O'):
 return old.judge(template,dict(claim=claim,C48=reference,published_reference=reference),arm,demos or {})

def job(row,arm,b,repeat=0,branch='evidence'):
 h=c.digest(c.canonical(b));rid=c.digest(c.canonical(['100/v1',branch,row['stage'],row['id'],repeat,h]))[:28]
 return dict(id=row['id'],sid=row['sid'],stage=row['stage'],panel=row['panel'],arm=arm,repeat=repeat,branch=branch,request_id=rid,body=b,body_sha256=h)

def main():
 assert not (c.OUT/'execution_freeze.json').exists()
 c.PRIVATE.mkdir(parents=True,exist_ok=True)
 admissions,notes,passages,exclusions,corpus_summary=e.source_corpus();tok=e.Tokens()
 try:
  f098=c.read(c.ROOT/'outputs/098_p90_native_confirmation/execution_freeze.json');excluded=set(f098['evaluation_patients'])|set(f098['example_development_patients']);confirmation=set(admissions)-excluded;assert len(confirmation)==32
  cohort=c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl');assert len(cohort)==9065
  pool=[dict(id=r['id'],sid=str(r['sid']),author=r['author'],GT=r['GT'],Original=r['original'],historical_role=r['historical_role']) for r in cohort]
  designs={p['name']:design(pool,p,confirmation) for p in PROFILES};chosen_ids={r['id'] for rr in designs.values() for r in rr}
  inputs={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl') if r['proposition_id'] in chosen_ids};assert set(inputs)==chosen_ids
  props={r['proposition_id']:r for r in e.csvrows(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/propositions/propositions.csv.gz') if r['proposition_id'] in chosen_ids}
  with duckdb.connect() as db:
   db.register('wanted',pd.DataFrame({'proposition_id':sorted(chosen_ids)}));links=db.execute('SELECT proposition_id,reference_id,verdict FROM read_parquet(?) JOIN wanted USING(proposition_id) WHERE rater_alias=?',[str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/verdicts.parquet'),'v1.1.0-rater-121']).fetchall()
   assert len(links)==len(chosen_ids);db.register('refs',pd.DataFrame({'reference_id':sorted({x[1] for x in links})}));references=dict(db.execute('SELECT reference_id,reference FROM read_parquet(?) JOIN refs USING(reference_id)',[str(c.ROOT/'data/00_raw/verifact-bhc/1.1.0/verifact/reference_payloads.parquet')]).fetchall())
  published={pid:(ref,verdict) for pid,ref,verdict in links};indices={sid:e.BM25(pp) for sid,pp in passages.items()};materials={};publicbuild=[]
  builder=c.sha(c.TASK/'evidence100.py');folder=c.PRIVATE/('materials_'+builder[:12]);folder.mkdir(exist_ok=True)
  pool_byid={r['id']:r for r in pool}
  for i,pid in enumerate(sorted(chosen_ids,key=lambda pid:c.digest('100/build/v1/'+pid))):
   r=pool_byid[pid];x=inputs[pid];prop=props[pid];rid,original=published[pid];sid=r['sid']
   assert prop['subject_id']==sid and prop['hadm_id']==admissions[sid]['HADM_ID'] and prop['text']==x['text'] and original==r['Original'] and c.digest(references[rid])==rid
   path=folder/(pid+'.json')
   if path.exists():m=c.read(path);assert m['builder_sha256']==builder and m['claim']==x['text']
   else:
    new,audit=e.build(x['text'],admissions[sid],notes[sid],passages[sid],indices[sid],tok)
    m=dict(id=pid,sid=sid,claim=x['text'],references=dict(O=references[rid],C=x['reference'],**new),construction=audit,published_reference_id=rid,builder_sha256=builder)
    c.put(path,m)
   materials[pid]=m
   audit=m['construction'];publicbuild.append(dict(id=pid,sid=sid,material_sha256=c.sha(path),**{k:v for k,v in audit.items() if k not in ['intervals','S_passage_ids','L_note_ids']},S_passages=len(audit['S_passage_ids']),L_notes=len(audit['L_note_ids']),claim_sha256=c.digest(m['claim']),references={a:dict(sha256=c.digest(t),characters=len(t),rendered_reference_tokens=tok.refcount(t)) for a,t in m['references'].items()}))
   if (i+1)%20==0:print(c.canonical(dict(zero_API_materials=i+1,total=len(chosen_ids))),flush=True)
  template=next(j['body'] for j in c.lines(c.ROOT/'.local_models/098_p90_native_confirmation/jobs.jsonl') if j['arm']=='O');template={k:copy.deepcopy(v) for k,v in template.items() if k!='messages'}
  assert template['model']=='deepseek-v4-flash-0731' and template['max_tokens']==8192 and template['temperature']==0 and template['reasoning_effort']=='high'
  demos=c.read(c.ROOT/'.local_models/098_p90_native_confirmation/demonstrations.json')
  qt=dict(model='qwen3.5-27b',temperature=0,top_p=1,n=1,stream=False,enable_thinking=True,thinking_budget=2048,max_tokens=512)
  variants={};allest=[];oldroom=50-c.read(c.OUT/'handoff_budget_snapshot.json')['previous098_cost_and_unknown_cny']
  for p in PROFILES:
   rr=designs[p['name']];jobs=[];qjobs=[]
   for row in rr:
    mm=materials[row['id']];arms=['O','C']+NEW;arms=arms[len(jobs)%5:]+arms[:len(jobs)%5]
    for arm in arms:
     b=body(mm['claim'],mm['references'][arm],template);j=job(row,arm,b);j['input_token_forecast']=sum(tok.count(z['content']) for z in b['messages'])+256;jobs.append(j)
    if row['stage']=='confirmation':
     qar=['O','C','P','Q'] if row['panel']=='natural' else ['O','P']
     for arm in qar:
      b=body(mm['claim'],mm['references']['C' if arm=='C' else 'O'],qt,demos,arm);j=job(row,arm,b,branch='cross_model');j['input_token_forecast']=int(sum(len(z['content']) for z in b['messages'])*.5)+512;qjobs.append(j)
     if row['repeat_subset']:
      for arm in ['O','C']+NEW:
       b=body(mm['claim'],mm['references'][arm],template);j=job(row,arm,b,1);j['input_token_forecast']=sum(tok.count(z['content']) for z in b['messages'])+256;jobs.append(j)
      for arm in ['O','P','Q']:
       b=body(mm['claim'],mm['references']['O'],qt,demos,arm);j=job(row,arm,b,1,'cross_model');j['input_token_forecast']=int(sum(len(z['content']) for z in b['messages'])*.5)+512;qjobs.append(j)
   cost=lambda j:(j['input_token_forecast']*1.5+8192*4.5)/1e6
   dev=sum(cost(j) for j in jobs if j['stage']=='development');paths={}
   for winner,arms in [('S24',['O','C','S24']),('L24',['O','C','S24','L24']),('EHR-all',['O','C','EHR-all'])]:
    reps=['O',winner]+(['S24'] if winner=='L24' else [])
    selected=[j for j in jobs if j['stage']=='confirmation' and j['arm'] in (reps if j['repeat'] else arms)]
    paths[winner]=dict(confirmation_max_output_no_cache_cny=sum(cost(j) for j in selected),confirmation_logical_jobs=len(selected))
   estimate=dict(profile=p,prior098_maximum_remaining_task_room_cny=oldroom,development_max_output_no_cache_cny=dev,candidate_paths=paths,
    worst_new_total_no_cache_max_output_cny=oldroom+dev+max(x['confirmation_max_output_no_cache_cny'] for x in paths.values()),
    cross_model_no_cache_cny=sum((j['input_token_forecast']*.6+2592*4.8)/1e6 for j in qjobs)+oldroom,
    assumptions='No cache or alias savings; full8192 output for every evidence request; full remaining098 cumulative50 capacity ring-fenced; idle input/output1.5/4.5; each request still reserved at peak byte bound')
   variants[p['name']]=dict(rows=rr,jobs=jobs,qjobs=qjobs);allest.append(estimate)
  chosen=next((x for x in allest if max(x['worst_new_total_no_cache_max_output_cny'],x['cross_model_no_cache_cny'])<=125),None)
  c.put(c.OUT/'prospective_budget_options.json',dict(utc=c.utc(),operating_line=125,new_hard_cap=130,options=allest))
  assert chosen is not None,'Both fixed scales exceed125; no follow-up API authorized within reserved completion forecast'
  name=chosen['profile']['name'];v=variants[name];rr=v['rows'];ids={r['id'] for r in rr}
  c.putl(c.PRIVATE/'sample.jsonl',[dict(r,claim=materials[r['id']]['claim'],references=materials[r['id']]['references']) for r in rr])
  c.putl(c.PRIVATE/'all_evidence_jobs.jsonl',v['jobs']);c.putl(c.PRIVATE/'all_cross_model_jobs.jsonl',v['qjobs'])
  c.putl(c.OUT/'cohort.jsonl',[dict(r,claim_sha256=c.digest(materials[r['id']]['claim']),reference_hashes={arm:c.digest(text) for arm,text in materials[r['id']]['references'].items()}) for r in rr])
  c.putl(c.OUT/'construction_ledger.jsonl',[r for r in publicbuild if r['id'] in ids])
  c.put(c.OUT/'budget_plan.json',dict(utc=c.utc(),chosen=chosen,reason='First of the two user-fixed scales whose most-expensive complete confirmation path fits125 with no cache and max outputs; selected before any100 answer',no_quality_read=True))
  filelist=[c.TASK/f for f in ['protocol.md','common100.py','evidence100.py','prepare100.py','token_count_worker100.py']]+[c.PRIVATE/f for f in ['sample.jsonl','all_evidence_jobs.jsonl','all_cross_model_jobs.jsonl']]+[c.OUT/f for f in ['cohort.jsonl','construction_ledger.jsonl','budget_plan.json','source_registry.json','source_inventory.json']]
  c.put(c.OUT/'execution_freeze.json',dict(utc=c.utc(),profile=chosen['profile'],files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in filelist},development_patients=sorted(excluded),confirmation_patients=sorted(confirmation),
    stage_counts={stage:dict(N=sum(r['stage']==stage for r in rr),patients=len({r['sid'] for r in rr if r['stage']==stage}),natural_GT=dict(Counter(r['GT'] for r in rr if r['stage']==stage and r['panel']=='natural'))) for stage in ['development','confirmation']},
    data_scope='All patients historically exposed; this-round patient-isolated confirmation only',GT_in_construction=False,new100_answers_seen=False,branch_decided=False,
    methods=dict(S24='Full008 BM25 whole640-character blocks matched to actual renderedL length',L24='Whole original notes scored by max008 child BM25,24K',EHR_all='All eligible original notes without retrieval/truncation')))
  print(c.canonical(dict(frozen=True,profile=chosen['profile'],worst_new_total_cny=chosen['worst_new_total_no_cache_max_output_cny'],cases=len(rr),source=corpus_summary)))
 finally:tok.close()
if __name__=='__main__':main()
