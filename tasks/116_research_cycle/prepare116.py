"""Initialize the authorized cycle and first cached-input joint-path probe."""
from pathlib import Path
from datetime import datetime
import sys,shutil,tarfile
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
P=R/'.local_models/116_research_cycle';O=R/'outputs/116_research_cycle'
def main():
 P.mkdir(exist_ok=True);O.mkdir(parents=True,exist_ok=True);B=P/'bundle';(B/'data').mkdir(parents=True,exist_ok=True)
 session=dict(cycle=1,start_epoch=1793274436,start_beijing='2026-10-29 19:47:16',duration_seconds=43200,deadline_beijing='2026-10-30 07:47:16',GPU_cap_CNY=20,API_cap_CNY=20,hourly_CNY=1.58,no_shutdown=True)
 c.put(P/'session.json',session);c.put(B/'session.json',session)
 source=R/'.local_models/113_label_path';inputs=c.rows(source/'inputs.jsonl');keys=c.rows(source/'keys.jsonl');cfg113=c.read(R/'tasks/113_label_path/config.json')
 assert len(inputs)==610 and len(cfg113['pilot_ids'])==180
 c.putl(P/'keys.jsonl',keys);c.putl(B/'data/inputs.jsonl',inputs);c.putl(P/'baseline107.jsonl',c.rows(source/'baseline107.jsonl'))
 h=c.read(R/'.local_models/115_label_sum/evidence/results/train/checkpoint_a/checkpoint_complete.json')['files']['adapter_model.safetensors']
 job=dict(name='joint_path_pilot',candidate='joint_path',adapter_path='/root/autodl-tmp/verifact115/results/train/checkpoint_a',adapter_sha256=h,ids=cfg113['pilot_ids'],label_sequences=cfg113['label_sequences'],branch_ids=cfg113['branch_ids'],phase_limit_seconds=1800,first_value_index=4,source='original113_fixed180',model_dir='/root/verifact_image/models/qwen3.5-9b',max_seq_length=13783,scoring='canonical_JSON_plus_EOS_sum_logP',new_training=False,no_temperature=True)
 c.put(B/'data/joint_path_pilot.json',job);c.put(P/'joint_path_pilot.json',job)
 for name in ['tasks/116_research_cycle/score116.py','tasks/104_supervision_evidence/training104.py','tasks/106_label_preparation/loss106.py']:
  dest=B/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,dest)
 with tarfile.open(P/'bundle116.tar.gz','w:gz',compresslevel=1) as t:
  for p in B.rglob('*'):
   if p.is_file():t.add(p,arcname=p.relative_to(B),recursive=False)
 if not (O/'cycle_state.json').exists():c.put(O/'cycle_state.json',dict(**session,status='first_probe_prepared',active_job='joint_path_pilot',completed_jobs=[],best_candidate='107_label_only',paid_API_CNY=0,confirmation40_used=False))
 print(c.canonical(dict(job=job['name'],N=len(job['ids']),bundle_bytes=(P/'bundle116.tar.gz').stat().st_size)))
if __name__=='__main__':main()
