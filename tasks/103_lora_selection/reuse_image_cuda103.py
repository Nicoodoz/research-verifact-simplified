"""Copy only exact locked CUDA distributions from chosen base image, verify RECORD."""
import importlib.metadata as md,re,hashlib,base64,shutil,json,argparse
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--image28',action='store_true');args=ap.parse_args()
root=Path('/root/autodl-tmp/verifact103');target=root/'venv103/lib/python3.12/site-packages';lock=(root/'task'/('requirements_gpu_image28.lock' if args.image28 else 'requirements_gpu.lock')).read_text();pins=dict(re.findall(r'^([a-zA-Z0-9_-]+)==([^\s\\]+)',lock,re.M));records=[]
for d in md.distributions():
 name=d.metadata['Name'].lower().replace('_','-')
 if not (name.startswith('nvidia-') or (args.image28 and name in ['torch','torchvision','triton'])) or pins.get(name)!=d.version.split('+')[0]:continue
 count=0;size=0
 for f in d.files or []:
  if str(f).endswith('.pyc'):continue
  src=Path(d.locate_file(f));dest=(target/str(f)).resolve()
  assert dest.is_relative_to(root/'venv103'),dest
  if not src.is_file():continue
  if f.hash:
   h=hashlib.new(f.hash.mode)
   with src.open('rb') as s:
    for chunk in iter(lambda:s.read(16*1024*1024),b''):h.update(chunk)
   assert base64.urlsafe_b64encode(h.digest()).rstrip(b'=').decode()==f.hash.value,src
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);count+=1;size+=src.stat().st_size
 records.append(dict(name=name,version=d.version,files=count,bytes=size,RECORD_verified=True));print(name,d.version,size,flush=True)
(root/'results'/('image28_reuse.json' if args.image28 else 'image_cuda_reuse.json')).write_text(json.dumps(records,indent=2)+'\n')
