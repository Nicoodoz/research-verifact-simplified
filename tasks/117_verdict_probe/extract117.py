"""Frozen107 semantic states at prompt and common verdict-prefix boundaries."""
from pathlib import Path
import argparse,sys,os,time,signal,gc
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/104_supervision_evidence'));import training104 as original
STOP=False
def stop(*_):
 global STOP;STOP=True

def main():
 p=argparse.ArgumentParser();p.add_argument('--job',required=True);a=p.parse_args()
 job=c.read(R/'data'/a.job);session=c.read(R/'session.json');out=R/'results'/job['name'];out.mkdir(parents=True,exist_ok=True)
 started=time.time();deadline=min(session['start_epoch']+session['duration_seconds']-300,started+job['phase_limit_seconds'])
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 def budget():
  if STOP or time.time()>deadline-30:raise TimeoutError('Keep all extracted states; stop at authorized boundary')
 def progress(stage,n,eta=None):c.put(out/'progress.json',dict(stage=stage,completed=n,total=len(job['ids']),remaining_seconds=eta,epoch=time.time()))
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
 from unsloth import FastLanguageModel as Fast
 import torch,numpy as np
 from transformers import AutoTokenizer
 from peft import PeftModel
 tok=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True);prefix=tok.encode('{"verdict":"',add_special_tokens=False)
 assert prefix==[4754,415,8217,3147]
 for label in c.LABELS:assert tok.encode(c.canonical({'verdict':label}),add_special_tokens=False)[:len(prefix)]==prefix
 pool={r['id']:r for r in c.rows(R/job['inputs'])};seq={};prompt_n={}
 for i in job['ids']:
  row=pool[i];assert not {'GT','sid','panel','verdict','answer'}&set(row)
  x=original.prompt_ids(tok,row)
  if row.get('expected_prompt_sha256'):assert c.digest(c.canonical(x))==row['expected_prompt_sha256']
  seq[i]=x+prefix;prompt_n[i]=len(x);assert len(seq[i])<=job['max_seq_length']
 budget();progress('loading',0)
 model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=job['max_seq_length'],dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
 folder=Path(job['adapter_path']);assert c.sha(folder/'adapter_model.safetensors')==job['adapter_sha256']
 model=PeftModel.from_pretrained(model,folder,is_trainable=False);Fast.for_inference(model);model.eval()
 assert not any(p.requires_grad for p in model.parameters())
 backbone=model.get_base_model().model;pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
 order=sorted(seq,key=lambda i:(len(seq[i]),i));limit=job.get('batch_size',4);times=[];done=0;batchno=0
 # Formal longest inputs measure real memory; successful outputs are reused.
 order=order[-limit:]+order[:-limit]
 while order:
  budget();n=min(limit,len(order));ids=order[:n];order=order[n:];batchno+=1
  target=out/'batches'/f'{batchno:05d}.npz';meta=target.with_suffix('.json')
  if target.exists():assert c.read(meta)['ids']==ids;done+=n;continue
  mx=max(len(seq[i]) for i in ids)
  batch=dict(input_ids=torch.tensor([[pad]*(mx-len(seq[i]))+seq[i] for i in ids],device='cuda'),attention_mask=torch.tensor([[0]*(mx-len(seq[i]))+[1]*len(seq[i]) for i in ids],device='cuda'),use_cache=False,return_dict=True)
  torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
  try:
   with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
    result=backbone(**batch);h=result.last_hidden_state if hasattr(result,'last_hidden_state') else result[0]
    index=torch.arange(n,device='cuda');pos=torch.tensor([mx-len(seq[i])+prompt_n[i]-1 for i in ids],device='cuda')
    before=h[index,pos].float().cpu().numpy();value=h[:,-1].float().cpu().numpy()
  except torch.cuda.OutOfMemoryError:
   c.put(out/'oom_attempts'/f'{batchno:05d}.json',dict(ids=ids,batch_size=n,accepted_states=0,seconds=time.perf_counter()-t))
   del batch;gc.collect();torch.cuda.empty_cache()
   if n==1:raise
   limit=max(1,n//2);order=ids+order;continue
  assert np.isfinite(before).all() and np.isfinite(value).all();torch.cuda.synchronize();seconds=time.perf_counter()-t
  target.parent.mkdir(exist_ok=True);temporary=target.with_suffix('.tmp')
  with temporary.open('wb') as f:np.savez(f,ids=np.array(ids),prompt_end=before,verdict_prefix=value)
  temporary.replace(target);c.put(meta,dict(ids=ids,seconds=seconds,input_tokens=[len(seq[i]) for i in ids],prefix_token_ids=prefix,peak_allocated_bytes=torch.cuda.max_memory_allocated(),adapter_sha256=job['adapter_sha256']))
  done+=n;times.append(seconds);progress('extracting',done,sum(times[1:])/max(1,len(times)-1)*len(order)/limit)
  del batch,h,result,before,value
 c.put(out/'complete.json',dict(N=done,seconds=sum(times),wall_seconds=time.time()-started,epoch=time.time(),adapter_sha256=job['adapter_sha256'],prefix_token_ids=prefix,initial_batch=job.get('batch_size',4),final_batch=limit,labels_in_model_inputs=False));progress('complete',done)
if __name__=='__main__':main()
