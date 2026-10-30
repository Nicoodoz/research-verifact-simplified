"""Admission estimate from completed real inference timings; never launches work."""
from pathlib import Path
import argparse,json,time,sys
R=Path(__file__).resolve().parents[2];P=R/'.local_models/137_extra_steps'
sys.path.insert(0,str(R/'tasks/135_reason_first'));from analyze135 import collect
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
def main():
 p=argparse.ArgumentParser();p.add_argument('--scope',choices=['old500','full1817'],required=True);a=p.parse_args()
 done=c.read(P/'evidence/extra_steps/complete.json');trained=c.read(P/'evidence/extra_steps/training_done.json')
 assert done['N']==160 and trained['steps']==518
 keys=c.rows(R/'.local_models/134_author_baselines/keys.jsonl');screen=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
 target={r['id'] for r in keys if a.scope=='full1817' or r['old_panel'] in ('natural','pressure')}
 prior=collect([P/'evidence/extra_steps/predictions',P/'evidence/screen160/extra_steps',P/'evidence/old500/extra_steps',P/'evidence/full1817/extra_steps'])
 remaining=target-prior.keys()
 old=collect([R/'.local_models/136_claim_repeat_transfer/evidence'/scope/'claim_repeat' for scope in ['screen160','old500','full1817']])
 old_screen_seconds=sum(old[i]['seconds'] for i in screen)
 actual_new_screen_wall=max(1,done['epoch']-trained['epoch'])
 ratio=max(1,actual_new_screen_wall/old_screen_seconds)
 inference_seconds=sum(old[i]['seconds'] for i in remaining)*ratio*1.25+180
 reserve=900
 session=c.read(R/'.local_models/134_author_baselines/session.json');deadline=session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY'];now=time.time()
 result=dict(scope=a.scope,new_IDs=len(remaining),already_attempted=len(target&prior.keys()),
  method='Recorded136 per-ID batch time, multiplied by observed137 screen slowdown and1.25 safety; plus180s loading and900s return/analysis/publish reserve',
  recorded_new160_seconds=actual_new_screen_wall,slowdown_factor=ratio,estimated_inference_and_loading_seconds=inference_seconds,
  save_analysis_publish_reserve_seconds=reserve,remaining_global_seconds=deadline-now,
  current_GPU_estimate_CNY=(now-session['start_epoch'])*session['hourly_CNY']/3600,
  projected_GPU_estimate_CNY=(now-session['start_epoch']+inference_seconds+reserve)*session['hourly_CNY']/3600,
  fits_current_budget=bool(inference_seconds+reserve<=deadline-now),API_CNY=0,no_shutdown=True,
  limitation='Forecast only; actual progress and hard wall-clock guards remain authoritative. Invalid first outputs are not rerun.')
 c.put(P/(a.scope+'_budget_forecast.json'),result);print(c.canonical(result))
if __name__=='__main__':main()
