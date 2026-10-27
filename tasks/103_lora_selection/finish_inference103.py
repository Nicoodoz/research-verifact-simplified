"""Complete only missing necessary inference;35B native uses existing matched API replies."""
import os,time,json,subprocess
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');out=r/'results'
pid=int((out/'active_worker.pid').read_text())
while True:
 try:os.kill(pid,0)
 except ProcessLookupError:break
 time.sleep(3)
def replies(model,arm):
 p=out/model/'eval'/(arm+'.jsonl');rs=[json.loads(s) for s in p.read_text().splitlines()];assert len(rs)==180 and len({v['id'] for v in rs})==180;assert all(v['parsed'].get('finish_reason')=='stop' for v in rs);return rs
for m in ['qwen3.5-9b','qwen3.6-35b-a3b']:
 for arm in ['label_base','lora_label']:replies(m,arm)
replies('qwen3.6-35b-a3b','native_api')
(out/'operator_status.json').write_text(json.dumps(dict(message='35B原生180条已复用合法API回执，不在GPU重跑；两模型直接模式基线及训练后判定均完成180条。9B未发现明确可用且有官方单价的同名API，正在补齐本地原生剩余76条。27B停在40条并保存，不再训练。'),ensure_ascii=False))
with (r/'qwen3.5-9b_native_base.log').open('ab') as f:
 p=subprocess.run(['bash',str(r/'task/run_gpu_live103.sh'),'--model','qwen3.5-9b','--phase','eval','--arm','native_base'],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=r)
if p.returncode:raise SystemExit('Preserve incomplete native inference and inspect')
replies('qwen3.5-9b','native_base')
(out/'necessary_inference_complete.json').write_text(json.dumps(dict(epoch=time.time(),models=['qwen3.6-35b-a3b','qwen3.5-9b'],N_each=180,native35_source='reused API; not a local-model receipt',native9_source='local',training_increment='local label_base versus local lora_label',new_API_calls=0,model27='stopped at40 training samples, checkpoint retained',quality_metrics_computed=False,shutdown='USER_MANUAL_PENDING'),indent=2))
(out/'operator_status.json').write_text(json.dumps(dict(message='35B和9B必要推理已全部完成；35B原生使用已有API回执，新增API零调用。27B已停止保存40条进度。无后续GPU任务，等待用户手动关机。'),ensure_ascii=False))
print('NECESSARY_INFERENCE_COMPLETE; USER_MANUAL_SHUTDOWN_REQUIRED',flush=True)
