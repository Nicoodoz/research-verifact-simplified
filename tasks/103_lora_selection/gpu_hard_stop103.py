"""Independent hard deadline: a slow archive must not extend GPU billing."""
import argparse,time,os,signal,subprocess
from pathlib import Path
from gpu_lifecycle103 import identity,read,write
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 state=read(a.out/'gpu_ledger.json');assert state['task']=='103_lora_selection' and state['identity']==identity()
 while True:
  state=read(a.out/'gpu_ledger.json');assert state['identity']==identity()
  elapsed=time.time()-state['billing_start_epoch'];price=state['gpu_hourly_cny']+state['storage_hourly_cny'];cost=state['prior_gpu_cny']+state['storage_fixed_cny']+elapsed*price/3600
  remain=min(28800-state['prior_seconds']-elapsed,(60-cost)/max(price,.001)*3600)
  if remain<=75:
   pidfile=a.out/'active_worker.pid'
   if pidfile.exists():
    try:os.kill(int(pidfile.read_text()),signal.SIGTERM)
    except ProcessLookupError:pass
   # The ordinary watcher has already requested a save at T-300 seconds.
   # Original outputs/checkpoints persist even if the extra tar is unfinished.
   write(a.out/'hard_shutdown_requested.json',dict(epoch=time.time(),estimated_cost_cny=cost,remaining_seconds=remain,identity=identity(),reason='hard cap takes precedence over a slow extra archive',data_deleted=False))
   os.sync();time.sleep(max(0,min(20,remain-45)))
   subprocess.run(['/usr/bin/shutdown','-h','now'],check=True);return
  time.sleep(min(10,remain-75))
if __name__=='__main__':main()
