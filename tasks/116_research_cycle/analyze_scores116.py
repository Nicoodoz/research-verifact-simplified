"""Lightweight cycle screening; no routine bootstrap, model call or GT routing."""
from pathlib import Path
import argparse,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/109_boundary_replay'));import common109 as c
from analyze109 import metrics
sys.path.insert(0,str(R/'tasks/110_update_interpolation'));from analyze110 import changes
P=R/'.local_models/116_research_cycle';O=R/'outputs/116_research_cycle'
def section(keys,old,new):
 rows=[dict(r,pred={'label_only107':old[r['id']]['verdict'],'candidate':new[r['id']]['verdict'],'paper_r1':r['paper_r1']}) for r in keys]
 m={a:metrics(rows,{r['id']:r['pred'][a] for r in rows}) for a in ['label_only107','candidate','paper_r1']};a,b=m['label_only107'],m['candidate']
 return dict(N=len(rows),scores=m,changes=changes(rows,'label_only107','candidate'),delta_MCC=b['mcc']-a['mcc'],delta_PA=b['percent_agreement']-a['percent_agreement'],delta_correct=b['correct']-a['correct'],delta_false_S=b['false_S']-a['false_S'],patient_directions=[dict(sid=s,N=len(z),correct_delta=sum(int(r['pred']['candidate']==r['GT'])-int(r['pred']['label_only107']==r['GT']) for r in z),false_S_delta=sum(int(r['GT']!='Supported' and r['pred']['candidate']=='Supported')-int(r['GT']!='Supported' and r['pred']['label_only107']=='Supported') for r in z)) for s in sorted({r['sid'] for r in rows}) for z in [[r for r in rows if r['sid']==s]]])
def main(jobname):
 job=c.read(P/(jobname+'.json'));base={r['id']:r for r in c.rows(P/'baseline107.jsonl')};keys={r['id']:r for r in c.rows(P/'keys.jsonl')};scores={}
 for f in (P/'evidence'/jobname/'scores').glob('*.json'):
  r=c.read(f);assert r['adapter_sha256']==job['adapter_sha256'] and r['prompt_token_sha256']==base[r['id']]['prompt_token_sha256'];assert r['id'] not in scores;scores[r['id']]=r
 assert set(job['ids'])<=set(scores)
 if jobname.endswith('pilot'):groups={p:[keys[i] for i in job['ids'] if keys[i]['pilot_panel']==p] for p in ['natural','pressure']}
 else:
  # Expanded scores are combined only when their frozen IDs and adapter agree.
  for folder in (P/'evidence').glob('joint_path_*'):
   for f in (folder/'scores').glob('*.json'):
    r=c.read(f)
    if r['adapter_sha256']==job['adapter_sha256']:scores[r['id']]=r
  groups={p:[r for r in keys.values() if r['old_panel']==p] for p in ['natural','pressure']}
 out=dict(job=jobname,candidate=job['candidate'],panels={p:section(rs,base,scores) for p,rs in groups.items()},bootstrap_performed=False,cohort_role='development_only')
 if jobname.endswith('pilot'):
  n,p=out['panels']['natural'],out['panels']['pressure'];net=lambda v,g:v['changes']['by_class'][g]['rescued']-v['changes']['by_class'][g]['harmed']
  guards=dict(natural_correct=n['delta_correct']>=-2,natural_MCC=n['delta_MCC']>=-.02,natural_S=net(n,'Supported')>=-3,pressure_correct=p['delta_correct']>=-2)
  for g in ['Not Supported','Not Addressed']:guards['natural_'+g]=net(n,g)>=-2;guards['pressure_'+g]=net(p,g)>=-4
  for panel,v in out['panels'].items():
   for g,m in v['scores']['candidate']['per_class'].items():
    if m['recall'] is not None:guards[panel+'_'+g+'_positive']=m['recall']>0
  quality=n['delta_correct']+p['delta_correct']>=4 and n['delta_MCC']>=.015;risk=n['delta_false_S']+p['delta_false_S']<=-2 and n['delta_correct']+p['delta_correct']>=-2 and n['delta_MCC']>=-.01
  out['screen']=dict(guards=guards,quality_signal=quality,risk_signal=risk,continue_=all(guards.values()) and (quality or risk))
 c.put(O/(jobname+'.json'),out);c.putl(O/(jobname+'_predictions.jsonl'),[dict(id=i,sid=keys[i]['sid'],GT=keys[i]['GT'],pilot_panel=keys[i]['pilot_panel'],old_panel=keys[i]['old_panel'],baseline107=base[i]['verdict'],verdict=scores[i]['verdict'],scores=scores[i]['scores'],restricted_q=scores[i]['restricted_q']) for i in job['ids']])
 if jobname=='joint_path_pilot':
  prior={r['id']:r for r in c.rows(R/'outputs/115_label_sum/predictions_sanitized.jsonl')};common=sorted(set(prior)&set(job['ids']));parts={}
  for panel in ['natural','pressure']:
   ids=[i for i in common if keys[i]['pilot_panel']==panel]
   parts[panel]=dict(N=len(ids),greedy_correct=sum(prior[i]['label_sum']==prior[i]['GT'] for i in ids),MAP_correct=sum(scores[i]['verdict']==prior[i]['GT'] for i in ids),changed=sum(scores[i]['verdict']!=prior[i]['label_sum'] for i in ids),S_rescued=sum(prior[i]['GT']=='Supported' and prior[i]['label_sum']!='Supported' and scores[i]['verdict']=='Supported' for i in ids),S_harmed=sum(prior[i]['GT']=='Supported' and prior[i]['label_sum']=='Supported' and scores[i]['verdict']!='Supported' for i in ids))
  c.put(O/'joint_path_mechanism70.json',dict(N=len(common),scope='Only original180 intersect115 existing500; descriptive, no new inference',panels=parts))
 print(c.canonical(dict(job=jobname,screen=out.get('screen'),panels={p:dict(delta_MCC=v['delta_MCC'],delta_correct=v['delta_correct'],delta_false_S=v['delta_false_S'],candidate=v['scores']['candidate']) for p,v in out['panels'].items()})))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('job');main(p.parse_args().job)
