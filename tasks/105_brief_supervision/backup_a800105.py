"""Parallel private critical backup. Never touches live rolling checkpoints."""
import sys,os,json,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];folder=Path(sys.executable).parent/'Library/bin';dll=os.add_dll_directory(str(folder)) if folder.exists() else None
sys.path.insert(0,str(ROOT/'.local_models/103_lora_selection/tooling/ssh'));import paramiko
auth=json.loads(sys.stdin.readline());auth['hostname']=auth.pop('host')
OUT=ROOT/'.local_models/105_brief_supervision/a800/backup';OUT.mkdir(parents=True,exist_ok=True)
R='/root/autodl-tmp/verifact105';done=set()
def read(s,path):
 with s.open(path) as f:return json.load(f)
def download(s,remote,local,expected):
 if local.exists() and hashlib.sha256(local.read_bytes()).hexdigest()==expected:return
 local.parent.mkdir(parents=True,exist_ok=True);part=local.with_suffix(local.suffix+'.partial');s.get(remote,str(part))
 h=hashlib.sha256()
 with part.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 if h.hexdigest()!=expected:raise ValueError('Critical backup SHA mismatch: '+local.name)
 part.replace(local)
while len(done)<2:
 try:
  client=paramiko.SSHClient();client.set_missing_host_key_policy(paramiko.AutoAddPolicy());client.connect(**auth,look_for_keys=False,allow_agent=False,timeout=10,banner_timeout=10,auth_timeout=10);s=client.open_sftp()
  for arm in ['label_only','evidence_brief']:
   if arm in done:continue
   source=R+'/results/train/'+arm
   try:complete=read(s,source+'/training_done.json')
   except OSError:continue
   assert complete['step']==50 and complete['consumed']==392
   slot=complete['final_slot'];manifest=read(s,source+'/'+slot+'/checkpoint_complete.json');assert manifest['step']==50
   saved={}
   for name,sha in manifest['files'].items():
    if name=='training_state.pt':continue
    download(s,source+'/'+slot+'/'+name,OUT/arm/slot/name,sha);saved[name]=sha
   for name in ['steps.jsonl','training_done.json','adapter_setup.json','resume.json']:
    s.get(source+'/'+name,str(OUT/arm/name))
   (OUT/arm/'critical_backup_verified.json').write_text(json.dumps(dict(epoch=time.time(),arm=arm,step=50,consumed=392,files=saved,remote_final_slot=slot,optimizer_not_downloaded=True,base_weights_not_downloaded=True),indent=2),encoding='utf-8');done.add(arm)
  s.close();client.close()
 except Exception as exc:
  with (OUT/'errors.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(epoch=time.time(),error=type(exc).__name__,message=str(exc)))+'\n')
 time.sleep(25)
(OUT/'both_adapters_verified.json').write_text(json.dumps(dict(epoch=time.time(),arms=sorted(done),all_final_adapter_SHA_verified=True)),encoding='utf-8')
