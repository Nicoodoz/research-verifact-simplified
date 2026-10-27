"""User-directed schedule: resources -> budget decision -> training, then remaining controls."""
import json,time,subprocess,os,hashlib
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');out=r/'results';model='qwen3.6-35b-a3b'
def count(p):
 try:return len(p.read_text().splitlines())
 except OSError:return 0
while not all(count(out/model/'eval'/(arm+'_speed.jsonl'))==6 for arm in ['native_base','label_base']):
 ledger=json.loads((out/'gpu_ledger.json').read_text())
 if time.time()-ledger['billing_start_epoch']>7*3600:raise SystemExit('Resource tests not ready within scheduling time; no automatic training')
 time.sleep(5)
while True:
 try:os.kill(int((out/'active_worker.pid').read_text()),0)
 except ProcessLookupError:break
 time.sleep(2)
py='/root/miniconda3/bin/python'
for script in ['gpu_bridge_check103.py','gpu_plan_after_probe103.py']:
 subprocess.run([py,str(r/'task'/script),'--out',str(out),'--bundle',str(r/'bundle')],check=True,cwd=r)
decision=json.loads((out/'scale_decision.json').read_text());assert decision['status']=='GO';limit=decision['samples_each']
assert not any((out/m/'train/steps.jsonl').exists() for m in ['qwen3.5-9b',model])
files=['gpu_worker103.py','gpu_batch103.py','gpu_plan_after_probe103.py','run_gpu_live103.sh','train_priority_queue103.py']
freeze=dict(epoch=time.time(),samples_each=limit,no_classification_accuracy_inspected=True,no_third_model=True,sha256={f:hashlib.sha256((r/'task'/f).read_bytes()).hexdigest() for f in files})
(out/'training_execution_freeze.json').write_text(json.dumps(freeze,indent=2))
jobs=[(model,'train',None),(model,'eval','label_base'),(model,'eval','lora_label'),('qwen3.5-9b','train',None),('qwen3.5-9b','eval','lora_label'),('qwen3.5-9b','eval','native_base'),(model,'eval','native_base')]
for m,phase,arm in jobs:
 cmd=['bash',str(r/'task/run_gpu_live103.sh'),'--model',m,'--phase',phase]
 if arm:cmd+=['--arm',arm]
 else:cmd+=['--limit',str(limit)]
 (out/'operator_status.json').write_text(json.dumps(dict(message=f'统一冻结每模型{limit}条训练；当前执行{m} / {phase} / {arm or "LoRA"}。原始60元/8小时预算不重置，尚缺未训练基线在训练后从冻结初始权重补齐；不查看成绩调整方案。'),ensure_ascii=False))
 name=m+'_'+(arm if arm else phase)+'.log'
 with (r/name).open('ab') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=r)
 if p.returncode:raise SystemExit(f'{m}/{phase}/{arm} failed {p.returncode}; preserve first answers/checkpoints and inspect')
 (out/'last_completed_stage.json').write_text(json.dumps(dict(epoch=time.time(),model=m,phase=phase,arm=arm)))
(out/'gpu_all_work_done.json').write_text(json.dumps(dict(epoch=time.time(),samples_each=limit,required_arms_complete=True)))
print('All required GPU work finished; finalize backup and stop this instance now',flush=True)
