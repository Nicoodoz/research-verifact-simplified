"""Prepare one query-repetition probe, no outcome-dependent wording."""
from pathlib import Path
import sys,tarfile,shutil,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
P=R/'.local_models/116_research_cycle'
cfg=c.read(R/'tasks/113_label_path/config.json')
parser=argparse.ArgumentParser();parser.add_argument('--scope',choices=['pilot','old500','selection1817'],default='pilot');args=parser.parse_args()
job=dict(name='claim_repeat_pilot',candidate='claim_repeat',worker='generate116.py',input_transform='claim_repeat',model_dir='/root/verifact_image/models/qwen3.5-9b',adapter_path=cfg['adapter_path'],adapter_sha256=cfg['adapter_sha256'],ids=cfg['pilot_ids'],phase_limit_seconds=1800)
if args.scope!='pilot':
 keys=c.rows(P/'keys_selection1817.jsonl');pilot=set(cfg['pilot_ids']);old={r['id'] for r in keys if r['subset']=='old500'}
 if args.scope=='old500':
  job.update(name='claim_repeat_500_missing',ids=sorted(old-pilot),analysis_scope='old500',aggregate_jobs=['claim_repeat_pilot','claim_repeat_500_missing'])
 else:
  job.update(name='claim_repeat_1817_missing',ids=sorted({r['id'] for r in keys}-old-pilot),analysis_scope='selection1817',aggregate_jobs=['claim_repeat_pilot','claim_repeat_500_missing','claim_repeat_1817_missing'],inputs='data/inputs_selection1817.jsonl',phase_limit_seconds=7200)
target=P/(job['name']+'.json')
if target.exists():assert c.read(target)==job,'Existing frozen job differs'
else:c.put(target,job)
B=P/'repeat_bundle'
for name in ['tasks/116_research_cycle/generate116.py','tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']:
 p=B/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,p)
if args.scope=='selection1817':
 target=B/'data/inputs_selection1817.jsonl';target.parent.mkdir(exist_ok=True);shutil.copy2(P/'inputs_selection1817.jsonl',target)
with tarfile.open(P/'repeat_bundle.tar.gz','w:gz',compresslevel=1) as t:
 for p in B.rglob('*'):
  if p.is_file():t.add(p,arcname=p.relative_to(B),recursive=False)
print(job['name'],len(job['ids']),'new IDs; original reference remains unchanged')
