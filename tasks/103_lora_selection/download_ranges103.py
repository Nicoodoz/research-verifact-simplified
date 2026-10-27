"""Global16 HTTP Range workers, persistent verified-prefix/chunk state, exact HF SHA."""
import json,time,hashlib,os,threading,concurrent.futures as cf,urllib.request,urllib.parse,argparse
from pathlib import Path
LOCK=threading.Lock()
def atomic(p,x):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x));tmp.replace(p)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--manifest',type=Path);a=ap.parse_args();manifest=json.loads((a.manifest or a.root/'weight_download_manifest.json').read_text());jobs=[];files=[];start=time.monotonic()
 for model,m in manifest.items():
  folder=a.root/'models'/model
  for w in m['weights']:
   dest=folder/w['filename'];part=dest.with_suffix(dest.suffix+'.partial');working=dest.with_suffix(dest.suffix+'.range');statefile=dest.with_suffix(dest.suffix+'.ranges.json')
   if dest.exists():assert digest(dest)==w['sha256'];continue
   if statefile.exists():state=json.loads(statefile.read_text())
   else:
    prefix=part.stat().st_size if part.exists() else 0
    if part.exists():part.replace(working)
    with working.open('ab'):pass
    with working.open('r+b') as f:f.truncate(w['bytes'])
    state=dict(prefix=prefix,done=[],bytes=w['bytes'],sha256=w['sha256']);atomic(statefile,state)
   url=f"https://modelscope.cn/api/v1/models/{m['repo']}/repo?"+urllib.parse.urlencode({'Revision':w['modelscope_file_revision'],'FilePath':w['filename']})
   fd=os.open(working,os.O_RDWR);record=dict(dest=dest,working=working,statefile=statefile,state=state,fd=fd,weight=w);files.append(record)
   for lo in range(state['prefix'],w['bytes'],128*1024*1024):
    hi=min(w['bytes']-1,lo+128*1024*1024-1)
    if lo not in state['done']:jobs.append((record,url,lo,hi))
 completed=[0];transferred=[0]
 def fetch(job):
  r,url,lo,hi=job
  for attempt in range(4):
   try:
    req=urllib.request.Request(url,headers={'Range':f'bytes={lo}-{hi}','User-Agent':'VeriFact103-fixed-SHA-range-download'})
    with urllib.request.urlopen(req,timeout=120) as res:
     assert res.status==206 and res.headers['Content-Range'].startswith(f'bytes {lo}-{hi}/')
     offset=lo
     for block in iter(lambda:res.read(1024*1024),b''):
      assert offset+len(block)<=hi+1
      view=memoryview(block)
      while view:
       n=os.pwrite(r['fd'],view,offset);offset+=n;view=view[n:]
     assert offset==hi+1
    with LOCK:
     r['state']['done'].append(lo);atomic(r['statefile'],r['state']);completed[0]+=1;transferred[0]+=hi-lo+1
     if completed[0]%16==0:print(json.dumps(dict(chunks=completed[0],total_chunks=len(jobs),GiB=transferred[0]/2**30,MiB_per_second=transferred[0]/2**20/(time.monotonic()-start))),flush=True)
    return
   except Exception as e:
    if attempt==3:raise
    print(json.dumps(dict(file=r['dest'].name,offset=lo,attempt=attempt+1,error=type(e).__name__)),flush=True);time.sleep(2*(attempt+1))
 with cf.ThreadPoolExecutor(max_workers=32) as pool:list(pool.map(fetch,jobs))
 for r in files:
  os.fsync(r['fd']);os.close(r['fd']);assert digest(r['working'])==r['weight']['sha256'];r['working'].replace(r['dest'])
 for model,m in manifest.items():
  folder=a.root/'models'/model
  for w in m['weights']:assert (folder/w['filename']).stat().st_size==w['bytes']
  (folder/'REVISION').write_text(m['hf_revision']+'\n');(folder/'DOWNLOAD_VERIFIED.json').write_text(json.dumps(m,indent=2));print(model,'all_shards_SHA_verified',flush=True)
if __name__=='__main__':main()
