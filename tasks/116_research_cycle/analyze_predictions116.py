"""Paired first-pass screening for generative and three-code candidates."""
from pathlib import Path
from collections import Counter
import sys,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/109_boundary_replay'));import common109 as c
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));from parse105 import parse
sys.path.insert(0,str(Path(__file__).parent));from analyze_scores116 import section
P=R/'.local_models/116_research_cycle';O=R/'outputs/116_research_cycle'
def screening(panels):
 n,p=panels['natural'],panels['pressure'];net=lambda v,g:v['changes']['by_class'][g]['rescued']-v['changes']['by_class'][g]['harmed']
 guards=dict(natural_correct=n['delta_correct']>=-2,natural_MCC=n['delta_MCC']>=-.02,natural_S=net(n,'Supported')>=-3,pressure_correct=p['delta_correct']>=-2,coverage=min(n['valid_fraction'],p['valid_fraction'])>=.95)
 for g in ['Not Supported','Not Addressed']:guards['natural_'+g]=net(n,g)>=-2;guards['pressure_'+g]=net(p,g)>=-4
 for name,v in panels.items():
  for g,m in v['scores']['candidate']['per_class'].items():
   if m['recall'] is not None:guards[name+'_'+g+'_positive']=m['recall']>0
 quality=n['delta_correct']+p['delta_correct']>=4 and n['delta_MCC']>=.015;risk=n['delta_false_S']+p['delta_false_S']<=-2 and n['delta_correct']+p['delta_correct']>=-2 and n['delta_MCC']>=-.01
 return dict(guards=guards,quality_signal=quality,risk_signal=risk,continue_=all(guards.values()) and (quality or risk))
def load_predictions(name):
 job=c.read(P/(name+'.json'));new={};folder=P/'evidence'/name
 if job.get('worker')=='generate116.py' or job.get('output_mode')=='generative':
  for f in sorted((folder/'batches').glob('*.json')):
   for r in c.read(f)['records']:
    assert r['parsed']==parse(r['content'],r['finish_reason']);new[r['id']]=dict(r,verdict=r['parsed']['verdict'],valid=r['parsed']['valid'])
 else:
  for f in (folder/'predictions').glob('*.json'):
   r=c.read(f);assert r['verdict'] in c.LABELS and parse(r['content'])['verdict']==r['verdict'];new[r['id']]=dict(r,valid=True)
 assert set(new)==set(job.get('ids',job.get('eval_ids'))),'Need all first receipts, not a selected success subset'
 return new

def main(name):
 job=c.read(P/(name+'.json'));expanded=job.get('analysis_scope') in {'old500','selection1817'}
 keys={r['id']:r for r in c.rows(P/('keys_selection1817.jsonl' if expanded else 'keys.jsonl'))};base={r['id']:r for r in c.rows(P/('baseline107_selection1817.jsonl' if expanded else 'baseline107.jsonl'))};new={}
 for source in job.get('aggregate_jobs',[name]):
  source_job=c.read(P/(source+'.json'));assert source_job['candidate']==job['candidate']
  if 'adapter_sha256' in source_job and 'adapter_sha256' in job:assert source_job['adapter_sha256']==job['adapter_sha256']
  if 'input_transform' in source_job or 'input_transform' in job:assert source_job.get('input_transform','original')==job.get('input_transform','original')
  received=load_predictions(source);assert not set(new)&set(received),'Duplicate first receipts across jobs'
  if job.get('adapter_sha256'):
   assert all(r.get('adapter_sha256',job['adapter_sha256'])==job['adapter_sha256'] for r in received.values())
  new.update(received)
 wanted=list(new)
 for i,r in new.items():assert r['source_prompt_sha256_104']==base[i]['prompt_token_sha256']
 if not expanded:groups={p:[keys[i] for i in wanted if keys[i]['pilot_panel']==p] for p in ['natural','pressure']}
 else:
  groups={p:[r for r in keys.values() if r['old_panel']==p] for p in ['natural','pressure']}
  if job['analysis_scope']=='selection1817':
   groups.update(new1317=[r for r in keys.values() if r['subset']=='new'],selection1817=list(keys.values()))
   groups.update({'history103_'+p:[r for r in keys.values() if r['history103_panel']==p] for p in ['natural','pressure']})
  assert {r['id'] for rows in groups.values() for r in rows}<=set(new),'Expanded cohort missing predictions'
 panels={}
 for p,allrows in groups.items():
  rows=[r for r in allrows if new[r['id']]['valid']];part=section(rows,base,new)
  invalid=[r for r in allrows if not new[r['id']]['valid']];non_s=sum(r['GT']!='Supported' for r in allrows);unknown_non_s=sum(r['GT']!='Supported' for r in invalid);fs=part['scores']['candidate']['false_S']
  part.update(expected_N=len(allrows),valid_fraction=len(rows)/len(allrows),invalid=len(invalid),invalid_GT=dict(Counter(r['GT'] for r in invalid)),expected_non_S=non_s,unknown_non_S=unknown_non_s,false_S_full_cohort_bounds=[fs/non_s,(fs+unknown_non_s)/non_s] if non_s else None);panels[p]=part
 result=dict(job=name,candidate=job['candidate'],panels=panels,bootstrap_performed=False)
 if not expanded:result['screen']=screening(panels)
 c.put(O/(name+'.json'),result);c.putl(O/(name+'_predictions.jsonl'),[dict(id=i,sid=keys[i]['sid'],GT=keys[i]['GT'],author=keys[i]['author'],old_panel=keys[i].get('old_panel'),subset=keys[i].get('subset'),pilot_panel=keys[i]['pilot_panel'],baseline107=base[i]['verdict'],verdict=new[i]['verdict'],valid=new[i]['valid'],input_tokens=new[i].get('input_tokens'),source_input_tokens=base[i].get('input_tokens'),probabilities=new[i].get('probabilities')) for i in wanted])
 if job.get('analysis_scope')=='old500':
  sets={'shared70':[i for i in wanted if keys[i]['old_panel'] and keys[i]['pilot_panel']],
        'old500_only430':[i for i in wanted if keys[i]['old_panel'] and not keys[i]['pilot_panel']],
        'pilot_only110':[i for i in wanted if not keys[i]['old_panel'] and keys[i]['pilot_panel']]}
  diagnostic={}
  for group,ids in sets.items():
   valid=[i for i in ids if new[i]['valid']]
   diagnostic[group]=dict(expected_N=len(ids),valid_N=len(valid),correct_delta=sum(int(new[i]['verdict']==keys[i]['GT'])-int(base[i]['verdict']==keys[i]['GT']) for i in valid),false_S_delta=sum(int(keys[i]['GT']!='Supported' and new[i]['verdict']=='Supported')-int(keys[i]['GT']!='Supported' and base[i]['verdict']=='Supported') for i in valid))
  c.put(O/(name+'_overlap.json'),dict(groups=diagnostic,note='Diagnostic count differences only; original180 and old500 are not nested, and neither pooled count is a natural-distribution metric.'))
 print(c.canonical(dict(job=name,screen=result.get('screen'),panels={p:dict(delta_MCC=v['delta_MCC'],delta_correct=v['delta_correct'],delta_false_S=v['delta_false_S'],scores={a:{k:m[k] for k in ['mcc','percent_agreement','correct','false_S','non_S']} for a,m in v['scores'].items()}) for p,v in panels.items()})))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('job');main(p.parse_args().job)
