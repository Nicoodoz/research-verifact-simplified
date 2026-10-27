"""Same frozen HF weight bytes via verified ModelScope file revisions; resumable."""
import argparse,json,time,urllib.request,urllib.parse,hashlib,concurrent.futures as cf
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
 return h.hexdigest()
def download(item,folder,repo):
 dest=folder/item['filename'];part=dest.with_suffix(dest.suffix+'.partial');begin=time.monotonic()
 if dest.exists():
  assert dest.stat().st_size==item['bytes'] and sha(dest)==item['sha256'];return
 url=f'https://modelscope.cn/api/v1/models/{repo}/repo?'+urllib.parse.urlencode({'Revision':item['modelscope_file_revision'],'FilePath':item['filename']})
 for attempt in range(3):
  try:
   offset=part.stat().st_size if part.exists() else 0
   if offset==item['bytes']:
    assert sha(part)==item['sha256'];part.replace(dest);return
   headers={'User-Agent':'VeriFact103-fixed-checkpoint'}
   if offset:headers['Range']=f'bytes={offset}-'
   with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=90) as response:
    if offset:assert response.status==206,'Server must honor resume range'
    with part.open('ab' if offset else 'wb') as f:
     for block in iter(lambda:response.read(8*1024*1024),b''):f.write(block)
   assert part.stat().st_size==item['bytes'] and sha(part)==item['sha256'],'Weight size/SHA mismatch'
   part.replace(dest);print(json.dumps(dict(file=item['filename'],bytes=item['bytes'],seconds=time.monotonic()-begin,sha256_verified=True)),flush=True);return
  except Exception as e:
   print(json.dumps(dict(file=item['filename'],attempt=attempt+1,error=type(e).__name__,detail=str(e))),flush=True)
   if attempt==2:raise
   time.sleep(2*(attempt+1))
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--model-root',type=Path,required=True);a=p.parse_args();manifest=json.loads(a.manifest.read_text())
 for name,m in manifest.items():
  folder=a.model_root/name;folder.mkdir(parents=True,exist_ok=True)
  for file,h in m['small_file_sha256'].items():assert sha(folder/file)==h,file
  with cf.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda x:download(x,folder,m['repo']),m['weights']))
  (folder/'REVISION').write_text(m['hf_revision']+'\n')
  (folder/'DOWNLOAD_VERIFIED.json').write_text(json.dumps(m,indent=2)+'\n')
  print(json.dumps(dict(model=name,complete=True,source='ModelScope byte-identical frozen HF weights')),flush=True)
if __name__=='__main__':main()
