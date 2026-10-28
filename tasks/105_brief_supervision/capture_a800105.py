"""Capture small private evidence after completion; no raw weights or optimizer."""
import sys,os,json,time,hashlib,tarfile,shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];dllpath=Path(sys.executable).parent/'Library/bin';dll=os.add_dll_directory(str(dllpath)) if dllpath.exists() else None
sys.path.insert(0,str(ROOT/'.local_models/103_lora_selection/tooling/ssh'));import paramiko
auth=json.loads(sys.stdin.readline());auth['hostname']=auth.pop('host');OUT=ROOT/'.local_models/105_brief_supervision/a800';OUT.mkdir(exist_ok=True)
script=r'''import pathlib,tarfile,hashlib,json,time
r=pathlib.Path('/root/autodl-tmp/verifact105');w=r/'results'
if not (r/'budget/finish_requested.json').exists():print(json.dumps({'ready':False}));raise SystemExit
p=r/'a800_evidence.tar.gz'
with tarfile.open(p,'w:gz') as t:
 for f in sorted(w.rglob('*')):
  if f.is_file() and f.suffix in ('.json','.jsonl','.log') and not f.name.endswith('.tmp'):t.add(f,arcname=f.relative_to(r))
 for f in sorted((r/'budget').glob('*.json')):t.add(f,arcname=f.relative_to(r))
 for f in r.iterdir():
  if f.is_file() and f.suffix in ('.json','.log','.py','.sh'):t.add(f,arcname=f.name)
print(json.dumps(dict(ready=True,path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),epoch=time.time())))
'''
while True:
 try:
  client=paramiko.SSHClient();client.set_missing_host_key_policy(paramiko.AutoAddPolicy());client.connect(**auth,look_for_keys=False,allow_agent=False,timeout=10,banner_timeout=10,auth_timeout=10)
  _,o,e=client.exec_command('/root/miniconda3/bin/python -c '+shlex.quote(script),timeout=30);info=json.loads(o.read().decode())
  if info['ready']:
   s=client.open_sftp();target=OUT/'a800_evidence.tar.gz';s.get(info['path'],str(target));s.close();client.close();assert hashlib.sha256(target.read_bytes()).hexdigest()==info['sha256']
   dest=OUT/'evidence';dest.mkdir(exist_ok=True)
   with tarfile.open(target) as t:
    for m in t.getmembers():
     final=(dest/m.name).resolve();assert final.is_relative_to(dest.resolve()) and not m.issym() and not m.islnk()
    t.extractall(dest)
   (OUT/'evidence_backup_verified.json').write_text(json.dumps(info,indent=2),encoding='utf-8');break
  client.close()
 except Exception as exc:
  with (OUT/'capture_errors.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(epoch=time.time(),error=type(exc).__name__,message=str(exc)))+'\n')
 time.sleep(25)
