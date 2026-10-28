"""Authorized operational continuation: preserved scientific bundle, manual shutdown."""
from pathlib import Path
import sys,json,time,os,signal,subprocess
ROOT=Path('/root/autodl-tmp/verifact105');B=ROOT/'bundle';W=ROOT/'results';L=ROOT/'budget/ledger.json'
sys.path.insert(0,str(B/'tasks/105_brief_supervision'))
import common105 as c
import budget105 as budget
START=1793171160.0 # User15:06 UTC+08,2026-10-28
PRIOR=4.503952316301399;PRIOR_GPU=2277.2666959762573

def setup():
 if not L.exists():
  c.put(L,dict(task=105,cap_cny=20,operating_line_cny=18,API_cap_cny=0,new_disk_allowed=False,closed_sessions=[],adjustments_cny=PRIOR,
   active=dict(kind='gpu',hourly_cny=7.98,billing_start_epoch=START,machine_id=budget.machine()),shutdown_reserve_cny=2,
   prior_GPU_seconds=PRIOR_GPU,unknown_prior_intervals_retained=True,prior_lower_bound_only=True,prior_source='/root/verifact_image/105/cost_checkpoint',
   manual_shutdown_only=True,created_utc=c.utc(),budget_reset=False))
 c.put(ROOT/'a800_status.json',dict(stage='镜像恢复完成；A800最长输入梯度/显存预检，尚未更新optimizer。',manual_shutdown_only=True))

def watch():
 while True:
  s=c.read(L);now=time.time();used=budget.total(s)
  c.put(L.parent/'watchdog_ready.json',dict(pid=os.getpid(),ledger=str(L.resolve()),machine_id=budget.machine(),heartbeat_epoch=now))
  finish=(L.parent/'finish_requested.json').exists()
  if used>=17.8 or PRIOR_GPU+now-START>=148*60 or finish:
   s['shutdown_requested']=dict(utc=c.utc(),reason='finish' if finish else 'budget_time_stop',cost_at_request_cny=used,manual_shutdown_only=True)
   c.put(L,s);c.put(ROOT/'manual_shutdown_needed.json',dict(utc=c.utc(),reason=s['shutdown_requested']['reason'],GPU_still_on=True))
   for name in ['gpu_worker.lock','supervisor.lock']:
    p=W/name
    if p.exists():
     try:pid=int(p.read_text());cmd=Path('/proc')/str(pid)/'cmdline';raw=cmd.read_bytes() if cmd.exists() else b''
     except (OSError,ValueError):continue
     if b'worker105.py' in raw:os.kill(pid,signal.SIGTERM)
   c.put(ROOT/'a800_status.json',dict(stage='工作已停止/完成，请用户手动关机；程序未调用关机。',manual_shutdown_only=True));return
  time.sleep(3)

def launch(mode):
 setup();env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',OMP_NUM_THREADS='8',MAX_JOBS='8',TORCHINDUCTOR_COMPILE_THREADS='8',TORCH_DISABLE_ADDR2LINE='1')
 if mode=='gate':
  log=(ROOT/'watch_manual.log').open('ab');subprocess.Popen([sys.executable,'-u',__file__,'watch','budget105.py'],stdout=log,stderr=log,stdin=subprocess.DEVNULL,start_new_session=True);log.close();time.sleep(1)
  command=[sys.executable,'-u',str(B/'tasks/105_brief_supervision/worker105.py'),'--mode','gate']
 else:command=[sys.executable,'-u',str(B/'tasks/105_brief_supervision/run_all105.py')]
 command+=['--bundle',str(B),'--work',str(W),'--model-dir','/root/verifact_image/models/qwen3.5-9b','--ledger',str(L)]
 log=(ROOT/('gate105.log' if mode=='gate' else 'run105.log')).open('ab');p=subprocess.Popen(command,env=env,stdout=log,stderr=log,stdin=subprocess.DEVNULL,start_new_session=True);log.close()
 c.put(ROOT/(mode+'_launch.json'),dict(pid=p.pid,utc=c.utc(),command=command,manual_shutdown_only=True));print(p.pid)

if __name__=='__main__':
 if sys.argv[1]=='watch':watch()
 else:launch(sys.argv[1])
