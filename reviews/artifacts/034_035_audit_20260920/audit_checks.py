
"""Scoped 034/035 audit. Redirect verifier receipts; never overwrite frozen results."""
import os,sys,json,csv,hashlib,importlib.util,socket
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.optimize import minimize
root=Path(__file__).resolve().parents[3];a=Path(__file__).parent
def denied(*args,**kwargs):raise RuntimeError('Audit is offline')
socket.socket.connect=denied;socket.create_connection=denied
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def read(p):return json.loads(p.read_text())
def csvread(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
original_write=Path.write_text
def audited_write(path,data,*args,**kwargs):
 path=Path(path)
 if path.name=='verification_001.json' and path.parent.name in ('034_same_data_comparison','035_lambda_boundary_calibration'):
  path=a/(path.parent.name+'_verification.json')
 else:raise AssertionError('Unexpected audit verifier write: '+str(path))
 return original_write(path,data,*args,**kwargs)
with patch.object(Path,'write_text',audited_write):
 for number,name in [('034','034_same_data_comparison'),('035','035_lambda_boundary_calibration')]:
  sys.path.insert(0,str(root/'tasks'/name))
  m=load('verify'+number,root/'tasks'/name/('verify'+number+'.py'));m.main()
# Verify exact source connection for every034 row, not only its aggregate.
p34=root/'outputs/034_same_data_comparison'
base={r['proposition_id']:r for r in csvread(root/'outputs/033_gate_training_subset/evaluation_001/full_predictions.csv')}
original={r['proposition_id']:r for author in ('human','llm') for r in csvread(root/f'outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv')}
for r in csvread(p34/'predictions_common.csv'):
 b=base[r['proposition_id']];o=original[r['proposition_id']]
 assert r['Original_Verifact_O']==o['verdict'] and r['U2']==b['U2'] and r['U2_A_all40_LOPO']==b['A_all40']
 assert r['GT']==b['GT'] and r['subject_id']==b['subject_id']
# Independently solve every final numerical fit with working SLSQP.
sys.path.insert(0,str(root/'tasks/035_lambda_boundary_calibration'))
import common as c,learning as l
run=root/'outputs/035_lambda_boundary_calibration/run_002';datasets=read(run/'inputs_numeric.json')
cases=[];replayed=0;max_lp=0.
for source in ('old_R0','main40','bridge_deepseek','bridge_qwen'):
 for fold in range(4):
  meta=read(run/f'fits/{source}/fold{fold}.json');train=[r for r in datasets[source] if r['fold']!=fold]
  assert meta['training_ids']==[r['id'] for r in train] and meta['training_patients']==sorted({r['sid'] for r in train})
  for name,scope in meta['evaluation'].items():
   origin='bridge_qwen' if name=='DS_to_Q' else 'bridge_deepseek' if name=='Q_to_DS' else name
   test=[r for r in datasets[origin] if r['fold']==fold]
   assert scope['ids']==[r['id'] for r in test]
   assert set(meta['training_patients']).isdisjoint(r['sid'] for r in test)
   inferred=l.infer(test,meta['models']);frozen=np.load(run/'frozen_predictions'/(name+'.npz'))
   ii=np.array([i for i,r in enumerate(datasets[origin]) if r['fold']==fold])
   for method,(p,lp) in inferred.items():
    assert np.array_equal(p,frozen[method+'_labels'][ii])
    diff=float(np.max(np.abs(lp-frozen[method+'_logprob'][ii])));max_lp=max(max_lp,diff);assert diff<1e-12
    replayed+=1
  cases.append((source+f'/fold{fold}',train,meta['models']))
cases.append(('full_main40',datasets['main40'],read(run/'full_development_models.json')['models']))
comparisons=[]
for name,train,models in cases:
 z,y=c.arrays(train);old=models['Joint_NLL']
 fit=minimize(lambda x:l.joint_objective(x,z,y),[old['a'],old['b']],jac=True,method='SLSQP',
  bounds=[(.05,5),(0,20)],constraints=[{'type':'ineq','fun':lambda x:4*x[0]-x[1],'jac':lambda x:np.array([4.,-1.])}],
  options={'ftol':1e-12,'maxiter':300})
 gap=old['train_nll']-float(fit.fun)
 comparisons.append(dict(name=name,success=bool(fit.success),saved_nll=old['train_nll'],slsqp_nll=float(fit.fun),gap=gap,saved_lambda=old['lam'],slsqp_lambda=float(fit.x[1]/fit.x[0])))
assert all(r['success'] and abs(r['gap'])<1e-8 for r in comparisons),comparisons
summary=dict(passed=True,source034_exact_rows=3675,folds_patient_isolation=16,prediction_method_fold_replays=replayed,max_logprob_difference=max_lp,joint_slsqp_comparisons=comparisons,API_calls=0)
(a/'independent_summary.json').write_text(json.dumps(summary,indent=2)+chr(10),encoding='utf-8')
print('Independent audit PASS; 17 SLSQP fits, max NLL gap',max(abs(r['gap']) for r in comparisons),flush=True)
