
import json,hashlib,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[3];a=Path(__file__).parent;base=root/'outputs/033_gate_training_subset'
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
sys.path.insert(0,str(root/'tasks/033_gate_training_subset'))
import common033 as s
freeze=read(base/'search_001/selection_freeze.json');rank=read(base/'historical_001/ranking.json')
def key(r):return (-int(r['eligible_retention80']),-r['robust_gain_per100R'],-r['MCC'],-r['correct'],r['risk'],r['k'],r['set_id'])
for m in ('A','D'):
 assert min([r for r in rank if r['method']==m],key=key)==freeze['historical_best'][m]
assert freeze['selected']['A']['train_patients']==['31135','59840','9030']
assert freeze['selected']['D']['train_patients']==['27036','27823','59250','59840','93640']
plan=read(base/'search_001/directed_plan.json');assert len(plan['unique_sets'])==23 and len(plan['plan'])==24
conn=read(base/'evaluation_001/label_connection.json')
assert plan['created_utc']<freeze['created_utc']<conn['created_utc']
blind=lines(base/'preparation_001/rows_selection_blind.jsonl')
assert all(r['human_gt'] is None for r in blind if r['partition']=='confirmation')
rows=lines(base/'evaluation_001/full_rows.jsonl');rr=[r for r in rows if r['partition']=='confirmation' and r['candidate']]
maps=read(base/'evaluation_001/candidate_predictions.json');subjects=sorted({r['subject_id'] for r in rows if r['partition']=='confirmation'})
y=np.array([r['human_gt']=='Supported' for r in rr]);si=np.array([subjects.index(r['subject_id']) for r in rr])
weights=np.array([np.bincount(np.random.RandomState(i).choice(12,12),minlength=12)[si] for i in range(1000)])
def mix(R,F,budget):
 lo=np.flatnonzero(F<=budget);hi=np.flatnonzero(F>budget);v=max(R[lo],default=0)
 if len(lo) and len(hi):v=max(v,float((R[lo,None]+(budget-F[lo,None])/(F[hi][None,:]-F[lo,None])*(R[hi][None,:]-R[lo,None])).max()))
 return v
matched=read(base/'evaluation_001/matched.json');draws=read(base/'evaluation_001/bootstrap_draws.json');result={}
for m in ('A','D'):
 target=m+'_directed_best';ref=m+'_all40';p=np.array([maps[ref][r['proposition_id']]['probability'] for r in rr])
 masks=np.array([[maps[ref][r['proposition_id']]['keep'] for r in rr]]+[list(p>=t) for t in [np.nextafter(max(p),np.inf),*sorted(set(p),reverse=True)]],float)
 d=np.array([maps[target][r['proposition_id']]['keep'] for r in rr],float)
 R=weights@(masks*y).T;F=weights@(masks*(~y)).T;tr=weights@(d*y);tf=weights@(d*(~y))
 vals=[float(tr[i]-mix(R[i],F[i],tf[i])) for i in range(1000)];k='confirmation/'+target+'-vs-'+ref
 assert np.allclose(vals,draws[k],atol=1e-10,rtol=0)
 gain=float(d@y-mix(masks@y,masks@(~y),d@(~y)))
 assert abs(gain-matched[k]['R_gain_vs_mixture'])<1e-10
 assert np.allclose(np.percentile(vals,[1.25,98.75]),matched[k]['ci97_5_two_main'])
 result[m]=dict(gain=gain,ci95=matched[k]['ci95'],ci97_5=matched[k]['ci97_5_two_main'])
# Recompute the selected search-panel robust score with the frozen formula (no reselection).
panel=s.Panel([r for r in blind if r['partition']=='expansion'],read(s.P31/'before_models/A.json'))
for m in ('A','D'):
 chosen=freeze['selected'][m];model=read(s.HIST/'models'/(chosen['model_id']+'.json'))
 v=panel.evaluate(s.fit_probability(model,panel.candidates),model['threshold'])
 assert abs(v['robust_gain_per100R']-chosen['robust_gain_per100R'])<1e-10
summary=dict(passed=True,historical_rankings_checked=4356,directed_sets=23,selected_search_scores_recomputed=2,independent_bootstrap_draws=2000,primary_results=result,API_calls=0,refits=0)
(a/'independent_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(summary)
