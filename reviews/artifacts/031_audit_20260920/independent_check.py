
"""Independent 031 receipt accounting, split/timing, refit and matched-risk audit."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import json,csv,hashlib,socket,sys,collections
from decimal import Decimal as D
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[3];artifact=Path(__file__).parent;base=Path('outputs/031_training_expansion_confirmation')
def blocked(*a,**k):raise RuntimeError('Audit offline')
socket.socket.connect=blocked;socket.create_connection=blocked;socket.getaddrinfo=blocked
def read(p):return json.loads((root/p).read_text(encoding='utf-8'))
def lines(p):return [json.loads(s) for s in (root/p).read_text(encoding='utf-8').splitlines()]
def table(p):
 with (root/p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
history={}
for p in (root/'reviews/artifacts').glob('*/audited_files_sha256.json'):history.update(json.loads(p.read_text()))
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in history.items())
split=read(base/'planning_001/split.json');groups=read('outputs/003_error_analysis/patient_groups.json')['groups']
old=lines('outputs/029_semantic_information_gate/preparation_001/features.jsonl')
fullold=lines('outputs/029_semantic_information_gate/preparation_001/full_rows.jsonl')
assert sorted({r['subject_id'] for r in fullold})==split['original16']
remaining=sorted(set(map(str,groups['development']))-set(split['original16']),key=lambda p:hashlib.sha256(('031/patient-split/v1:'+p).encode()).hexdigest())
assert remaining[:12]==split['expansion12'] and remaining[12:]==split['confirmation12']
assert not set(remaining)&set(map(str,groups['reserved_test']))
materials={r['proposition_id']:r for r in lines(base/'judge_inputs_001/materials.jsonl')}
ledger={r['path'].replace('\\','/'):r for r in table(base/'costs_001/ledger.csv')}
counts=collections.Counter();roles=collections.Counter();success=collections.Counter();total=D(0);reserved=D(0);events=[];requests=[]
# Frozen role templates used only for exact body comparison; no 031 API implementation.
sys.path.insert(0,str(root/'tasks/028_traceable_claim_evidence_verification'))
import common028
for p in sorted((root/base/'attempts').glob('*/request.json')):
 rq=json.loads(p.read_text());job=rq['job'];body=job['body'];requests.append(rq);rp=p.parent/'receipt.json'
 assert hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()==rq['body_sha256']
 reserve=D(str(rq['reservation_cny']));charge=reserve
 assert D(str(rq['prior_task_used_or_reserved_cny']))+reserve<=80+D('1e-12')
 events.append((rq['created_utc'],1,reserve));end=None
 if rp.exists():
  rec=json.loads(rp.read_text());assert rec['request_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
  tr=rec['transport'];status=tr['http_status'];native=json.loads(tr['body_text']);counts[status]+=1;end=tr['ended_utc']
  if status==200:
   success[job['request_id']]+=1;roles[job.get('role',job['kind'])]+=1
   u=native.get('usage',{})
   if job['kind']=='chat':
    assert native['model']==body['model'];assert u['total_tokens']==u['prompt_tokens']+u['completion_tokens']
    charge=(D(u['prompt_tokens'])*3+D(u['completion_tokens'])*(12 if job['role']=='peer' else 9))/1000000
   else:
    counted=u.get('prompt_tokens',u.get('total_tokens',native.get('meta',{}).get('billed_units',{}).get('input_tokens',native.get('meta',{}).get('tokens',{}).get('input_tokens'))))
    assert isinstance(counted,int) and counted>0;charge=D(counted)*D('.07')/1000000
  else:
   assert status in (401,429);reserved+=reserve
 else:counts['missing_receipt']+=1;reserved+=reserve
 assert abs(charge-D(ledger[p.relative_to(root).as_posix()]['charge_cny']))<D('1e-12')
 assert charge<=reserve+D('1e-12')
 total+=charge
 if end:events.append((end,0,charge-reserve))
 if job['kind']=='chat':
  m=materials[job['proposition_id']];role=job['role']
  expected=common028.body(m['text'],m['reference'],role) if role in ('repeat','trace') else common028.api.old.body(m['text'],m['reference'],True)
  if role in ('score','peer'):expected['model']='qwen3.8-27b' if role=='peer' else 'deepseek-v4-flash-0731'
  assert body==expected
  assert set(json.loads(body['messages'][1]['content']))=={'proposition','reference'}
assert len(requests)==4513 and len(success)==4484 and max(success.values())==1
assert counts=={200:4484,401:4,429:14,'missing_receipt':11}
assert abs(total-D('37.70924338'))<D('1e-10')
running=D(0);peak=D(0)
for _,_,delta in sorted(events):running+=delta;peak=max(peak,running)
assert peak<=80
first=min(r['created_utc'] for r in requests);firstchat=min(r['created_utc'] for r in requests if r['job']['kind']=='chat')
assert read(base/'before_models/manifest.json')['created_utc']<first
for name in ('freeze_001/manifest.json','execution_freeze_001.json','analysis_contract_001.json'):
 m=read(base/name)
 assert m['created_utc']<firstchat
 for p,h in m['sha256'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h
inf=read(base/'inference_001/manifest.json');gtconnection=read(base/'analysis_001/GT_connection.json')
assert inf['created_utc']<gtconnection['connected_utc']
assert hashlib.sha256((root/base/'inference_001/confirmation_predictions_blind.jsonl').read_bytes()).hexdigest()==inf['predictions_sha256']==gtconnection['prediction_sha256']
unknown={str(p.relative_to(root)).replace('\\','/') for p in (root/base/'attempts').glob('*/request.json') if not (p.parent/'receipt.json').exists()}
assert unknown=={p.replace('\\','/') for p in read(base/'io_amendment_001/manifest.json')['unknown_request_paths']}
# Every cached reference binds back to the unchanged original C48 source.
sources={}
cache=lines(base/'materials_001/cached_c48.jsonl')
for r in cache:
 src=r['source']
 if src not in sources:sources[src]={x['proposition_id']:x for x in lines(src)}
 x=sources[src][r['proposition_id']]
 ref=x['retrieval']['C48']['reference'] if '/009_' in src else x['reference']
 assert ref==r['reference']==materials[r['proposition_id']]['reference']
assert len(cache)==745
# Refit all eight frozen learning recipes, not searching a new model.
sys.path.insert(0,str(root/'tasks/029_semantic_information_gate'))
import learning029
config=read('outputs/029_semantic_information_gate/preparation_001/config.json')
schema=read('outputs/029_semantic_information_gate/preparation_001/feature_schema.json')['conditions']
train=lines(base/'inference_001/shared_training_features.jsonl');assert len(train)==246
assert not set(r['subject_id'] for r in train)&set(split['confirmation12'])
states=0
for era,pool in [('before',old),('after',train)]:
 for m in 'ABCD':
  saved=read(base/(era+'_models')/(m+'.json'))
  fresh=learning029.fold(pool,[],schema[m],'Logistic',config,split['confirmation12'])
  assert all(fresh[k]==saved[k] for k in fresh),era+m
  states+=len(fresh['inner_folds'])+1
# Independent raw two-point envelope bootstrap from confirmation predictions.
gt={r['proposition_id']:r['human_gt'] for r in table(base/'analysis_001/confirmation_GT.csv')}
rows=lines(base/'inference_001/confirmation_predictions_blind.jsonl');patients=sorted({r['subject_id'] for r in rows})
cand=[r for r in rows if r['candidate']];truth=np.array([gt[r['proposition_id']]=='Supported' for r in cand]);si=np.array([patients.index(r['subject_id']) for r in cand])
weights=np.array([np.bincount(np.random.RandomState(i).choice(12,12),minlength=12)[si] for i in range(1000)])
def mix(R,F,budget):
 lo=np.flatnonzero(F<=budget);hi=np.flatnonzero(F>budget);best=max(R[lo],default=0)
 if len(lo) and len(hi):best=max(best,float((R[lo,None]+(budget-F[lo,None])/(F[hi][None,:]-F[lo,None])*(R[hi][None,:]-R[lo,None])).max()))
 return best
primary={}
matched=read(base/'analysis_001/matched.json');draws=read(base/'analysis_001/bootstrap_draws.json')
for target,ref in [('after_C','after_A'),('after_D','after_B')]:
 key=target+'-vs-'+ref;p=np.array([r['methods'][ref]['probability'] for r in cand])
 masks=np.array([[r['methods'][ref]['keep'] for r in cand]]+[list(p>=t) for t in [np.nextafter(max(p),np.inf),*sorted(set(p),reverse=True)]],float)
 d=np.array([r['methods'][target]['keep'] for r in cand],float)
 R=weights@(masks*truth).T;F=weights@(masks*(~truth)).T;tr=weights@(d*truth);tf=weights@(d*(~truth))
 values=[float(tr[i]-mix(R[i],F[i],tf[i])) for i in range(1000)]
 assert np.allclose(values,draws[key],rtol=0,atol=1e-10)
 gain=float(d@truth-mix(masks@truth,masks@(~truth),d@(~truth)))
 assert abs(gain-matched[key]['R_gain_vs_mixture'])<1e-10
 assert np.allclose(np.percentile(values,[2.5,97.5]),matched[key]['ci95'])
 assert np.allclose(np.percentile(values,[1.25,98.75]),matched[key]['ci97_5_Bonferroni2'])
 loo=[]
 for sid in range(12):
  w=(si!=sid).astype(float);loo.append(float(d@(w*truth)-mix(masks@(w*truth),masks@(w*(~truth)),d@(w*(~truth)))))
 assert all(v<0 for v in loo)
 primary[key]=dict(gain=gain,ci95=matched[key]['ci95'],ci97_5=matched[key]['ci97_5_Bonferroni2'],LOO_negative=len(loo))
summary=dict(passed=True,historical_frozen_files=len(history),requests=len(requests),http_counts=dict(counts),successful_roles=dict(roles),Decimal_total=str(total),failed_unknown_reserve=str(reserved),peak_event_reservation=str(peak),first_API=first,first_Judge=firstchat,cached_C48_bound=745,all_models_refit=8,refit_model_states=states,primary_bootstrap_draws=2000,primary_results=primary,API_calls=0)
(artifact/'independent_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary))
