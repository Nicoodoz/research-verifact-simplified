"""Expose a fully SHA-verified early model while remaining model downloads continue."""
import json,os,time,argparse
from pathlib import Path
from download_ranges103 import digest
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--model',required=True);a=p.parse_args();manifest=json.loads((a.root/'weight_download_manifest.json').read_text());m=manifest[a.model];folder=a.root/'models'/a.model
 while True:
  ready=True
  for w in m['weights']:
   dest=folder/w['filename'];statefile=dest.with_suffix(dest.suffix+'.ranges.json')
   if dest.exists():continue
   if not statefile.exists():ready=False;break
   s=json.loads(statefile.read_text());expected=set(range(s['prefix'],s['bytes'],128*1024*1024))
   if set(s['done'])!=expected:ready=False;break
  if ready:break
  time.sleep(5)
 for w in m['weights']:
  dest=folder/w['filename'];source=dest if dest.exists() else dest.with_suffix(dest.suffix+'.range')
  assert digest(source)==w['sha256'] and source.stat().st_size==w['bytes']
  if not dest.exists():os.link(source,dest)
 (folder/'REVISION').write_text(m['hf_revision']+'\n');(folder/'DOWNLOAD_VERIFIED.json').write_text(json.dumps(m,indent=2))
 print(a.model,'READY_VERIFIED_ALL_WEIGHT_BYTES',flush=True)
if __name__=='__main__':main()
