"""Finish kernel verification and run unchanged frozen-ID base controls, no GT scoring."""
import os,json,sys,time,subprocess,hashlib
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');out=r/'results';model='qwen3.5-9b'
wheel=r/'causal_conv1d-1.7.0+cu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl'
for _ in range(120):
 if wheel.exists() and wheel.stat().st_size==196377090:break
 time.sleep(5)
else:raise SystemExit('Kernel upload incomplete; no implicit environment change')
assert hashlib.sha256(wheel.read_bytes()).hexdigest()=='a1fcd5d022b67ddfc9e1c291f890004c1c081a03d66b532f6eebe31219168e0e'
py=str(r/'venv103/bin/python');env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',OMP_NUM_THREADS='8',MAX_JOBS='8',TORCHINDUCTOR_COMPILE_THREADS='8',TORCH_DISABLE_ADDR2LINE='1',HF_HOME=str(r/'cache'),TMPDIR=str(r/'tmp'))
subprocess.run([py,'-m','pip','install','--no-deps',str(wheel)],check=True,env=env)
subprocess.run([py,str(r/'task/verify_causal_kernel103.py')],check=True,env=env)
subprocess.run([py,'-m','pip','check'],check=True,env=env)
(out/'installed_gpu_with_causal.lock').write_bytes(subprocess.check_output([py,'-m','pip','freeze','--all']))
for arm in ['native_base','label_base']:
 rows=[json.loads(s) for s in (out/model/'eval'/(arm+'_speed.jsonl')).read_text().splitlines()]
 assert len(rows)==6 and all(v['parsed']['verdict'] is not None and v['parsed'].get('finish_reason')=='stop' for v in rows)
# Required baseline evaluation is independent of choosing train512 vs train256.
for arm in ['label_base','native_base']:
 cmd=[py,'-u',str(r/'task/gpu_batch103.py'),'--bundle',str(r/'bundle'),'--out',str(out),'--model-root',str(r/'models'),'--model',model,'--phase','eval','--arm',arm]
 with (r/(model+'_'+arm+'.log')).open('ab') as log:
  p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,env=env,cwd=r)
  (out/'active_worker.pid').write_text(str(p.pid));rc=p.wait()
 if rc:raise SystemExit(f'{arm} exit {rc}; preserve first answers and inspect')
print('Both9B base controls complete. No formal training was started.',flush=True)
