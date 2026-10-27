"""Latest user scope: finish three512-example adapters, no inference/evaluation/transfers."""
import json,os,time,subprocess,hashlib
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');out=r/'results';models=['qwen3.6-35b-a3b','qwen3.5-9b','qwen3.8-27b']
def read(p):return json.loads(p.read_text())
def check(m):
 work=out/m/'train';done=read(work/'training_done.json');assert done['samples']==512 and done['steps']==64
 update=read(work/'weight_update.json');assert update['any_update']
 checkpoint=Path(read(work/'resume.json')['checkpoint']);assert checkpoint.resolve().parent==(work.resolve())
 assert (checkpoint/'adapter_model.safetensors').stat().st_size>0
 config=read(checkpoint/'adapter_config.json');assert config['r']==16 and config['lora_alpha']==32
 assert (r/'models'/m/'REVISION').read_text().strip()==read(r/'bundle/model_metadata.json')[m]['revision']
 return dict(model=m,samples=512,steps=64,adapter=str(checkpoint/'adapter_model.safetensors'),config=str(checkpoint/'adapter_config.json'),checkpoint=str(checkpoint),revision=(r/'models'/m/'REVISION').read_text().strip(),adapter_bytes=(checkpoint/'adapter_model.safetensors').stat().st_size,any_update=True)
pid=int((out/'active_worker.pid').read_text())
while True:
 try:os.kill(pid,0)
 except ProcessLookupError:break
 time.sleep(5)
check('qwen3.6-35b-a3b');check('qwen3.5-9b')
m='qwen3.8-27b'
while not (r/'models'/m/'DOWNLOAD_VERIFIED.json').exists():
 state=read(out/'gpu_ledger.json');assert time.time()-state['billing_start_epoch']<6.5*3600,'Insufficient remaining time: report before starting27B'
 time.sleep(5)
if not (out/m/'train/training_done.json').exists():
 (out/'operator_status.json').write_text(json.dumps(dict(message='仅微调：35B与9B已完成512条；现在训练3.8-27B 512条，优先沿用BF16 LoRA。不运行推理或评价，不回传大文件。结束后保存并通知用户手动关机。'),ensure_ascii=False))
 with (r/'qwen3.8-27b_train.log').open('ab') as f:
  p=subprocess.run(['bash',str(r/'task/run_gpu_live103.sh'),'--model',m,'--phase','train','--limit','512'],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=r)
 if p.returncode:raise SystemExit('27B training engineering failure: inspect preserved state, do not proceed to evaluation')
complete=[check(m) for m in models]
(out/'three_training_complete.json').write_text(json.dumps(dict(epoch=time.time(),models=complete,inference_or_evaluation_requested=False,large_file_transfer_enabled=False,shutdown='USER_MANUAL_PENDING'),indent=2))
(out/'operator_status.json').write_text(json.dumps(dict(message='三模型512条训练与最终适配器保存检查完成。已停止后续任务，无推理、评价或大文件回传。等待用户手动关机；原预算硬截止保护仍保留。'),ensure_ascii=False))
print('THREE_TRAINING_COMPLETE; USER_MANUAL_SHUTDOWN_REQUIRED',flush=True)
