"""Prepare one query-repetition probe, no outcome-dependent wording."""
from pathlib import Path
import sys,tarfile,shutil
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
P=R/'.local_models/116_research_cycle'
cfg=c.read(R/'tasks/113_label_path/config.json')
job=dict(name='claim_repeat_pilot',candidate='claim_repeat',worker='generate116.py',input_transform='claim_repeat',model_dir='/root/verifact_image/models/qwen3.5-9b',adapter_path=cfg['adapter_path'],adapter_sha256=cfg['adapter_sha256'],ids=cfg['pilot_ids'],phase_limit_seconds=1800)
c.put(P/'claim_repeat_pilot.json',job);B=P/'repeat_bundle'
for name in ['tasks/116_research_cycle/generate116.py','tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']:
 p=B/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,p)
with tarfile.open(P/'repeat_bundle.tar.gz','w:gz',compresslevel=1) as t:
 for p in B.rglob('*'):
  if p.is_file():t.add(p,arcname=p.relative_to(B),recursive=False)
print('claim_repeat fixed180 prepared; original reference remains unchanged')
