"""Run the two frozen speed panels after a successful probe; never inspect GT."""
import argparse,json,os,subprocess,time
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--model',required=True);p.add_argument('--wait-pid',type=int,required=True);a=p.parse_args()
out=a.root/'results';work=out/a.model
while True:
 try:os.kill(a.wait_pid,0)
 except ProcessLookupError:break
 time.sleep(5)
if not (work/'probe/training_done.json').exists():raise SystemExit('Probe did not finish: no automatic next phase')
env=os.environ.copy();env.update(OMP_NUM_THREADS='8',MAX_JOBS='8',TORCHINDUCTOR_COMPILE_THREADS='8',TORCH_DISABLE_ADDR2LINE='1',HF_HUB_OFFLINE='1',HF_HOME=str(a.root/'cache'),TMPDIR=str(a.root/'tmp'))
for arm in ['native_base','label_base']:
 cmd=[str(a.root/'venv103/bin/python'),'-u',str(a.root/'task/gpu_batch103.py'),'--bundle',str(a.root/'bundle'),'--out',str(out),'--model-root',str(a.root/'models'),'--model',a.model,'--phase','eval','--arm',arm,'--speed']
 log=a.root/(a.model+'_'+arm+'_speed.log')
 with log.open('ab') as f:
  proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,env=env,cwd=a.root)
  (out/'active_worker.pid').write_text(str(proc.pid))
  rc=proc.wait()
 if rc:raise SystemExit(f'{arm} failed with exit {rc}; inspect preserved log')
print('Both frozen speed panels completed; no formal training started',flush=True)
