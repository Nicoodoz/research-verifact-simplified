"""This task's instance-only timer, budget, persistent backup and AutoDL shutdown."""
import argparse,json,time,os,subprocess,signal,tarfile,hashlib,socket
from pathlib import Path
from gpu_worker103 import read,write
def identity():
 assert os.name=='posix','Never shut down the Windows workstation'
 return dict(hostname=socket.gethostname(),machine_id=Path('/etc/machine-id').read_text().strip())
def backup(out):
 # All checkpoints stay on disk; separate archive excludes only re-downloadable weights.
 target=out.parent/'103_results_backup.tar';tmp=target.with_suffix('.tmp')
 with tarfile.open(tmp,'w') as tar:tar.add(out,arcname='103_results')
 tmp.replace(target)
 h=hashlib.sha256()
 with target.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 write(out.parent/'103_backup_manifest.json',dict(archive=str(target),bytes=target.stat().st_size,sha256=h.hexdigest(),utc_epoch=time.time()))
 return target
def shutdown(out):
 state=read(out/'gpu_ledger.json');assert state['task']=='103_lora_selection' and state['identity']==identity()
 elapsed=time.time()-state['billing_start_epoch']
 write(out/'shutdown_requested.json',dict(epoch=time.time(),identity=identity(),scope='this_instance_only',remote_billing_stop_must_be_verified=True,cumulative_seconds=elapsed+state['prior_seconds'],estimated_cumulative_cny=state['prior_gpu_cny']+elapsed/3600*(state['gpu_hourly_cny']+state['storage_hourly_cny'])+state['storage_fixed_cny']))
 backup(out);os.sync()
 os.sync();subprocess.run(['/usr/bin/shutdown','-h','now'],check=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['init','resume','watch','finish','status']);p.add_argument('--out',type=Path,required=True);p.add_argument('--billing-start',type=float);p.add_argument('--gpu-hourly',type=float,default=6.98);p.add_argument('--storage-hourly',type=float,default=0);p.add_argument('--storage-fixed',type=float,default=0);p.add_argument('--prior-seconds',type=float,default=0);p.add_argument('--prior-cny',type=float,default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 if a.action=='init':
  assert a.billing_start is not None and a.billing_start<=time.time()
  assert not (a.out/'gpu_ledger.json').exists(),'Never reset cumulative budget; preserve ledger on resume'
  write(a.out/'gpu_ledger.json',dict(task='103_lora_selection',identity=identity(),billing_start_epoch=a.billing_start,gpu_hourly_cny=a.gpu_hourly,storage_hourly_cny=a.storage_hourly,storage_fixed_cny=a.storage_fixed,prior_seconds=a.prior_seconds,prior_gpu_cny=a.prior_cny,cap_cny=60,max_seconds=28800));return
 state=read(a.out/'gpu_ledger.json');assert state['identity']==identity()
 if a.action=='resume':
  assert a.billing_start is not None and a.billing_start<=time.time();last=read(a.out/'shutdown_requested.json')
  write(a.out/f'gpu_ledger_before_resume_{int(time.time())}.json',state)
  state.update(billing_start_epoch=a.billing_start,prior_seconds=max(last['cumulative_seconds'],a.prior_seconds),prior_gpu_cny=max(last['estimated_cumulative_cny'],a.prior_cny),storage_fixed_cny=a.storage_fixed,gpu_hourly_cny=a.gpu_hourly,storage_hourly_cny=a.storage_hourly)
  write(a.out/'gpu_ledger.json',state);return
 if a.action=='finish':shutdown(a.out);return
 while True:
  elapsed=time.time()-state['billing_start_epoch'];cost=state['prior_gpu_cny']+elapsed/3600*(state['gpu_hourly_cny']+state['storage_hourly_cny'])+state['storage_fixed_cny']
  remaining=min(28800-state['prior_seconds']-elapsed,(60-cost)/max(.001,state['gpu_hourly_cny']+state['storage_hourly_cny'])*3600)
  write(a.out/'gpu_cost_status.json',dict(elapsed_seconds=elapsed+state['prior_seconds'],estimated_cost_cny=cost,remaining_seconds=remaining))
  if a.action=='status':print(json.dumps(read(a.out/'gpu_cost_status.json')));return
  if remaining<300:
   pidfile=a.out/'active_worker.pid'
   if pidfile.exists():
    pid=int(pidfile.read_text())
    try:os.kill(pid,signal.SIGTERM)
    except ProcessLookupError:pass
   time.sleep(max(0,min(90,remaining-120)));shutdown(a.out);return
  time.sleep(15)
if __name__=='__main__':main()
