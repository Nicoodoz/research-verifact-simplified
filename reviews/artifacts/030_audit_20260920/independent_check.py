
"""Independent 030 schedule, fixed-output statistics, and sampled-refit audit."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import json,hashlib,csv,math,socket,sys,collections
from pathlib import Path
import numpy as np
from scipy.special import expit
root=Path(__file__).resolve().parents[3];artifact=Path(__file__).parent
def blocked(*a,**k):raise RuntimeError('Offline audit')
socket.socket.connect=blocked;socket.create_connection=blocked;socket.getaddrinfo=blocked
def read(p):return json.loads((root/p).read_text(encoding='utf-8'))
def lines(p):return [json.loads(s) for s in (root/p).read_text(encoding='utf-8').splitlines()]
def table(p):
 with (root/p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
base=Path('outputs/030_gate_training_stability');prep=base/'preparation_001';run=base/'run_001'
features=lines(prep/'features.jsonl');rows=lines(prep/'full_rows.jsonl');byid={r['proposition_id']:r for r in features}
groups={r['subject_id']:r['group'] for r in features};subjects=sorted({r['subject_id'] for r in rows})
assert len(rows)==1529 and len(byid)==155 and len(groups)==15 and len(subjects)==16
split=read('outputs/003_error_analysis/patient_groups.json')['groups']
assert set(subjects)<=set(map(str,split['development'])) and not set(subjects)&set(map(str,split['reserved_test']))
for name in ('features.jsonl','full_rows.jsonl'):
 assert (root/prep/name).read_bytes()==(root/'outputs/029_semantic_information_gate/preparation_001'/name).read_bytes()
assert read(prep/'learning_config.json')==read('outputs/029_semantic_information_gate/preparation_001/config.json')
history={}
for p in (root/'reviews/artifacts').glob('*/audited_files_sha256.json'):history.update(json.loads(p.read_text()))
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in history.items())
manifest=read(prep/'manifest.json')
assert manifest['created_utc']<read(run/'execution_status.json')['started_utc']<read(run/'execution_status.json')['completed_utc']
for section in ('sources','files','code'):
 assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in manifest[section].items())
config=read(prep/'config.json');sweeps=read(prep/'sweeps.json');units=lines(prep/'units.jsonl');ul={u['unit_id']:u for u in units}
seen={};trainsets=set()
for spec in sweeps:
 signature=[]
 for uid in spec['units']:
  u=ul[uid];held=u['held_patient']
  ranked=sorted((p for p in groups if p!=held),key=lambda p:hashlib.sha256(f"{config['hash_seed']}|{spec['rep']}|{held}|{p}".encode()).hexdigest())
  selected=ranked[:spec['k']] if spec['composition'] is None else [p for group,n in zip(('025','026'),spec['composition']) for p in [p for p in ranked if groups[p]==group][:n]]
  assert sorted(selected)==u['train_patients']
  assert set(u['training_candidate_ids'])=={p for p,r in byid.items() if r['subject_id'] in selected}
  assert set(u['test_candidate_ids'])=={p for p,r in byid.items() if r['subject_id']==held}
  assert set(u['test_claim_ids'])=={r['proposition_id'] for r in rows if r['subject_id']==held}
  signature.append((held,tuple(sorted(selected))));trainsets.add(tuple(sorted(selected)))
 key=(spec['bin'],tuple(signature));expected=seen.setdefault(key,spec['sweep_id']);assert expected==spec['canonical_sweep']
assert len(trainsets)==1452 and len(seen)==141 and len(units)==2400
# Fresh fits of first hash-ranked held-out patient in each of eight pre-fixed bins, rep 0.
sys.path.insert(0,str(root/'tasks/029_semantic_information_gate'))
import learning029 as learning
schema=read(prep/'feature_schema.json')['conditions'];learn=read(prep/'learning_config.json')
selected_units=[ul[s['units'][0]] for s in sweeps if s['rep']==0]
selected={(m,tuple(u['train_patients'])) for u in selected_units for m in ('A','B','D')}
# Also refit every model with an actually recorded fallback.
def mid(method,tr):return method+'_'+hashlib.sha256(json.dumps(sorted(tr),sort_keys=True,separators=(',',':')).encode()).hexdigest()[:20]
for f in read(run/'fallbacks.json'):
 z=read(run/'models'/(f['model_id']+'.json'));selected.add((z['method'],tuple(z['final_fit']['training_patients'])))
refits=0;refitstates=0;refit_ids=[]
for method,tr in sorted(selected):
 original=read(run/'models'/(mid(method,tr)+'.json'))
 train=[r for r in features if r['subject_id'] in tr]
 fresh=learning.fold(train,[],schema[method],'Logistic',learn,set(subjects)-set(tr))
 assert all(fresh[k]==original[k] for k in fresh),mid(method,tr)
 refits+=1;refitstates+=1+len(fresh['inner_folds']);refit_ids.append(mid(method,tr))
# All operating-point mappings and R/H/W from fixed saved candidate outputs.
counts=0;maps_by_sweep={}
for spec in sweeps:
 if spec['sweep_id']!=spec['canonical_sweep']:continue
 sp=run/'sweeps'/spec['sweep_id'];maps=read(sp/'candidate_predictions.json');maps_by_sweep[spec['sweep_id']]=maps
 full=table(sp/'evaluation/full_predictions.csv');lookup={r['proposition_id']:r for r in full}
 assert set(lookup)=={r['proposition_id'] for r in rows}
 metrics=read(sp/'evaluation/metrics.json')
 for group in ('pooled','025','026'):
  for author in ('all','human','llm'):
   rr=[r for r in rows if (group=='pooled' or r['group']==group) and (author=='all' or r['author_type']==author)]
   for method in ('A','B','D'):
    R=H=W=correct=0
    for r in rr:
     accepted=r['candidate'] and maps[method][r['proposition_id']]['keep']
     p=0 if accepted else r['u0'];g=['Supported','Not Supported','Not Addressed'].index(r['human_gt'])
     assert lookup[r['proposition_id']][method]==['Supported','Not Supported','Not Addressed'][p]
     R+=accepted and g==0;H+=accepted and r['u0']==g and g!=0;W+=accepted and r['u0'] not in (0,g) and g!=0;correct+=p==g
    m=metrics[group+'/'+author+'/'+method];assert (R,H,W,correct)==(m['R'],m['H'],m['W'],m['correct']);counts+=1
truth=np.array([r['human_gt']=='Supported' for r in features]);si=np.array([subjects.index(r['subject_id']) for r in features])
weights=np.array([np.bincount(np.random.RandomState(seed).choice(16,16),minlength=16)[si] for seed in range(1000)])
def mixture(R,F,budget):
 lo=np.flatnonzero(F<=budget);hi=np.flatnonzero(F>budget);best=max(R[lo],default=0)
 if len(lo) and len(hi):
  v=R[lo,None]+(budget-F[lo,None])/(F[hi][None,:]-F[lo,None])*(R[hi][None,:]-R[lo,None])
  best=max(best,float(v.max()))
 return best
draws={r:[] for r in ('A','B')};points={r:[] for r in ('A','B')}
for rep in range(20):
 sid=f'size_11_r{rep:02}';maps=maps_by_sweep[sid];d=np.array([maps['D'][r['proposition_id']]['keep'] for r in features],float)
 tr=weights@(d*truth);tf=weights@(d*(~truth))
 for ref in ('A','B'):
  p=np.array([maps[ref][r['proposition_id']]['probability'] for r in features]);accept=np.array([[maps[ref][r['proposition_id']]['keep'] for r in features]]+[list(p>=t) for t in [np.nextafter(max(p),np.inf),*sorted(set(p),reverse=True)]],float)
  R=weights@(accept*truth).T;F=weights@(accept*(~truth)).T
  values=[float(tr[i]-mixture(R[i],F[i],tf[i])) for i in range(1000)]
  original=read(run/'sweeps'/sid/'evaluation/bootstrap.json')['matched_gain'][ref]
  assert np.allclose(values,original,rtol=0,atol=1e-10)
  draws[ref].append(values);points[ref].append(float(d@truth-mixture(accept@truth,accept@(~truth),d@(~truth))))
saved=read(run/'analysis/conditional_patient_bootstrap.json')['results']['size_11']
for ref in ('A','B'):
 assert np.allclose(np.mean(draws[ref],axis=0),saved['matched_mean_draws'][ref],rtol=0,atol=1e-10)
 assert np.allclose(np.percentile(np.mean(draws[ref],axis=0),[2.5,97.5]),saved['matched_mean_ci95'][ref],rtol=0,atol=1e-10)
# Independent per-candidate deduplication and source contrast summary.
stability=[]
for specbin in sorted({s['bin'] for s in sweeps}):
 ss=[s for s in sweeps if s['bin']==specbin and s['sweep_id']==s['canonical_sweep']]
 for method in ('A','B','D'):
  vals=[]
  for r in features:
   unique={maps_by_sweep[s['sweep_id']][method][r['proposition_id']]['model_id']:maps_by_sweep[s['sweep_id']][method][r['proposition_id']]['keep'] for s in ss}
   n=len(unique);acc=sum(unique.values())
   if n>1:vals.append(2*acc*(n-acc)/(n*(n-1)))
  expected=read(run/'analysis/stability_summary.json')[specbin][method]['mean_pairwise_disagreement']['mean']
  assert (expected is None and not vals) or abs(float(np.mean(vals))-expected)<1e-12
  stability.append((specbin,method))
contrasts={}
for method in ('A','B','D'):
 changes=[maps_by_sweep[f'source_mostly025_r{rep:02}'][method][p]['keep']!=maps_by_sweep[f'source_mostly026_r{rep:02}'][method][p]['keep'] for rep in range(20) for p in byid]
 contrasts[method]=float(np.mean(changes))
summary=dict(passed=True,historical_frozen_files=len(history),units_reconstructed=2400,unique_sweeps=141,unique_training_sets=1452,sampled_refit_final_models=refits,sampled_refit_states=refitstates,sampled_model_ids=refit_ids,full_RHW_metric_groups=counts,independent_k11_bootstrap_draws=40000,k11_mean_gain={k:float(np.mean(v)) for k,v in points.items()},k11_CI=saved['matched_mean_ci95'],stability_groups=len(stability),source_action_changes=contrasts,API_calls=0)
(artifact/'independent_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='sampled_model_ids'}))
