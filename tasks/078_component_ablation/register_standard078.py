"""Freeze historical patient-out standard controls; no target GT or scores read."""
import common078 as c
def main():
 source={};mapping={};patients={x['sid'] for x in c.lines(c.OUT/'primary_blind.jsonl')}
 for fold in range(4):
  p=c.ROOT/f'outputs/034_same_data_comparison/lambda_extension_001/run_001/fits/main40/fold{fold}.json';m=c.read(p);source[p.relative_to(c.ROOT).as_posix()]=c.sha(p)
  for sid in m['evaluation']['main40']['patients']:
   if sid not in patients:continue
   assert sid not in m['training_patients'] and sid not in mapping
   mapping[sid]=dict(fold=fold,source=p.relative_to(c.ROOT).as_posix(),training_patients=m['training_patients'],M=m['models']['M_022'],V=m['models']['V_022'])
 assert set(mapping)==patients
 for p in [c.TASK/'standard_controls_addendum.md',c.ROOT/'tasks/022_competition_aware_support_calibration/calibration022.py']:source[p.relative_to(c.ROOT).as_posix()]=c.sha(p)
 c.put(c.OUT/'standard_controls_freeze.json',dict(created_utc=c.now(),target_GT_joined=False,extra_API=0,new_fits=0,source_sha256=source,mapping=mapping));print('24 patient-out standard-control bindings frozen; no target GT read')
if __name__=='__main__':main()
