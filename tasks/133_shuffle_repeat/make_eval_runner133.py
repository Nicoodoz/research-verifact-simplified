"""Create launch/monitor helpers after a missing-only133 evaluation is prepared."""
from pathlib import Path
import argparse,ast,json
R=Path(__file__).resolve().parents[2];Q=R/'.local_models/133_shuffle_repeat/run20261031'
p=argparse.ArgumentParser();p.add_argument('--scope',choices=['screen160','old500','full1817'],required=True);p.add_argument('--check-only',action='store_true');a=p.parse_args()
if not a.check_only:json.loads((Q/a.scope/'job.json').read_text())
remote='/root/autodl-tmp/verifact133_eval_'+a.scope
start='''from pathlib import Path
import json,subprocess,tarfile,time
p=Path(REMOTE)
if (p/'pid.json').exists():raise RuntimeError('Existing evaluation launch; inspect rather than duplicate')
if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
with tarfile.open(p/'bundle.tar.gz') as t:t.extractall(p,filter='data')
log=(p/'run.log').open('ab')
child=subprocess.Popen(['/root/verifact_image/envs/venv103/bin/python','-u','-B',str(p/'tasks/133_shuffle_repeat/infer133.py')],cwd=p,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
record=dict(pid=child.pid,epoch=time.time(),task=133,phase=PHASE,no_shutdown=True)
(p/'pid.json').write_text(json.dumps(record));print(json.dumps(record))
'''.replace('REMOTE',repr(remote)).replace('PHASE',repr(a.scope))
monitor='''from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,os,shlex,subprocess,sys,tarfile,time
Q=Path(__file__).resolve().parent;R=Q.parents[2];O=R/'outputs/133_shuffle_repeat';remote=REMOTE;scope=SCOPE
dll=Path(sys.executable).parent/'Library/bin';handle=os.add_dll_directory(str(dll)) if dll.exists() else None
sys.path.insert(0,str(R/'.local_models/103_lora_selection/tooling/ssh'));import paramiko
auth=json.loads(sys.stdin.readline());session=json.loads((Q/'session.json').read_text());job=json.loads((Q/scope/'job.json').read_text());client=None
probe="""from pathlib import Path
import json,subprocess,time
p=Path(REMOTE);v={}
for n in ['pid.json','results/progress.json','results/complete.json','results/failure.json','controller_done.json']:
 f=p/n
 if f.exists():v[n]=json.loads(f.read_text())
v['controller_alive']=Path('/proc/'+str(v['pid.json']['pid'])).exists()
v['gpu']=subprocess.getoutput('nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader')
v['compute']=subprocess.getoutput('nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader')
v['epoch']=time.time();print(json.dumps(v))
"""
def connect():
 global client
 if client:client.close()
 client=paramiko.SSHClient();client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
 client.connect(auth['host'],port=auth['port'],username=auth['user'],password=auth['password'],timeout=20,banner_timeout=20,auth_timeout=20,look_for_keys=False,allow_agent=False)
def execute(src):
 _,o,e=client.exec_command('/root/verifact_image/envs/venv103/bin/python -c '+shlex.quote(src),timeout=120)
 text=o.read().decode();err=e.read().decode()
 if o.channel.recv_exit_status():raise RuntimeError(err[-1500:])
 return text
try:
 connect();previous=None;failures=0
 while True:
  try:
   v=json.loads(execute(probe));failures=0;(Q/('live_'+scope+'.json')).write_text(json.dumps(v,indent=2)+'\\n',encoding='utf-8')
   pr=v.get('results/progress.json',{});stage=pr.get('stage','starting');counts=pr.get('counts',{});n=sum(counts.values());eta=pr.get('remaining_seconds')
   totals={arm:counts.get(arm,0)+job['prior_per_arm'][arm] for arm in job['arms']};cost=(time.time()-session['start_epoch'])*1.58/3600;stamp=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
   terminal='controller_done.json' in v or not v['controller_alive']
   lines=['# 133 实时进度','',stamp,'',f'阶段：{stage}；本阶段新增{n}/{sum(job["expected_per_arm"].values())}。',str(totals)+' / 每输入目标'+str(job['target_N']),'',('预计剩余约'+str(round(eta/60,1))+'分钟。') if eta is not None else '加载或首批阶段，不外推。','',f'新增窗口GPU估算¥{cost:.3f}/20；API原80元累计0。',f"GPU：{v['gpu']}；进程：{v['compute'] or '无'}。",'阻塞：'+str(v.get('results/failure.json','无已确认阻塞。')),'不关机、不释放。','']
   (O/'progress.md').write_text('\\n'.join(lines),encoding='utf-8')
   cursor=(stage,n//12,terminal)
   if cursor!=previous:print(json.dumps(dict(stage=stage,new_done=n,totals=totals,GPU_CNY=round(cost,3),ETA_min=None if eta is None else round(eta/60,1),terminal=terminal)),flush=True);previous=cursor
   if terminal:
    src="from pathlib import Path;import tarfile;p=Path("+repr(remote)+");t=tarfile.open(p/'return_eval.tar.gz','w:gz',compresslevel=1);t.add(p/'results',arcname='.',recursive=True);t.close()"
    execute(src)
    with client.open_sftp() as sftp:sftp.get(remote+'/return_eval.tar.gz',str(Q/('return_'+scope+'.tar.gz')))
    with tarfile.open(Q/('return_'+scope+'.tar.gz')) as t:t.extractall(Q/'evidence'/scope,filter='data')
    if 'results/complete.json' in v:
     cmd=[sys.executable,'-B',str(R/'tasks/133_shuffle_repeat/analyze133.py'),'--scope',scope]
     if scope=='full1817':cmd+=['--bootstrap']
     with (Q/('analysis_'+scope+'.log')).open('ab') as log:rc=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT).returncode
     print(json.dumps(dict(analysis_exit=rc,returned=True)),flush=True)
    else:print(json.dumps(dict(returned=True,incomplete=True)),flush=True)
    break
   time.sleep(25)
  except (OSError,EOFError,paramiko.SSHException,RuntimeError) as e:
   failures+=1;print(json.dumps(dict(observation_retry=failures,error=type(e).__name__)),flush=True)
   if failures>=5:raise
   time.sleep(5);connect()
finally:
 if client:client.close()
 auth.clear()
'''.replace('REMOTE',repr(remote)).replace('SCOPE',repr(a.scope))
ast.parse(start);ast.parse(monitor)
if not a.check_only:
 (Q/('start_'+a.scope+'.py')).write_text(start,encoding='utf-8');(Q/('monitor_'+a.scope+'.py')).write_text(monitor,encoding='utf-8')
print(remote)
