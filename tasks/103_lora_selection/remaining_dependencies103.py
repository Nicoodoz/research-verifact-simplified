"""Retain full hash lock for downloads; image packages separately RECORD-verified."""
import re,importlib.metadata as md,json
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');text=(r/'task/requirements_gpu_image28.lock').read_text();blocks=re.split(r'(?m)(?=^[A-Za-z0-9_.-]+==)',text);keep=[];skipped=[]
for b in blocks:
 m=re.match(r'([A-Za-z0-9_.-]+)==([^\s\\]+)',b)
 if not m:keep.append(b);continue
 try:version=md.version(m[1])
 except md.PackageNotFoundError:version=None
 if version and version.split('+')[0]==m[2]:skipped.append(dict(name=m[1],version=version))
 else:keep.append(b)
(r/'task/requirements_remaining.lock').write_text(''.join(keep));(r/'results/already_installed_dependencies.json').write_text(json.dumps(skipped,indent=2));print('remaining_packages',sum(bool(re.match(r'[A-Za-z0-9_.-]+==',b)) for b in keep),'verified_existing',len(skipped))
