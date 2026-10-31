"""Read first receipts from133 without replacing invalid answers."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[2];Q=R/'.local_models/133_shuffle_repeat/run20261031'
ARMS=('plain104','claim_repeat')
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]
def receipts():
 result={arm:{} for arm in ARMS}
 def keep(arm,row):
  i=row['id'];old=result[arm].get(i)
  if old is not None and (old['content'],old['parsed'])!=(row['content'],row['parsed']):raise ValueError('Conflicting first receipt: '+i)
  result[arm][i]=row
 for f in (Q/'evidence/shuffle_repeat/batches').glob('*.json'):
  for row in read(f)['records']:keep('plain104',row)
 for scope in ['screen160','old500','full1817']:
  for arm in ARMS:
   for f in (Q/'evidence'/scope/arm).glob('*.json'):
    row=read(f)
    if 'id' in row:keep(arm,row)
 return result
def target_ids(scope):
 keys={r['id']:r for r in rows(R/'.local_models/134_author_baselines/keys.jsonl')}
 if scope=='screen160':return keys,set(read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
 return keys,{i for i,r in keys.items() if scope=='full1817' or r['old_panel'] in ('natural','pressure')}
