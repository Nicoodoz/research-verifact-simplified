"""077: read-only score discrimination and GT-aware frontier diagnostics, no fitting/API."""
import argparse,datetime,hashlib,json,sys
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).parent;SRC=ROOT/'outputs/076_existing_results_synthesis'
sys.path.insert(0,str(ROOT/'src'))
from verifact_research.evaluation import evaluate
from verifact_research.evaluation.metrics import LABELS,encode
PAIRS=[(0,1),(0,2),(1,2)];PNAMES=['S_NS','S_NA','NS_NA'];GRID=np.array([0,.05,.10,.20,.30,1.]);CHECKS=0
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def put(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
def jl(p,x):Path(p).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n' for r in x),encoding='utf-8',newline='\n')
def finite(x):return None if not np.isfinite(x) else float(x)
def interval(x):
 x=np.asarray(x);z=x[np.isfinite(x)]
 return dict(valid_draws=len(z),invalid_draws=len(x)-len(z),ci95=[float(v) for v in np.quantile(z,[.025,.975])] if len(z) else None)
def data(rows):
 y=encode([x['GT'] for x in rows]);sids=sorted({x['sid'] for x in rows});sid=np.array([sids.index(x['sid']) for x in rows]);scores={a:np.array([[x[a]['scores'][k] for k in LABELS] for x in rows],float) for a in ['B','F4']}
 return y,sids,sid,{a:np.log(np.maximum(s/100,1e-6)) for a,s in scores.items()}
def auc_arrays(rows,boot=True):
 global CHECKS
 y,sids,sid,logs=data(rows);npat=len(sids);w=np.array([np.bincount(np.random.RandomState(i).randint(0,npat,npat),minlength=npat) for i in range(1000)]) if boot else np.ones((1,npat))
 result={};draws={a:[] for a in logs};within={};shifts={}
 for key,(c,d) in zip(PNAMES,PAIRS):
  pos=np.where(y==c)[0];neg=np.where(y==d)[0];pair={};wx={}
  npatpos=np.bincount(sid[pos],minlength=npat);npatneg=np.bincount(sid[neg],minlength=npat);den=(w@npatpos)*(w@npatneg)
  for arm,l in logs.items():
   z=np.round(l[:,c]-l[:,d],12);delta=z[pos,None]-z[neg][None,:];wins=(delta>0).astype(float)+.5*(delta==0)
   auc=float(wins.mean()) if len(pos) and len(neg) else None
   if auc is not None:
    q=np.r_[z[pos],z[neg]];truth=np.r_[np.ones(len(pos)),np.zeros(len(neg))];assert abs(auc-roc_auc_score(truth,q))<1e-12;CHECKS+=1
    for constant in [-5.0,.1342909508820116,2.5184]:
     assert abs(auc-roc_auc_score(truth,np.round(q+constant,10)))<1e-12;CHECKS+=1
   wins_pat=np.zeros((npat,npat));np.add.at(wins_pat,(np.broadcast_to(sid[pos,None],wins.shape).ravel(),np.broadcast_to(sid[neg][None,:],wins.shape).ravel()),wins.ravel())
   num=np.einsum('bi,ij,bj->b',w,wins_pat,w);draw=np.divide(num,den,out=np.full(len(w),np.nan),where=den>0);draws[arm].append(draw)
   same=sid[pos,None]==sid[neg][None,:];wx[arm]=dict(auc=float(wins[same].mean()) if same.any() else None,within_patient_pairs=int(same.sum()),patients_with_both=int(np.sum((npatpos>0)&(npatneg>0))))
   pair[arm]=dict(auc=auc,interval=interval(draw) if boot else None)
  bd,fd=draws['B'][-1],draws['F4'][-1]
  result[key]=dict(positive=LABELS[c],negative=LABELS[d],positive_n=len(pos),negative_n=len(neg),B=pair['B'],F4=pair['F4'],delta=None if pair['B']['auc'] is None else pair['F4']['auc']-pair['B']['auc'],delta_interval=interval(fd-bd) if boot else None)
  within[key]=dict(**wx,delta=None if wx['B']['auc'] is None else wx['F4']['auc']-wx['B']['auc'])
  dz=(logs['F4'][:,c]-logs['F4'][:,d])-(logs['B'][:,c]-logs['B'][:,d])
  shifts[key]={label:dict(n=int(np.sum(y==k)),mean=finite(np.mean(dz[y==k])) if np.any(y==k) else None,median=finite(np.median(dz[y==k])) if np.any(y==k) else None) for k,label in enumerate(LABELS)}
 valid=all(v['delta'] is not None for v in result.values())
 mb=np.mean(np.array(draws['B']),axis=0);mf=np.mean(np.array(draws['F4']),axis=0)
 macro=dict(B=float(np.mean([x['B']['auc'] for x in result.values()])) if valid else None,F4=float(np.mean([x['F4']['auc'] for x in result.values()])) if valid else None,delta=float(np.mean([x['delta'] for x in result.values()])) if valid else None,delta_interval=interval(mf-mb) if boot else None)
 return dict(pairs=result,macro=macro,within_patient=within,class_conditional_log_ratio_shift=shifts)
def envelope(risk,correct):
 # Risk upper-bound, maximizing total correct. Collapse identical risk and remove dominated states.
 xx=np.unique(risk);yy=np.array([correct[risk==x].max() for x in xx]);yy=np.maximum.accumulate(yy)
 keep=np.r_[True,np.diff(yy)>1e-12];xx,yy=xx[keep],yy[keep];hx=[];hy=[]
 for x,y in zip(xx,yy):
  while len(hx)>1 and (hy[-1]-hy[-2])*(x-hx[-1]) <= (y-hy[-1])*(hx[-1]-hx[-2])+1e-14:hx.pop();hy.pop()
  hx.append(x);hy.append(y)
 return xx,yy,np.array(hx),np.array(hy)
def envelope_values(risk,correct):
 x,y,hx,hy=envelope(risk,correct)
 det=lambda q:y[np.maximum(0,np.searchsorted(x,q+1e-12,side='right')-1)]
 mix=lambda q:np.interp(q,hx,hy)
 dx=np.unique(np.r_[0,x[(x>0)&(x<.2)],.2]);mx=np.unique(np.r_[0,hx[(hx>0)&(hx<.2)],.2])
 det_area=float(np.sum(np.diff(dx)*det(dx[:-1]))/.2);mix_area=float(np.sum(np.diff(mx)*(mix(mx[:-1])+mix(mx[1:]))/2)/.2)
 return dict(deterministic=det(GRID).tolist(),mixed=mix(GRID).tolist(),low_risk_mean_deterministic=det_area,low_risk_mean_mixed=mix_area),dict(deterministic_x=x.tolist(),deterministic_y=y.tolist(),mixed_x=hx.tolist(),mixed_y=hy.tolist())
def states(rows,arm,family,weights,score=False):
 global CHECKS
 y,sids,sid,logs=data(rows);z=logs[arm].copy()
 if family=='frozen_NS_NA':z+=np.log(np.array([weights[k] for k in LABELS]))
 margin=np.round(z[:,0]-np.maximum(z[:,1],z[:,2]),12);levels=np.unique(margin)[::-1]
 base=np.where(z[:,1]>=z[:,2],1,2);pred=[base.copy()];ranges=[None]
 for level in levels:
  p=base.copy();p[margin>=level]=0;pred.append(p);ranges.append(float(-level))
 pred=np.array(pred);correct=(pred==y).astype(float);risk=((pred==0)&(y!=0)).astype(float)
 nsna0=pred[0];assert all(np.all(p[p!=0]==nsna0[p!=0]) for p in pred);CHECKS+=1
 anchor=np.array([x[arm]['PriorG' if family=='frozen_NS_NA' else 'raw'] for x in rows]);anchoridx=encode(anchor.tolist());assert any(np.array_equal(anchoridx,p) for p in pred);CHECKS+=1
 pointmetrics=[]
 if score:
  co=[dict(proposition_id=x['id'],subject_id=x['sid'],human_gt=x['GT']) for x in rows]
  for i,p in enumerate(pred):
   e=evaluate(co,[dict(proposition_id=x['id'],verdict=LABELS[int(k)]) for x,k in zip(rows,p)],profile='none',missing='error')
   assert abs(e['percent_agreement']-correct[i].mean())<1e-12;CHECKS+=1
   pointmetrics.append(dict(state=i,shift_strictly_above=ranges[i],correct=int(correct[i].sum()),falseS=int(risk[i].sum()),PA=e['percent_agreement'],MCC=e['mcc'],AC1=e['gwet_ac1']))
 return correct,risk,pointmetrics
def frontiers(rows,weights,boot=True,save_states=False):
 y,sids,sid,logs=data(rows);n=len(rows);non=int(np.sum(y!=0));families={};saved={}
 if non==0:return dict(defined=False,reason='No non-S ground truth'),saved
 npat=len(sids);w=np.array([np.bincount(np.random.RandomState(i).randint(0,npat,npat),minlength=npat)[sid] for i in range(1000)]) if boot else None
 for family in ['frozen_NS_NA','raw_NS_NA']:
  values={};draws={};saved[family]={}
  for arm in ['B','F4']:
   c,r,met=states(rows,arm,family,weights,save_states);v,env=envelope_values(r.sum(axis=1)/non,c.sum(axis=1)/n);values[arm]=dict(**v,envelope=env);saved[family][arm]=met
   if boot:
    C=c@w.T;R=r@w.T;N=w.sum(axis=1);NON=w[:,y!=0].sum(axis=1);ds=[]
    for i in range(1000):
     if NON[i]==0:ds.append([np.nan]*14);continue
     vi,_=envelope_values(R[:,i]/NON[i],C[:,i]/N[i]);ds.append(vi['deterministic']+vi['mixed']+[vi['low_risk_mean_deterministic'],vi['low_risk_mean_mixed']])
    draws[arm]=np.array(ds)
  delta={k:(np.array(values['F4'][k])-np.array(values['B'][k])).tolist() for k in ['deterministic','mixed','low_risk_mean_deterministic','low_risk_mean_mixed']}
  cis=None
  if boot:
   d=draws['F4']-draws['B'];cis=dict(deterministic=[interval(d[:,i]) for i in range(6)],mixed=[interval(d[:,6+i]) for i in range(6)],low_risk_mean_deterministic=interval(d[:,12]),low_risk_mean_mixed=interval(d[:,13]))
  families[family]=dict(**values,delta=delta,delta_intervals=cis)
 return dict(defined=True,n=n,nonS_n=non,risk_budgets=GRID.tolist(),families=families),saved
def describe(rows,weights,boot=True,save_states=False):
 f,s=frontiers(rows,weights,boot,save_states)
 return dict(n=len(rows),patients=len({x['sid'] for x in rows}),GT_counts=dict(Counter(x['GT'] for x in rows)),author_counts=dict(Counter(x['author'] for x in rows)),auc=auc_arrays(rows,boot),frontier=f),s
def compact(z):
 return dict(n=z['n'],auc={k:v['delta'] for k,v in z['auc']['pairs'].items()},macro=z['auc']['macro']['delta'],frontier={f:v['delta']['low_risk_mean_mixed'] for f,v in z['frontier'].get('families',{}).items()})
def check_synthetic():
 global CHECKS
 x,y,hx,hy=envelope(np.array([0,0,.1,.2,1]),np.array([.4,.5,.7,.6,.3]));assert np.allclose(x,[0,.1]) and np.allclose(y,[.5,.7]);CHECKS+=1
 v,_=envelope_values(np.array([0,.1,.2,1]),np.array([.5,.55,.7,.4]));assert abs(v['low_risk_mean_mixed']-.6)<1e-12 and v['mixed'][1]>v['deterministic'][1];CHECKS+=1
 assert roc_auc_score([0,1],[2,2])==.5;assert roc_auc_score([0,1],[1,2])==1;CHECKS+=2
 tiny=[]
 for i,(gt,b,f) in enumerate([(LABELS[0],[80,10,10],[40,30,30]),(LABELS[1],[10,80,10],[40,30,30]),(LABELS[2],[10,10,80],[40,30,30])]):tiny.append(dict(id=str(i),sid=str(i),GT=gt,B=dict(scores=dict(zip(LABELS,b))),F4=dict(scores=dict(zip(LABELS,f)))))
 a=auc_arrays(tiny,False);assert a['macro']['B']==1 and a['macro']['F4']==.5;CHECKS+=1
 tiny=[x for x in tiny if x['GT']!=LABELS[2]];assert auc_arrays(tiny,False)['macro']['delta'] is None;CHECKS+=1
 return CHECKS
def main(out):
 out.mkdir(parents=True,exist_ok=False);pre=read(SRC/'manifest.json');assert all(sha(ROOT/p)==h for p,h in pre['files'].items());syn=check_synthetic()
 source={str((SRC/x).relative_to(ROOT)).replace('\\','/'):sha(SRC/x) for x in ['manifest.json','unified_predictions.jsonl','static_pool_selection.jsonl','fixed_transform.json','static_F4_deduplicated.json','paired_decomposition.json']}
 put(out/'analysis_freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),protocol_sha256=sha(TASK/'README.md'),analysis_code_sha256=sha(Path(__file__)),sources=source,risk_budgets=GRID.tolist(),primary_risk_interval=[0,.2],bootstrap_iterations=1000,new_API=0,new_fits=0,synthetic_checks=syn))
 records=lines(SRC/'unified_predictions.jsonl');ix={(x['stage'],x['id'],x['arm']):x for x in records};keys=sorted({x['stage'] for x in records});weights=read(SRC/'fixed_transform.json')['weights'];pools={};excluded={};selected=[]
 def make(options,name):
  rows=[];bad=[]
  for stage,pid in sorted(options):
   b=ix[stage,pid,'B'];f=ix[stage,pid,'F4'];assert all(b[k]==f[k] for k in ['id','sid','author','GT','reference_sha256']);assert b['id']==pid
   if not(b['valid'] and f['valid']):bad.append(dict(id=pid,stage=stage,B_valid=b['valid'],F4_valid=f['valid']));continue
   rows.append(dict(id=pid,stage=stage,sid=b['sid'],author=b['author'],GT=b['GT'],B=b,F4=f));selected.append(dict(cohort=name,id=pid,stage=stage))
  assert len({x['id'] for x in rows})==len(rows);pools[name]=rows;excluded[name]=bad
 for stage in keys:make([(stage,i) for i in sorted({x['id'] for x in records if x['stage']==stage})],stage)
 selection=lines(SRC/'static_pool_selection.jsonl')
 for policy in ['earliest','latest']:make([(x['stage'],x['id']) for x in selection if x['policy']==policy],'pooled_'+policy)
 for name in ['pooled_earliest','pooled_latest']:
  for author in ['human','llm']:pools[name+'_'+author]=[x for x in pools[name] if x['author']==author]
 jl(out/'cohort_selection.jsonl',selected);put(out/'excluded.json',excluded);results={};curves={}
 for name,rows in pools.items():
  results[name],curves[name]=describe(rows,weights,True,True);print(json.dumps(dict(cohort=name,**compact(results[name]))),flush=True)
 put(out/'results.json',results);put(out/'curve_states.json',curves)
 sensitivity={}
 for name in ['pooled_earliest','pooled_latest']:
  rows=pools[name];loo={};blocks={}
  for sid in sorted({x['sid'] for x in rows}):z,_=describe([x for x in rows if x['sid']!=sid],weights,False);loo[sid]=compact(z)
  for label,tasks in [('071_072',['071','072']),('073',['073']),('074',['074']),('075',['075'])]:z,_=describe([x for x in rows if x['stage'][:3] not in tasks],weights,False);blocks[label]=compact(z)
  sensitivity[name]=dict(leave_patient_out=loo,leave_task_block_out=blocks)
 put(out/'sensitivity.json',sensitivity)
 assert all(sha(ROOT/p)==h for p,h in source.items());assert all(sha(ROOT/p)==h for p,h in pre['files'].items())
 put(out/'verification.json',dict(status='PASS',checks=CHECKS,source_076_manifest_unchanged=True,source_files=source,cohorts=len(pools),primary_n={k:results[k]['n'] for k in ['pooled_earliest','pooled_latest']},new_API_calls=0,cost_cny=0,new_fits=0,deployment_threshold_selected=False,independent_audit='not performed'))
 print(json.dumps(dict(status='PASS',checks=CHECKS)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',default='outputs/077_static_example_discrimination');args=p.parse_args()
 with threadpool_limits(limits=1):main((ROOT/args.output).resolve())
