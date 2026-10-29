"""Frozen107 claim-position probe; first receipts only, original free JSON parser."""
from pathlib import Path
import sys,os,time,json,hashlib,signal,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/104_supervision_evidence'));import training104 as original
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));from parse105 import parse
STOP=False
def stop(*_):
 global STOP;STOP=True
def read(p):return json.loads(p.read_text())
def put(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.tmp');q.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode());q.replace(p)
def messages(row,kind):
 result=original.messages(row['claim'],row['reference'])
 if kind=='claim_repeat':result[-1]['content']+='\n\n## Text being verified (repeated; not reference evidence):\n'+json.dumps(row['claim'],ensure_ascii=False)+'\nApply the same three verdict definitions to this text, using only the reference above.'
 else:raise ValueError('Unfrozen input organization')
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--job',required=True);job=read(R/'data'/p.parse_args().job);session=read(R/'session.json');out=R/'results'/job['name'];out.mkdir(parents=True,exist_ok=True);started=time.time()
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);deadline=min(session['start_epoch']+session['duration_seconds']-120,started+job['phase_limit_seconds'])
 def budget():
  if STOP or time.time()>deadline-45:raise TimeoutError('Cycle/job boundary; keep all received outputs')
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
 from unsloth import FastLanguageModel as Fast
 import torch
 from transformers import AutoTokenizer
 from peft import PeftModel
 data={r['id']:r for r in map(json.loads,(R/'data/inputs.jsonl').read_text().splitlines())};tok=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True);ids={}
 for i in job['ids']:
  assert not {'GT','sid','panel'}&set(data[i]);plain=original.prompt_ids(tok,data[i]);assert hashlib.sha256(original.canonical(plain).encode()).hexdigest()==data[i]['expected_prompt_sha256']
  ids[i]=tok.apply_chat_template(messages(data[i],job['input_transform']),tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low');assert len(ids[i])+384<=16384
 put(out/'progress.json',dict(stage='loading',completed=0,total=len(ids),epoch=time.time()));budget()
 model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=16384,dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
 folder=Path(job['adapter_path']);assert hashlib.sha256((folder/'adapter_model.safetensors').read_bytes()).hexdigest()==job['adapter_sha256'];model=PeftModel.from_pretrained(model,folder,is_trainable=False);Fast.for_inference(model);model.eval()
 order=sorted(ids,key=lambda i:(len(ids[i]),i));groups=[]
 while order:
  n=1 if len(ids[order[0]])>12701 else min(2,len(order));groups.append(order[:n]);order=order[n:]
 pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id;eos=tok.convert_tokens_to_ids('<|im_end|>');done=0;times=[]
 for number,group in enumerate(groups):
  path=out/'batches'/f'{number:04d}.json'
  if path.exists():done+=len(group);continue
  budget();mx=max(len(ids[i]) for i in group);x=torch.tensor([[pad]*(mx-len(ids[i]))+ids[i] for i in group],device='cuda');mask=torch.tensor([[0]*(mx-len(ids[i]))+[1]*len(ids[i]) for i in group],device='cuda');t=time.perf_counter();torch.cuda.reset_peak_memory_stats()
  with torch.inference_mode():v=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos)
  torch.cuda.synchronize();secs=time.perf_counter()-t;records=[]
  for k,i in enumerate(group):
   tail=v[k,mx:].tolist();finish='length'
   if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
   content=tok.decode(tail,skip_special_tokens=True);records.append(dict(id=i,content=content,finish_reason=finish,parsed=parse(content,finish),source_prompt_sha256_104=data[i]['expected_prompt_sha256'],internal_prompt_sha256=hashlib.sha256(original.canonical(ids[i]).encode()).hexdigest(),input_tokens=len(ids[i])))
  put(path,dict(ids=group,records=records,seconds=secs,peak_allocated_bytes=torch.cuda.max_memory_allocated()));done+=len(group);times.append(secs);put(out/'progress.json',dict(stage='generating',completed=done,total=len(ids),epoch=time.time(),remaining_seconds=(sum(times[1:])/max(1,len(times)-1))*(len(groups)-number-1)));del x,mask,v
 put(out/'complete.json',dict(N=done,seconds=sum(times),epoch=time.time(),input_transform=job['input_transform'],adapter_sha256=job['adapter_sha256']))
if __name__=='__main__':main()
