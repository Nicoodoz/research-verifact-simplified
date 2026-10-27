"""Prepare private transfer bundle only; never connect to/rent a GPU."""
import argparse,shutil,tarfile
import common103 as c
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',choices=c.MODELS,required=True);p.add_argument('--neighbour',choices=c.MODELS);a=p.parse_args()
 assert (c.OUT/'analysis.json').exists()
 plan=c.read(c.OUT/'gpu_panels.json')|dict(candidates=['qwen3.5-9b',a.candidate],unresolved_neighbour=a.neighbour,status='READY_FOR_GPU',GPU_started=False,API_cap_cny=30,GPU_storage_cap_cny=60,GPU_max_hours=8,default_train_samples_each=512,fallback_train_samples_each=256,full_training_authorized=False)
 c.put(c.OUT/'gpu_plan.json',plan)
 bundle=c.PRIVATE/'bundle';bundle.mkdir(exist_ok=True)
 for name,src in [('train512.jsonl',c.PRIVATE),('sample240.jsonl',c.PRIVATE),('model_metadata.json',c.OUT),('token_lengths.jsonl',c.OUT),('gpu_plan.json',c.OUT)]:shutil.copyfile(src/name,bundle/name)
 preds={r['id']:r for r in c.lines(c.OUT/'predictions.jsonl')};usage=c.lines(c.OUT/'usage.jsonl');bridge=[]
 normalized={(r['id'],r['model']):r['whole_output'] for r in c.read(c.OUT/'label_format_sensitivity.json')['normalizations']}
 for r in usage:
  if r['repeat']==0 and r['id'] in plan['bridge_ids'] and r['mode'] in ['native','label']:
   strict=preds[r['id']]['predictions'][r['model']+'__'+r['mode']];value=strict or normalized.get((r['id'],r['model']))
   bridge.append(dict(id=r['id'],model=r['model'],mode=r['mode'],verdict=value,strict_verdict=strict,exact_label_normalized=value!=strict,prompt_tokens=r['prompt_tokens'],completion_tokens=r['completion_tokens']))
 c.putl(bundle/'api_bridge.jsonl',bridge)
 c.put(bundle/'manifest.json',dict(files={p.name:c.sha(p) for p in bundle.iterdir() if p.is_file()},private_clinical_data=True))
 target=c.PRIVATE/'gpu_bundle.tar.gz'
 with tarfile.open(target,'w:gz') as t:t.add(bundle,arcname='bundle')
 c.put(c.OUT/'gpu_bundle_manifest.json',dict(sha256=c.sha(target),bytes=target.stat().st_size,private_path=target.relative_to(c.ROOT).as_posix(),files=c.read(bundle/'manifest.json')['files'],uploaded=False,GPU_started=False))
 paths=list(c.TASK.glob('gpu_*.py'))+[c.TASK/'run_gpu.sh',c.TASK/'install_gpu.sh',c.TASK/'requirements_gpu.lock',c.TASK/'prompt103.py',c.TASK/'parse103.py',c.TASK/'parse_label103.py',c.OUT/'gpu_plan.json',c.OUT/'gpu_bundle_manifest.json']
 c.put(c.OUT/'gpu_preparation_freeze.json',dict(utc=c.utc(),files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},status='READY_FOR_GPU',hardware_validation_pending=True))
 print(c.canonical(dict(candidates=plan['candidates'],bundle_bytes=target.stat().st_size,status='READY_FOR_GPU')))
if __name__=='__main__':main()
