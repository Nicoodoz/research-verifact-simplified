"""Only finish outstanding frozen-ID predictions; never rerun successful receipts."""
import json,os,time,subprocess
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');out=r/'results';pid=int((out/'active_worker.pid').read_text())
while True:
 try:os.kill(pid,0)
 except ProcessLookupError:break
 time.sleep(3)
def check(model,arm):
 rs=[json.loads(s) for s in (out/model/'eval'/(arm+'.jsonl')).read_text().splitlines()]
 assert len(rs)==180 and len({v['id'] for v in rs})==180 and all(v['parsed'].get('finish_reason')=='stop' for v in rs)
check('qwen3.5-9b','native_base')
env=os.environ.copy();env.update(OMP_NUM_THREADS='8',MAX_JOBS='8',TORCHINDUCTOR_COMPILE_THREADS='8',TORCH_DISABLE_ADDR2LINE='1',HF_HUB_OFFLINE='1',HF_HOME=str(r/'cache'),TMPDIR=str(r/'tmp'),PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
cmd=[str(r/'venv103/bin/python'),'-u',str(r/'task/gpu_text_only_resume103.py'),'--bundle',str(r/'bundle'),'--out',str(out),'--model-root',str(r/'models'),'--model','qwen3.6-35b-a3b','--phase','eval','--arm','lora_label']
(out/'operator_status.json').write_text(json.dumps(dict(message='9B必要推理已完成；正在补35B最后12条。保留同批次与精度，修正未使用视觉模块移出GPU后的设备识别，并使用可扩展显存分配；不重跑已有168条。'),ensure_ascii=False))
with (r/'resume35_tail_devicefix.log').open('ab') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,env=env,cwd=r);(out/'active_worker.pid').write_text(str(p.pid));rc=p.wait()
if rc:raise SystemExit('35B remaining inference failed; inspect, no silent fallback')
for m in ['qwen3.6-35b-a3b','qwen3.5-9b']:
 for arm in ['label_base','lora_label']:check(m,arm)
check('qwen3.6-35b-a3b','native_api')
(out/'necessary_inference_complete.json').write_text(json.dumps(dict(epoch=time.time(),N_each=180,model35_native='verified existing API replies',model9_native='local',new_API_calls=0,quality_metrics_computed=False,shutdown='USER_MANUAL_PENDING'),indent=2))
(out/'operator_status.json').write_text(json.dumps(dict(message='两模型必要推理全部完成；无后续GPU任务，等待用户手动关机。新增API零调用，27B停在40条恢复检查点。'),ensure_ascii=False))
print('NECESSARY_INFERENCE_COMPLETE; USER_MANUAL_SHUTDOWN_REQUIRED',flush=True)
