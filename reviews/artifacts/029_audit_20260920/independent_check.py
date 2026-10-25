
"""Independent 029 audit: no task-029 implementation imports or fitting."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import json,csv,hashlib,math,socket
from pathlib import Path
import numpy as np
from scipy.special import expit
from scipy.optimize import linprog
import xgboost as xgb
def blocked(*a,**k):raise RuntimeError('Audit is offline')
socket.socket.connect=blocked;socket.create_connection=blocked;socket.getaddrinfo=blocked
root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent
def read(p):return json.loads((root/p).read_text(encoding='utf-8'))
def lines(p):return [json.loads(s) for s in (root/p).read_text(encoding='utf-8').splitlines()]
def table(p):
 with (root/p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
base=Path('outputs/029_semantic_information_gate');prep=base/'preparation_001';run=base/'run_001'
rows=lines(prep/'full_rows.jsonl');features=lines(prep/'features.jsonl');byid={r['proposition_id']:r for r in features}
labels=['Supported','Not Supported','Not Addressed'];subjects=sorted({r['subject_id'] for r in rows})
split=read('outputs/003_error_analysis/patient_groups.json')['groups']
assert len(rows)==1529 and len(features)==155 and len(subjects)==16
assert set(subjects)<=set(map(str,split['development'])) and not set(subjects)&set(map(str,split['reserved_test']))
h=read(base/'handoff_001.json')
mutable={'docs/PROJECT_STATUS.md', 'README.md', 'outputs/029_semantic_information_gate/CURRENT_STATUS.md', 'AGENTS.md', 'docs/REPRODUCIBILITY.md', 'tasks/029_semantic_information_gate/CURRENT_STATUS.md'}
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in h['sha256'].items() if p not in mutable)
history={}
for p in (root/'reviews/artifacts').glob('*/audited_files_sha256.json'):history.update(json.loads(p.read_text()))
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in history.items())
manifest=read(prep/'manifest.json')
first=(root/base/'launch_run_001/stdout.log').read_text().split()[0]
assert manifest['created_utc']<first<read(run/'execution_status.json')['completed_utc']
for section in ('sources','files','code'):
 assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in manifest[section].items())
source={r['proposition_id']:r for r in read('outputs/027_dual_judge_transfer_diagnosis/analysis_002/candidates.json')}
norm={(r['proposition_id'],r['arm']):r for r in lines('outputs/028_traceable_claim_evidence_verification/analysis_001/normalized.jsonl')}
def logs(sc):return np.array([math.log(max(sc[l]/100,1e-6)) for l in labels])
def dec(z,t):return 0 if z[0]+t>max(z[1:]) else (1 if z[1]>=z[2] else 2)
schema=read(prep/'feature_schema.json')['conditions']
for r in features:
 pid=r['proposition_id'];s=source[pid];sc=s['D_scores'];q=s['Q_scores'];p=np.array([sc[l]/100 for l in labels]);z=logs(sc);zz=logs(q)
 values=[*p,z[0]-max(z[1:]),abs(z[1]-z[2]),-sum(p*np.log(np.maximum(p,1e-6))),float(dec(z,0)==1),q[labels[0]]/100,zz[0]-max(zz[1:]),float(dec(zz,0)==0),float(dec(zz,2)==0),float(dec(z,0)==dec(zz,0))]
 assert np.allclose(values,[r['features'][k] for k in schema['A']],rtol=0,atol=1e-12)
 repeat=norm[pid,'repeat'];trace=norm[pid,'trace'];rr=trace['rows'];ev=[e for x in rr for e in x['evidence']]
 expected=[float(repeat['verdict']==l) for l in labels]+[len(rr)]+[sum(x['relation']==rel for x in rr)/len(rr) for rel in ('supported','contradicted','unaddressed','uncertain')]+[float(trace['claim_coverage']=='complete'),sum(bool(x['claim_spans']) for x in rr)/len(rr),sum(bool(x['valid']) for x in ev)/len(ev) if ev else 0.,float(trace['status']!='valid' or bool(trace.get('adherence')) or any(x.get('diagnostics') for x in rr))]
 assert np.allclose(expected,[r['features'][k] for k in schema['D'][12:]],rtol=0,atol=1e-12)
models=0;folds=0;lp_count=0;cms=0
def predict(meta,ids):
 global models
 models+=1;tr=[byid[p] for p in meta['training_ids']];names=meta['features']
 assert meta['fallback'] is None
 assert meta['R']==sum(r['human_gt']=='Supported' for r in tr)
 X=np.array([[byid[p]['features'][n] for n in names] for p in ids]).reshape(len(ids),len(names))
 if meta['estimator']=='Logistic':
  tx=np.array([[r['features'][n] for n in names] for r in tr]);sd=tx.std(axis=0);sd[sd<1e-12]=1
  assert np.allclose(tx.mean(axis=0),meta['mean'],atol=1e-12,rtol=0)
  assert np.allclose(sd,meta['scale'],atol=1e-12,rtol=1e-10)
  return expit(((X-meta['mean'])/meta['scale'])@np.array(meta['coef'])+meta['intercept'])
 b=xgb.Booster(params={'nthread':1});b.load_model(bytearray(meta['booster_json'],'utf-8'))
 assert len(b.get_dump())==40
 return b.predict(xgb.DMatrix(X)) if len(ids) else np.array([])
for scope in ('patient_OOF','025_to_026','026_to_025'):
 scopepath=run/scope
 for methodpath in (root/scopepath).iterdir():
  if methodpath.name=='evaluation':continue
  merged={}
  for path in methodpath.glob('fold_*.json'):
   f=json.loads(path.read_text());folds+=1;excluded=set(f['excluded_patients'])
   expected={p for p,r in byid.items() if r['subject_id'] not in excluded}
   assert set(f['final_fit']['training_ids'])==expected
   assert set(f['test_ids'])==set(byid)-expected
   assert f['final_fit']['features']==schema[methodpath.name.split('-')[0]]
   inner={r['proposition_id']:r for r in f['inner_predictions']};assert set(inner)==expected
   for im in f['inner_folds']:
    sid=im['held_patient']
    assert set(im['training_ids'])=={p for p in expected if byid[p]['subject_id']!=sid}
    assert set(im['test_ids'])=={p for p in expected if byid[p]['subject_id']==sid}
    assert np.allclose(predict(im,im['test_ids']),[inner[p]['probability'] for p in im['test_ids']],rtol=0,atol=1e-12)
   positive=sorted([x['probability'] for p,x in inner.items() if byid[p]['human_gt']=='Supported'],reverse=True)
   t=positive[math.ceil(.8*len(positive))-1];assert t==f['threshold']
   pp=predict(f['final_fit'],f['test_ids']);local={r['proposition_id']:r for r in f['predictions']}
   assert all(abs(v-local[p]['probability'])<1e-12 and bool(v>=t)==local[p]['keep'] for p,v in zip(f['test_ids'],pp))
   merged.update(local)
  assert merged=={r['proposition_id']:r for r in json.loads((methodpath/'predictions.json').read_text())}
 full=table(scopepath/'evaluation/full_predictions.csv');metrics=read(scopepath/'evaluation/metrics.json')
 for key,m in metrics.items():
  group,author,method=key.split('/');ss=[r for r in full if (group=='pooled' or r['group']==group) and (author=='all' or r['author_type']==author)]
  cm=[[sum(r['GT']==g and r[method]==p for r in ss) for p in labels] for g in labels]
  assert cm==m['confusion_matrix'] and sum(cm[i][i] for i in range(3))==m['correct'];cms+=1
 curves=table(scopepath/'evaluation/curves.csv')
 for key,refs in read(scopepath/'evaluation/matched_risk.json').items():
  group,method=key.split('/');m=metrics[group+'/all/'+method]
  for ref,v in refs.items():
   cc=[r for r in curves if r['group']==group and r['reference']==ref];R=np.array([float(r['R']) for r in cc]);F=np.array([float(r['risk']) for r in cc])
   lp=linprog(-R,A_ub=F[None,:],b_ub=[m['risk']],A_eq=np.ones((1,len(R))),b_eq=[1],bounds=(0,None),method='highs')
   assert lp.success and abs(m['R']+lp.fun-v['R_gain_vs_mixture'])<1e-8;lp_count+=1
# Independently enumerate every pair of probability operating points for primary OOF CIs.
scope=run/'patient_OOF';cand=features;truth=np.array([r['human_gt']=='Supported' for r in cand]);sid=np.array([subjects.index(r['subject_id']) for r in cand])
maps={m:{r['proposition_id']:r for r in read(scope/m/'predictions.json')} for m in ('A-Logistic','B-Logistic','D-Logistic')}
def counts(accept,w):
 return accept@(w*truth),accept@(w*(~truth))
def mixture(R,F,budget):
 best=max(R[F<=budget],default=0)
 lo=np.flatnonzero(F<=budget);hi=np.flatnonzero(F>budget)
 if len(lo) and len(hi):
  fl=F[lo,None];fh=F[hi][None,:];v=R[lo,None]+(budget-fl)/(fh-fl)*(R[hi][None,:]-R[lo,None]);best=max(best,float(v.max()))
 return best
target=np.array([maps['D-Logistic'][r['proposition_id']]['keep'] for r in cand])
cis={}
for ref in ('A-Logistic','B-Logistic'):
 p=np.array([maps[ref][r['proposition_id']]['probability'] for r in cand])
 masks=np.array([[maps[ref][r['proposition_id']]['keep'] for r in cand]]+[list(p>=t) for t in [np.nextafter(max(p),np.inf),*sorted(set(p),reverse=True)]])
 values=[]
 for seed in range(1000):
  w=np.bincount(np.random.RandomState(seed).choice(16,16),minlength=16)[sid]
  R,F=counts(masks.astype(float),w);tr,tf=counts(target.astype(float),w)
  values.append(float(tr-mixture(R,F,tf)))
 actual=read(scope/'evaluation/matched_bootstrap.json')['pooled/D-Logistic'][ref]['R_gain_vs_mixture']['ci95']
 ci=np.percentile(values,[2.5,97.5]);assert np.allclose(ci,actual,atol=1e-10,rtol=0);cis[ref]=ci.tolist()
 for excluded in range(16):
  w=(sid!=excluded).astype(float);R,F=counts(masks.astype(float),w);tr,tf=counts(target.astype(float),w);assert tr-mixture(R,F,tf)>0
summary=dict(passed=True,initial_handoff_files=len(h['sha256']),historical_frozen_files=len(history),features_checked=len(features),models_replayed_without_fit=models,folds=folds,confusion_matrices=cms,independent_LP_operating_points=lp_count,primary_bootstrap_draws=2000,primary_CIs=cis,primary_LOO_positive_each=16,API_calls=0)
(out/'independent_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary))
