"""Fixed113 scoring comparison and prewritten pilot gate; no model calls."""
from pathlib import Path
import argparse,sys,time,math
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/109_boundary_replay'));import common109 as c
from analyze109 import metrics
sys.path.insert(0,str(R/'tasks/110_update_interpolation'));from analyze110 import changes
sys.path.insert(0,str(R/'tasks/107_support_aux'));from evaluate107 import risk_deltas
sys.path.insert(0,str(R/'src'));from verifact_research.evaluation import paired_compare
LABELS=('Supported','Not Supported','Not Addressed')
def section(keys,base,scores):
 rr=[dict(r,pred={'greedy107':base[r['id']]['verdict'],'label_path':scores[r['id']]['verdict'],'paper_r1':r['paper_r1']}) for r in keys]
 ms={a:metrics(rr,{r['id']:r['pred'][a] for r in rr}) for a in ['greedy107','label_path','paper_r1']};delta=changes(rr,'greedy107','label_path')
 co=[dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rr];pr=lambda a:[dict(proposition_id=r['id'],verdict=r['pred'][a]) for r in rr]
 patient=[dict(sid=sid,N=len(group),correct_delta=sum(int(r['pred']['label_path']==r['GT'])-int(r['pred']['greedy107']==r['GT']) for r in group),false_S_delta=sum(int(r['GT']!='Supported' and r['pred']['label_path']=='Supported')-int(r['GT']!='Supported' and r['pred']['greedy107']=='Supported') for r in group)) for sid in sorted({r['sid'] for r in rr}) for group in [[r for r in rr if r['sid']==sid]]]
 return dict(N=len(rr),scores=ms,changes=delta,delta_MCC=ms['label_path']['mcc']-ms['greedy107']['mcc'],delta_PA=ms['label_path']['percent_agreement']-ms['greedy107']['percent_agreement'],delta_correct=ms['label_path']['correct']-ms['greedy107']['correct'],delta_false_S=ms['label_path']['false_S']-ms['greedy107']['false_S'],
  disagreements=sum(r['pred']['label_path']!=r['pred']['greedy107'] for r in rr),patient_paired=paired_compare(co,pr('greedy107'),pr('label_path'),iterations=1000),risk_CI=risk_deltas(rr,'greedy107','label_path'),patients=patient,
  author={u:{a:metrics([r for r in rr if r['author']==u],{r['id']:r['pred'][a] for r in rr if r['author']==u}) for a in ms} for u in sorted({r['author'] for r in rr})})
def main(private,phase):
 cfg=c.read(R/'tasks/113_label_path/config.json');keys=c.rows(private/'keys.jsonl');base={r['id']:r for r in c.rows(private/'baseline107.jsonl')};scores={}
 for p in (private/'evidence/results/scores').glob('*.json'):
  r=c.read(p);i=r['id'];assert i not in scores and r['adapter_sha256']==cfg['adapter_sha256'] and r['prompt_token_sha256']==base[i]['prompt_token_sha256']
  assert set(r['scores'])==set(LABELS) and all(math.isfinite(v) and v<=0 for v in r['scores'].values())
  assert r['verdict']==max(LABELS,key=lambda g:r['scores'][g]);assert abs(sum(r['restricted_q'].values())-1)<1e-5;scores[i]=r
 wanted=set(cfg['pilot_ids']);assert wanted<=set(scores)
 result=dict(task=113,phase=phase,completed_unique=len(scores),new_greedy_calls=0,no_training=True,rule='complete canonical JSON+EOS sum logP argmax',sections={})
 for panel in ['natural','pressure']:result['sections']['pilot_'+panel]=section([r for r in keys if r['pilot_panel']==panel],base,scores)
 if phase=='pilot':
  n=result['sections']['pilot_natural'];p=result['sections']['pilot_pressure'];guard={}
  for label,x in [('natural',n),('pressure',p)]:
   guard[label+'_false_S']=x['delta_false_S']<=0;guard[label+'_correct']=x['delta_correct']>=-1;guard[label+'_MCC']=x['delta_MCC']>=-.01-1e-12
   for g in LABELS:
    if label=='pressure' and g=='Supported':continue
    cap=2 if g=='Supported' else 1;z=x['changes']['by_class'][g];guard[label+'_'+g]=z['rescued']-z['harmed']>=-cap
  quality=any(x['delta_correct']>=4 and x['delta_MCC']>=.02-1e-12 for x in [n,p]);risk=n['delta_false_S']+p['delta_false_S']<=-2 and n['delta_correct']+p['delta_correct']>=0
  timing=c.read(private/'evidence/results/pilot_complete.json');lengths=c.read(private/'evidence/results/input_lengths.json')['lengths'];estimate=timing['warm_seconds_per_input_token']*sum(lengths[i] for i in cfg['confirm_ids'])*1.3+120
  session=c.read(private/'session.json');available=session['start_epoch']+3600/session['rate']-time.time()-60
  gate=dict(continue_=all(guard.values()) and (quality or risk),guards=guard,quality_signal=quality,risk_signal=risk,budget_fits_confirm=estimate<=available,estimate_confirm_seconds=estimate,available_seconds=available,confirm_new_N=len(cfg['confirm_ids']))
  gate['continue']=gate.pop('continue_');c.put(private/'pilot_gate.json',gate);c.put(R/'outputs/113_label_path/pilot_gate.json',gate);result['gate']=gate
 else:
  assert set(cfg['confirm_ids'])<=set(scores)
  for panel in ['natural','pressure']:result['sections']['full500_'+panel]=section([r for r in keys if r['old_panel']==panel],base,scores)
 c.put(R/f'outputs/113_label_path/{phase}_comparison.json',result)
 c.putl(R/'outputs/113_label_path/predictions_sanitized.jsonl',[dict(id=r['id'],sid=r['sid'],GT=r['GT'],pilot_panel=r['pilot_panel'],old_panel=r['old_panel'],baseline=base[r['id']]['verdict'],**{k:scores[r['id']][k] for k in ['scores','restricted_q','verdict','input_tokens','seconds','prompt_token_sha256','adapter_sha256']}) for r in keys if r['id'] in scores])
 print(c.canonical(dict(phase=phase,gate=result.get('gate'),panels={k:{a:dict(MCC=m['mcc'],PA=m['percent_agreement'],correct=m['correct'],false_S=m['false_S'],non_S=m['non_S']) for a,m in v['scores'].items()} for k,v in result['sections'].items()})))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--private',type=Path,default=R/'.local_models/113_label_path');p.add_argument('--phase',choices=['pilot','confirm'],required=True);a=p.parse_args();main(a.private,a.phase)
