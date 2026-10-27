"""Read-only scientific coverage verification plus completion marker; no scoring/model calls."""
import json,time
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103');out=r/'results'
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
ids={x['id'] for x in rows(r/'bundle/sample240.jsonl') if x['local180']};checked={}
for model in ['qwen3.6-35b-a3b','qwen3.5-9b']:
 arms=['label_base','lora_label','native_api' if model=='qwen3.6-35b-a3b' else 'native_base'];data={}
 for arm in arms:
  rs=rows(out/model/'eval'/(arm+'.jsonl'));assert len(rs)==180 and {x['id'] for x in rs}==ids and all(x['parsed'].get('finish_reason')=='stop' for x in rs);data[arm]={x['id']:x for x in rs}
 for pid in ids:assert data['label_base'][pid]['prompt_sha256']==data['lora_label'][pid]['prompt_sha256'] and data['label_base'][pid]['batch_ids']==data['lora_label'][pid]['batch_ids']
 checked[model]={arm:dict(N=180,invalid=sum(x['parsed']['verdict'] is None for x in data[arm].values())) for arm in arms}
patch=json.loads((out/'qwen3.6-35b-a3b/eval/memory_lifetime_patch_used.json').read_text());assert any(patch.values())
result=dict(epoch=time.time(),N_each=180,coverage=checked,model35_native='verified existing API replies',model9_native='local',new_API_calls=0,quality_metrics_computed=False,local_label_pairs_same_inputs_and_batches=True,model27_saved_samples=40,shutdown='USER_MANUAL_PENDING')
(out/'necessary_inference_complete.json').write_text(json.dumps(result,indent=2));(out/'operator_status.json').write_text(json.dumps(dict(message='必要推理全部完成，无后续GPU实验。35B尾部采用仅释放已用完临时张量的修复，全部模型参数保持GPU；两模型本地直接模式同输入同批次核验通过。正在同步小型结果并推送GitHub，随后通知用户手动关机。'),ensure_ascii=False));print(json.dumps(result))
