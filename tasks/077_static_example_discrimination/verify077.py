"""Independent frontier checks and post-hoc inspection of score saturation."""
import json,hashlib,sys
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/077_static_example_discrimination';SRC=ROOT/'outputs/076_existing_results_synthesis'
sys.path.insert(0,str(ROOT/'src'))
from verifact_research.evaluation.metrics import LABELS,encode
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8').splitlines()]
records=lines(SRC/'unified_predictions.jsonl');ix={(r['stage'],r['id'],r['arm']):r for r in records};selections=lines(OUT/'cohort_selection.jsonl');res=read(OUT/'results.json');curves=read(OUT/'curve_states.json');weights=read(SRC/'fixed_transform.json')['weights'];tail={};checks=0
for cohort in ['pooled_earliest','pooled_latest']:
 rr=[r for r in selections if r['cohort']==cohort];y=encode([ix[r['stage'],r['id'],'B']['GT'] for r in rr]);non=int(np.sum(y!=0));tail[cohort]={}
 for family in ['frozen_NS_NA','raw_NS_NA']:
  for arm in ['B','F4']:
   rows=[ix[r['stage'],r['id'],arm] for r in rr];p=np.maximum(np.array([[r['scores'][k] for k in LABELS] for r in rows])/100,1e-6)
   if family=='frozen_NS_NA':p*=np.array([weights[k] for k in LABELS])
   ss=curves[cohort][family][arm];ts=[r['shift_strictly_above'] for r in ss]
   for j,r in enumerate(ss):
    shift=-100 if j==0 else (ts[j]+ts[j+1])/2 if j<len(ss)-1 else ts[j]+1
    pp=p.copy();pp[:,0]*=np.exp(shift);tie=[1,2,0];pred=np.array(tie)[np.argmax(pp[:,tie],axis=1)]
    assert int(np.sum(pred==y))==r['correct'];assert int(np.sum((pred==0)&(y!=0)))==r['falseS'];checks+=2
   risks=np.array([r['falseS']/non for r in ss]);values=np.array([r['correct']/len(y) for r in ss])
   vv=res[cohort]['frontier']['families'][family][arm]
   for j,budget in enumerate(res[cohort]['frontier']['risk_budgets']):
    assert abs(values[risks<=budget+1e-12].max()-vv['deterministic'][j])<1e-12;checks+=1
    lp=linprog(-values,A_ub=[risks],b_ub=[budget],A_eq=[np.ones(len(ss))],b_eq=[1],bounds=(0,None),method='highs')
    assert lp.success and abs(-lp.fun-vv['mixed'][j])<1e-9;checks+=1
 for arm in ['B','F4']:
  rows=[ix[r['stage'],r['id'],arm] for r in rr];sat=[r for r in rows if r['scores'][LABELS[0]]==100 and r['scores'][LABELS[1]]==0 and r['scores'][LABELS[2]]==0]
  bad=[dict(id=r['id'],sid=r['sid'],stage=r['stage'],author=r['author'],GT=r['GT'],scores=r['scores']) for r in sat if r['GT']!=LABELS[0]]
  tail[cohort][arm]=dict(saturated_100_0_0_n=len(sat),trueS=sum(r['GT']==LABELS[0] for r in sat),falseS=len(bad),falseS_cases=bad)
# Bootstrap's unusual wide lower-tail uncertainty is interpretable, not silently discarded.
value=dict(status='PASS',independent_checks=checks,checks_include=['direct multiplicative decoding of every pooled curve state','brute force deterministic risk budget optimum','linear programming check of every mixed frontier budget'],posthoc_tail_inspection=tail,independent_audit='not performed')
(OUT/'frontier_verification.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(value,ensure_ascii=False))
