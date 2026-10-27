"""Read-only compact status; never emits clinical inputs, reasons, or credentials."""
import json,time,subprocess,os
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103')
def read(p,default=None):
 try:return json.loads(p.read_text())
 except (OSError,ValueError):return default
def count(p):
 try:return len(p.read_text().splitlines())
 except OSError:return 0
models={}
manifest=read(r/'weight_download_manifest.json',{})|read(r/'weight_download_manifest_38.json',{})
for name,m in manifest.items():
 written=0;verified=0;completed=0
 for w in m['weights']:
  p=r/'models'/name/w['filename'];q=p.with_suffix(p.suffix+'.range');part=p.with_suffix(p.suffix+'.partial')
  if p.exists():verified+=1;written+=w['bytes'];completed+=w['bytes']
  elif q.exists():
   written+=min(w['bytes'],q.stat().st_blocks*512);s=read(p.with_suffix(p.suffix+'.ranges.json'),{})
   completed+=s.get('prefix',0)+sum(min(128*1024*1024,w['bytes']-a) for a in s.get('done',[]))
  elif part.exists():written+=part.stat().st_size
 models[name]=dict(expected_bytes=sum(w['bytes'] for w in m['weights']),written_bytes=written,completed_range_bytes=completed,verified_shards=verified,total_shards=len(m['weights']),ready=(r/'models'/name/'REVISION').exists(),probe_steps=count(r/'results'/name/'probe/steps.jsonl'),train_steps=count(r/'results'/name/'train/steps.jsonl'),eval={arm:count(r/'results'/name/'eval'/(arm+'.jsonl')) for arm in ['native_base','label_base','lora_label']})
 stats={}
 for arm in ([] if (r/'results/train_only_scope.json').exists() and not (r/'results/inference_scope.json').exists() else ['native_base','label_base','lora_label','native_api']):
  try:rs=[json.loads(s) for s in (r/'results'/name/'eval'/(arm+'.jsonl')).read_text().splitlines()]
  except (OSError,ValueError):continue
  if not rs:continue
  seconds=sum(v.get('seconds',0) for v in rs);stats[arm]=dict(N=len(rs),unique_ids=len({v['id'] for v in rs}),seconds=seconds,mean_seconds=seconds/len(rs),remaining_minutes_linear=max(0,180-len(rs))*seconds/len(rs)/60,invalid=sum(v['parsed']['verdict'] is None for v in rs),not_stop=sum(v['parsed'].get('finish_reason')!='stop' for v in rs),last_write_epoch=(r/'results'/name/'eval'/(arm+'.jsonl')).stat().st_mtime,peak_allocated_bytes=max(v.get('peak_allocated_bytes',0) for v in rs))
 models[name]['inference_progress']=stats
 models[name]['training_done']=(r/'results'/name/'train/training_done.json').exists()
 models[name]['resume']=read(r/'results'/name/'train/resume.json',{})
 models[name]['training_completion']=read(r/'results'/name/'train/training_done.json',{})
 try:
  ss=[json.loads(s) for s in (r/'results'/name/'train/steps.jsonl').read_text().splitlines()];target=read(r/'results/scale_decision.json',{}).get('samples_each',512)
  if ss:
   steady=ss[1:] or ss;rate=sum(v['total_seconds'] for v in steady)/sum(8 for v in steady)
   models[name]['training_progress']=dict(samples=ss[-1]['samples'],target=target,compute_remaining_minutes=max(0,target-ss[-1]['samples'])*rate/60,seconds=sum(v['total_seconds'] for v in ss))
 except (OSError,ValueError):pass
ledger=read(r/'results/gpu_ledger.json',{});elapsed=time.time()-ledger.get('billing_start_epoch',time.time())+ledger.get('prior_seconds',0);gpu=ledger.get('prior_gpu_cny',0)+(time.time()-ledger.get('billing_start_epoch',time.time()))*ledger.get('gpu_hourly_cny',0)/3600
logs={}
for name in ['resume35_lifetime.log','qwen3.5-9b_native_base.log']:
 try:logs[name]=r.joinpath(name).read_text(errors='replace').splitlines()[-3:]
 except OSError:pass
active={}
try:
 pid=int((r/'results/active_worker.pid').read_text());args=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0');state=Path(f'/proc/{pid}/stat').read_text().split()[2]
 active=dict(pid=pid,alive=state!='Z',model=args[args.index('--model')+1] if '--model' in args else None,phase=args[args.index('--phase')+1] if '--phase' in args else None,arm=args[args.index('--arm')+1] if '--arm' in args else None)
 boot=int(next(v.split()[1] for v in Path('/proc/stat').read_text().splitlines() if v.startswith('btime ')));active['started_epoch']=boot+int(Path(f'/proc/{pid}/stat').read_text().split()[21])/os.sysconf('SC_CLK_TCK');active['elapsed_seconds']=time.time()-active['started_epoch']
except (OSError,ValueError,IndexError):active=dict(alive=False)
try:gpu_state=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits'],timeout=5).decode().strip()
except Exception:gpu_state='unavailable'
print(json.dumps(dict(epoch=time.time(),elapsed_seconds=elapsed,gpu_estimate_cny=gpu,storage_reserved_cny=ledger.get('storage_fixed_cny',0),gpu_state=gpu_state,models=models,logs=logs,active=active,operator=read(r/'results/operator_status.json',{}),environment_ready=(r/'results/environment_ready.json').exists(),scale_decision=read(r/'results/scale_decision.json',{}),necessary_inference_complete=read(r/'results/necessary_inference_complete.json',{}),vision_adjustment=read(r/'results/qwen3.6-35b-a3b/eval/unused_vision_memory_adjustment.json',{})),ensure_ascii=False))
