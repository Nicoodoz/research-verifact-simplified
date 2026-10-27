"""Small evidence snapshot only: never include base weights or optimizer/adapter duplicates."""
import tarfile,time,json,hashlib
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');target=r/'evidence_latest.tar.gz';tmp=target.with_suffix('.tmp');start=time.time()
def keep(info):return None if any(part.startswith('checkpoint-') for part in Path(info.name).parts) else info
with tarfile.open(tmp,'w:gz') as t:
 t.add(r/'results',arcname='results',filter=keep)
 for p in r.glob('*.log'):t.add(p,arcname='logs/'+p.name)
 t.add(r/'task',arcname='task',filter=lambda info:None if '__pycache__' in info.name else info)
 for name in ['installed_gpu.lock','weight_download_manifest.json','weight_download_manifest_38.json']:
  if (r/name).exists():t.add(r/name,arcname='metadata/'+name)
tmp.replace(target);data=target.read_bytes();print(json.dumps(dict(bytes=len(data),seconds=time.time()-start,sha256=hashlib.sha256(data).hexdigest(),base_weights_included=False,checkpoints_included=False)))
