"""Prepare one query-repetition probe, no outcome-dependent wording."""
from pathlib import Path
import sys,tarfile,shutil,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
P=R/'.local_models/116_research_cycle'
cfg=c.read(R/'tasks/113_label_path/config.json')
parser=argparse.ArgumentParser();parser.add_argument('--scope',choices=['pilot','old500','selection1817'],default='pilot');parser.add_argument('--candidate',choices=['claim_repeat','support_check','gentle_refresh'],default='claim_repeat');args=parser.parse_args();prefix=args.candidate
job=dict(name=prefix+'_pilot',candidate=prefix,worker='generate116.py',input_transform=prefix,model_dir='/root/verifact_image/models/qwen3.5-9b',adapter_path=cfg['adapter_path'],adapter_sha256=cfg['adapter_sha256'],ids=cfg['pilot_ids'],phase_limit_seconds=1800)
if prefix=='gentle_refresh':
 assert args.scope!='pilot','The training worker already evaluates the fixed180; reuse it'
 best=c.read(P/'evidence/gentle_refresh/best.json');done=c.read(P/'evidence/gentle_refresh/training_done.json')
 assert best['step']==done['selected_step']==25 and best['checkpoint']==done['selected_checkpoint']
 job.update(input_transform='original',adapter_path=best['checkpoint'],adapter_sha256=best['adapter_sha256'])
if args.scope!='pilot':
 keys=c.rows(P/'keys_selection1817.jsonl');pilot=set(cfg['pilot_ids']);old={r['id'] for r in keys if r['subset']=='old500'}
 if args.scope=='old500':
  job.update(name=prefix+'_500_missing',ids=sorted(old-pilot),analysis_scope='old500',aggregate_jobs=[prefix if prefix=='gentle_refresh' else prefix+'_pilot',prefix+'_500_missing'])
 else:
  job.update(name=prefix+'_1817_missing',ids=sorted({r['id'] for r in keys}-old-pilot),analysis_scope='selection1817',aggregate_jobs=[prefix if prefix=='gentle_refresh' else prefix+'_pilot',prefix+'_500_missing',prefix+'_1817_missing'],inputs='data/inputs_selection1817.jsonl',phase_limit_seconds=7200)
target=P/(job['name']+'.json')
if target.exists():assert c.read(target)==job,'Existing frozen job differs'
else:c.put(target,job)
B=P/'repeat_bundle'
for name in ['tasks/116_research_cycle/generate116.py','tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']:
 p=B/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,p)
if args.scope=='selection1817':
 target=B/'data/inputs_selection1817.jsonl';target.parent.mkdir(exist_ok=True);shutil.copy2(P/'inputs_selection1817.jsonl',target)
bundle_name='repeat_bundle.tar.gz' if prefix=='claim_repeat' else prefix+'_bundle.tar.gz'
with tarfile.open(P/bundle_name,'w:gz',compresslevel=1) as t:
 for p in B.rglob('*'):
  if p.is_file() and (p.relative_to(B).parts[0]!='data' or args.scope=='selection1817'):t.add(p,arcname=p.relative_to(B),recursive=False)
print(job['name'],len(job['ids']),'new IDs; original reference remains unchanged')
