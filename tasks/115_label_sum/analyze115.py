"""Same-ID CPU comparison; no model, clinical relabeling or threshold search."""
from pathlib import Path
from collections import Counter
import sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/109_boundary_replay'));import common109 as c
from analyze109 import metrics
sys.path.insert(0,str(R/'tasks/110_update_interpolation'));from analyze110 import changes
sys.path.insert(0,str(R/'tasks/107_support_aux'));from evaluate107 import risk_deltas
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));from parse105 import parse
sys.path.insert(0,str(R/'src'));from verifact_research.evaluation import paired_compare
from sklearn.metrics import matthews_corrcoef,accuracy_score
P=R/'.local_models/115_label_sum';O=R/'outputs/115_label_sum'

def section(keys,base,new):
 common=[r for r in keys if base[r['id']]['valid'] and new[r['id']]['parsed']['valid']]
 rr=[dict(r,pred={'label_only107':base[r['id']]['verdict'],'label_sum':new[r['id']]['parsed']['verdict'],'paper_r1':r['paper_r1']}) for r in common]
 scores={a:metrics(rr,{r['id']:r['pred'][a] for r in rr}) for a in ['label_only107','label_sum','paper_r1']}
 for a,m in scores.items():
  assert abs(m['mcc']-matthews_corrcoef([r['GT'] for r in rr],[r['pred'][a] for r in rr]))<1e-12
  assert abs(m['percent_agreement']-accuracy_score([r['GT'] for r in rr],[r['pred'][a] for r in rr]))<1e-12
 delta=changes(rr,'label_only107','label_sum');a=scores['label_only107'];b=scores['label_sum']
 truth=[dict(proposition_id=r['id'],subject_id=str(r['sid']),human_gt=r['GT']) for r in rr]
 pred=lambda arm:[dict(proposition_id=r['id'],verdict=r['pred'][arm]) for r in rr]
 patients=[]
 for sid in sorted({str(r['sid']) for r in rr}):
  group=[r for r in rr if str(r['sid'])==sid]
  patients.append(dict(sid=sid,N=len(group),correct_delta=sum(int(r['pred']['label_sum']==r['GT'])-int(r['pred']['label_only107']==r['GT']) for r in group),false_S_delta=sum(int(r['GT']!='Supported' and r['pred']['label_sum']=='Supported')-int(r['GT']!='Supported' and r['pred']['label_only107']=='Supported') for r in group)))
 return dict(frozen_N=len(keys),joint_valid_N=len(rr),joint_valid_fraction=len(rr)/len(keys),scores=scores,changes=delta,delta_MCC=b['mcc']-a['mcc'],delta_PA=b['percent_agreement']-a['percent_agreement'],delta_correct=b['correct']-a['correct'],delta_false_S=b['false_S']-a['false_S'],
  paired=paired_compare(truth,pred('label_only107'),pred('label_sum'),iterations=1000),risk_CI=risk_deltas(rr,'label_only107','label_sum'),patients=patients,
  NA_S_to_NS_still_wrong=sum(r['GT']=='Not Addressed' and r['pred']['label_only107']=='Supported' and r['pred']['label_sum']=='Not Supported' for r in rr),
  class_transition={g:dict(Counter(r['pred']['label_only107']+' -> '+r['pred']['label_sum'] for r in rr if r['GT']==g)) for g in c.LABELS},
  author={u:{arm:metrics([r for r in rr if r['author']==u],{r['id']:r['pred'][arm] for r in rr if r['author']==u}) for arm in scores} for u in sorted({r['author'] for r in rr})},
  candidate_coverage=dict(received=len(keys),valid=sum(new[r['id']]['parsed']['valid'] for r in keys),invalid=sum(not new[r['id']]['parsed']['valid'] for r in keys),invalid_GT=dict(Counter(r['GT'] for r in keys if not new[r['id']]['parsed']['valid'])),finish_reasons=dict(Counter(new[r['id']]['finish_reason'] for r in keys))))

def main():
 key=c.rows(R/'.local_models/111_half_extension/cohort_keys.jsonl');keys=[r for r in key if r['subset']=='old500'];assert len(keys)==500
 base={r['id']:r for r in c.rows(R/'outputs/111_half_extension/predictions_sanitized.jsonl') if r['arm']=='label_only107' and r['id'] in {r['id'] for r in keys}}
 raw=[]
 for p in sorted((P/'evidence/results/eval').glob('batch-*.json')):
  receipt=c.read(p)
  for r in receipt['records']:
   assert r['parsed']==parse(r['content'],r['finish_reason']) and r['prompt_token_sha256']==base[r['id']]['prompt_token_sha256']
   raw.append(r)
 new={r['id']:r for r in raw};assert len(raw)==len(new)==500 and set(base)==set(new)
 result=dict(task=115,method='label_sum',new_training_configurations=1,no_new_API=True,baseline_reused=True,panels={})
 for panel,N in [('natural',400),('pressure',100)]:
  part=[r for r in keys if r['old_panel']==panel];assert len(part)==N;result['panels'][panel]=section(part,base,new)
 n=result['panels']['natural'];p=result['panels']['pressure'];ns=n['scores']['label_sum'];bs=n['scores']['label_only107']
 guards=dict(natural_coverage=n['joint_valid_fraction']>=.95,pressure_coverage=p['joint_valid_fraction']>=.95,natural_PA=n['delta_PA']>=-.02-1e-12,natural_S=ns['per_class']['Supported']['recall']-bs['per_class']['Supported']['recall']>=-.02-1e-12,pressure_MCC=p['delta_MCC']>=-.02-1e-12,pressure_false_S=p['delta_false_S']<=2)
 for panel,v in result['panels'].items():
  a,b=v['scores']['label_only107'],v['scores']['label_sum']
  for g in ['Not Supported','Not Addressed']:
   guards[panel+'_'+g]=b['per_class'][g]['recall']-a['per_class'][g]['recall']>=-.05-1e-12
  for g in c.LABELS:
   if b['per_class'][g]['recall'] is not None:guards[panel+'_'+g+'_positive']=b['per_class'][g]['recall']>0
 quality=n['delta_MCC']>=.02-1e-12 and n['delta_false_S']<=1;risk=n['delta_false_S']<=-4 and n['delta_MCC']>=-.01-1e-12
 result['frozen_gate']=dict(guards=guards,quality_signal=quality,risk_signal=risk,passed=all(guards.values()) and (quality or risk),automatic_expansion=False)
 result['decision']='signal_needs_user_decision_on_next_validation' if result['frozen_gate']['passed'] else 'stop_current_label_sum_recipe'
 c.put(O/'comparison.json',result)
 c.putl(O/'predictions_sanitized.jsonl',[dict(id=r['id'],sid=r['sid'],author=r['author'],GT=r['GT'],panel=r['old_panel'],label_only107=base[r['id']]['verdict'],label_sum=new[r['id']]['parsed']['verdict'],valid=new[r['id']]['parsed']['valid'],finish_reason=new[r['id']]['finish_reason'],paper_r1=r['paper_r1'],prompt_token_sha256=new[r['id']]['prompt_token_sha256']) for r in keys])
 print(c.canonical(dict(decision=result['decision'],gate=result['frozen_gate'],panels={p:{a:dict(MCC=m['mcc'],PA=m['percent_agreement'],correct=m['correct'],false_S=m['false_S'],non_S=m['non_S']) for a,m in v['scores'].items()} for p,v in result['panels'].items()})))
if __name__=='__main__':main()
