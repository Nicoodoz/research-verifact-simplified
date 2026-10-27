"""Wait for verified MoE weights and completion of9B base controls, then resources only."""
import json,time,subprocess,os
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');out=r/'results';model='qwen3.6-35b-a3b'
def count(p):
 try:return len(p.read_text().splitlines())
 except OSError:return 0
while True:
 ledger=json.loads((out/'gpu_ledger.json').read_text())
 if time.time()-ledger['billing_start_epoch']>7*3600:raise SystemExit('Insufficient time for new probe; hard guard remains active')
 ready=(r/'models'/model/'DOWNLOAD_VERIFIED.json').exists() and (r/'models'/model/'REVISION').exists()
 finished=all(count(out/'qwen3.5-9b/eval'/(arm+'.jsonl'))==180 for arm in ['native_base','label_base'])
 if ready and finished:
  try:os.kill(int((out/'active_worker.pid').read_text()),0)
  except ProcessLookupError:break
 time.sleep(10)
if not (out/'qwen3.5-9b/probe_tail/training_done.json').exists():
 with (r/'qwen3.5-9b_probe_tail.log').open('ab') as log:
  p=subprocess.run(['bash',str(r/'task/run_gpu_live103.sh'),'--model','qwen3.5-9b','--phase','probe_tail'],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=r)
 if p.returncode:raise SystemExit('9B full-training long-tail resource step failed; inspect before MoE')
for phase,arm in [('probe',None),('eval','native_base'),('eval','label_base')]:
 cmd=['bash',str(r/'task/run_gpu_live103.sh'),'--model',model,'--phase',phase]
 if arm:cmd+=['--arm',arm,'--speed']
 name=model+'_'+(arm+'_speed' if arm else phase)+'.log'
 with (r/name).open('ab') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=r)
 if p.returncode:raise SystemExit(f'{phase}/{arm} failed {p.returncode}; inspect logs, no automatic training')
print('MoE resource probe and speed panels completed; no formal training started.',flush=True)
