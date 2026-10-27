"""While candidate choice is pending, finish only the required35B base controls."""
import os,time,subprocess,json
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');out=r/'results';model='qwen3.6-35b-a3b'
pid=int((out/'active_worker.pid').read_text())
while True:
 try:os.kill(pid,0)
 except ProcessLookupError:break
 time.sleep(3)
assert (out/model/'train/training_done.json').exists(),'Training interrupted: inspect before any further work'
for arm in ['label_base','lora_label','native_base']:
 (out/'operator_status.json').write_text(json.dumps(dict(message=f'35B训练已完成；当前完成35B {arm}必要对照，同时下载3.8-27B。用户正在选择后续候选，暂不启动9B或27B训练。最终适配器及最新恢复检查点并行回传，中间检查点保留在实例。'),ensure_ascii=False))
 with (r/(model+'_'+arm+'.log')).open('ab') as log:
  p=subprocess.run(['bash',str(r/'task/run_gpu_live103.sh'),'--model',model,'--phase','eval','--arm',arm],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=r)
 if p.returncode:raise SystemExit(f'{arm} failed; preserve all responses')
print('Required35B base controls complete; candidate/training choice remains with user',flush=True)
