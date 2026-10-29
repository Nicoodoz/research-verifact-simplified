"""One fresh 9B matched-refresh fit; inherited 105 loss and 107 checkpointing."""
from pathlib import Path
import os,sys,time,signal,random,json,hashlib,traceback
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'))
sys.path.insert(0,str(R/'tasks/107_support_aux'))
import common105 as c
from data105 import encode,shared
from parse105 import parse
STOP=False
def stop(*_):
 global STOP;STOP=True
def append(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('ab') as f:f.write((c.canonical(x)+'\n').encode());f.flush();os.fsync(f.fileno())
def main():
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 cfg=c.read(R/'data/config.json');session=c.read(R/'session.json');out=R/'results';out.mkdir(exist_ok=True)
 deadline=session['start_epoch']+3600*session['cap']/session['rate']
 def remaining():return deadline-time.time()
 def budget(seconds=120):
  if STOP or remaining()<seconds:raise TimeoutError('114 compute stop; preserve files, no shutdown')
 def progress(stage,completed,total,eta=None,**extra):
  c.put(out/'progress.json',dict(stage=stage,completed=completed,total=total,remaining_seconds=eta,epoch=time.time(),fee_cny=(time.time()-session['start_epoch'])*session['rate']/3600,**extra))
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
 from unsloth import FastLanguageModel as Fast
 import torch,numpy as np
 from transformers import AutoTokenizer
 from loss105 import backbone_loss
 import checkpoint107 as ckpt
 from peft import set_peft_model_state_dict
 from safetensors.torch import load_file
 budget(1800);progress('loading',0,50,4500)
 assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
 seed=cfg['seed'];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
 folder=Path(cfg['model_dir']);assert not (folder/'adapter_config.json').exists()
 tok=AutoTokenizer.from_pretrained(str(folder),local_files_only=True)
 rows=c.rows(R/'data/train.jsonl');lengths=c.rows(R/'data/train_lengths.jsonl');plan=c.read(R/'data/plan.json')
 assert len(rows)==392 and len(plan)==50 and plan[-1]['consumed']==392
 encoded=[encode(tok,r) for r in rows]
 for e,w in zip(encoded,lengths):assert e['prompt_token_sha256']==w['prompt_token_sha256'] and e['answer_sha256']==w['answer_sha256']
 ev={r['id']:r for r in c.rows(R/'data/eval_inputs.jsonl')};evl={r['id']:r for r in c.rows(R/'data/eval_token_lengths.jsonl')};batches=c.read(R/'data/eval_batches.json')['batches']
 assert len(ev)==500 and all(not {'GT','verdict','answer'}&set(r) for r in ev.values())
 evseq={i:shared.prompt_ids(tok,r) for i,r in ev.items()}
 for i,x in evseq.items():assert c.digest(c.canonical(x))==evl[i]['prompt_token_sha256']
 begin=time.perf_counter()
 model,_=Fast.from_pretrained(model_name=str(folder),max_seq_length=cfg['context_tokens'],dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
 assert not getattr(model,'is_loaded_in_4bit',False) and not getattr(model,'is_loaded_in_8bit',False) and all(p.device.type=='cuda' for p in model.parameters())
 tr=cfg['training'];model=Fast.get_peft_model(model,r=tr['lora_r'],lora_alpha=tr['lora_alpha'],lora_dropout=tr['lora_dropout'],bias=tr['bias'],target_modules=tr['target_modules'],use_gradient_checkpointing=tr['gradient_checkpointing'],random_state=seed,use_rslora=tr['use_rslora'],finetune_vision_layers=False,finetune_language_layers=True)
 named=[(n,p) for n,p in model.named_parameters() if p.requires_grad];params=[p for n,p in named]
 assert sum(p.numel() for p in params)==tr['expected_trainable_parameters'] and all('lora_' in n and 'vision' not in n and 'visual' not in n for n,p in named)
 assert all(not int(p.detach().count_nonzero()) for n,p in named if 'lora_B' in n)
 h=hashlib.sha256()
 for n,p in sorted(named):h.update(n.encode());h.update(p.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())
 initial=h.hexdigest();Fast.for_training(model)
 optimizer=torch.optim.AdamW(params,lr=tr['learning_rate'],betas=tuple(tr['betas']),eps=tr['eps'],weight_decay=tr['weight_decay'])
 scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lr_lambda=lambda step:1.)
 work=out/'train';work.mkdir(exist_ok=True);fp=dict(config=c.sha(R/'data/config.json'),data=c.sha(R/'data/train.jsonl'),plan=c.sha(R/'data/plan.json'),code=c.sha(Path(__file__)))
 c.put(out/'model_setup.json',dict(initial_LoRA_sha256=initial,trainable_parameters=sum(p.numel() for p in params),fresh_base=True,zero_initial_B=True,auxiliary_head=False,gpu=torch.cuda.get_device_name(),load_seconds=time.perf_counter()-begin,torch=torch.__version__,context_tokens=cfg['context_tokens']))
 def tensor(e):return dict(input_ids=torch.tensor([e['input_ids']],device='cuda'),attention_mask=torch.ones((1,len(e['input_ids'])),dtype=torch.long,device='cuda'),groups=torch.tensor([e['groups']],device='cuda'))
 # Probe has no optimizer update and restores RNG before the first presentation.
 if not (work/'resume.json').exists():
  progress('longest_backward_check',0,50,4200);rng=(torch.get_rng_state(),torch.cuda.get_rng_state_all(),random.getstate(),np.random.get_state())
  long=max(range(len(encoded)),key=lambda i:len(encoded[i]['input_ids']));reserved=[torch.zeros_like(p) for p in params for _ in range(2)]
  torch.cuda.reset_peak_memory_stats();t=time.perf_counter();batch=tensor(encoded[long])
  with torch.autocast('cuda',dtype=torch.bfloat16):loss,_=backbone_loss(model,batch,chunk_tokens=tr['head_chunk_tokens'])
  loss.backward();norm=torch.nn.utils.clip_grad_norm_(params,tr['gradient_clip']);torch.cuda.synchronize()
  assert torch.isfinite(loss) and torch.isfinite(norm) and any(p.grad is not None and int(p.grad.count_nonzero()) for n,p in named if 'lora_B' in n)
  free,total=torch.cuda.mem_get_info();peak=torch.cuda.max_memory_allocated();external=max(0,total-free-torch.cuda.memory_reserved());margin=total-external-peak
  assert margin>=256*1024**2,'Longest full input backward leaves <256 MiB physical headroom'
  c.put(out/'gpu_gate.json',dict(tokens=len(encoded[long]['input_ids']),seconds=time.perf_counter()-t,loss=float(loss.detach()),grad_norm=float(norm),LoRA_gradient=True,peak_allocated_bytes=peak,physical_headroom_bytes=margin,Adam_moments_memory_reserved=True,no_probe_update=True))
  del batch,loss,reserved;optimizer.zero_grad(set_to_none=True);torch.cuda.empty_cache()
  torch.set_rng_state(rng[0]);torch.cuda.set_rng_state_all(rng[1]);random.setstate(rng[2]);np.random.set_state(rng[3])
  expected=cfg['estimated_train_seconds']+cfg['estimated_eval_seconds']+cfg['return_reserve_seconds']
  budget(expected);ckpt.save(model,optimizer,scheduler,work,0,0,fp);step=0
 else:
  def restore(p):set_peft_model_state_dict(model,load_file(str(p/'adapter_model.safetensors')))
  step,consumed,_=ckpt.load(optimizer,scheduler,work,fp,restore)
  assert consumed==(plan[step-1]['consumed'] if step else 0)
 times=[];tokens_done=0;train_begin=time.perf_counter()
 for item in plan[step:]:
  budget(cfg['return_reserve_seconds']+120);optimizer.zero_grad(set_to_none=True);t=time.perf_counter();losses=[];tokens=0;torch.cuda.reset_peak_memory_stats()
  for idx in item['indices']:
   budget(cfg['return_reserve_seconds']+90);e=encoded[idx];batch=tensor(e)
   with torch.autocast('cuda',dtype=torch.bfloat16):loss,info=backbone_loss(model,batch,chunk_tokens=tr['head_chunk_tokens'])
   assert torch.isfinite(loss);(loss/item['divisor']).backward();losses.append(float(loss.detach()));tokens+=len(e['input_ids']);del loss,batch
  norm=torch.nn.utils.clip_grad_norm_(params,tr['gradient_clip']);assert torch.isfinite(norm)
  optimizer.step();scheduler.step();torch.cuda.synchronize();s=time.perf_counter();ckpt.save(model,optimizer,scheduler,work,item['step'],item['consumed'],fp)
  secs=time.perf_counter()-t;tokens_done+=tokens;times.append(secs)
  rec=dict(step=item['step'],epoch=item['epoch'],consumed=item['consumed'],indices=item['indices'],ids=[rows[i]['id'] for i in item['indices']],loss_divisor=item['divisor'],mean_loss=sum(losses)/len(losses),grad_norm=float(norm),tokens=tokens,seconds=secs,checkpoint_seconds=time.perf_counter()-s,peak_allocated_bytes=torch.cuda.max_memory_allocated())
  append(work/'steps.jsonl',rec)
  remain_tokens=sum(len(encoded[i]['input_ids']) for it in plan[item['step']:] for i in it['indices'])
  eta=sum(times)/tokens_done*remain_tokens+cfg['estimated_eval_seconds']+cfg['return_reserve_seconds'];progress('training',item['step'],50,eta,loss=rec['mean_loss'])
  if item['step'] in [1,5,25]:budget(eta*1.05)
 pointer=c.read(work/'resume.json');assert pointer['step']==50 and pointer['consumed']==392
 c.put(work/'training_done.json',dict(step=50,consumed=392,final_slot=pointer['slot'],fingerprint=fp,chosen_by='fixed_final_step',train_seconds=time.perf_counter()-train_begin,initial_LoRA_sha256=initial))
 optimizer.zero_grad(set_to_none=True);del optimizer,scheduler;torch.cuda.empty_cache();Fast.for_inference(model);model.eval()
 pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id;eos=tok.convert_tokens_to_ids('<|im_end|>');ew=out/'eval';ew.mkdir(exist_ok=True);eval_begin=time.perf_counter();done=0
 for j,entry in enumerate(batches):
  p=ew/f"batch-{entry['batch']:04d}.json"
  if p.exists():r=c.read(p);assert r['ids']==entry['ids'] and r['fingerprint']==fp;done+=len(entry['ids']);continue
  budget(cfg['return_reserve_seconds']+90);seq=[evseq[i] for i in entry['ids']];mx=max(map(len,seq));inputs=torch.tensor([[pad]*(mx-len(x))+x for x in seq],device='cuda');mask=torch.tensor([[0]*(mx-len(x))+[1]*len(x) for x in seq],device='cuda')
  t=time.perf_counter();torch.cuda.reset_peak_memory_stats()
  with torch.inference_mode():result=model.generate(input_ids=inputs,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos)
  torch.cuda.synchronize();records=[]
  for k,i in enumerate(entry['ids']):
   tail=result[k,mx:].tolist();finish='length'
   if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
   content=tok.decode(tail,skip_special_tokens=True);records.append(dict(id=i,arm='matched_refresh',prompt_token_sha256=evl[i]['prompt_token_sha256'],input_tokens=len(seq[k]),output_tokens=len(tail),finish_reason=finish,content=content,parsed=parse(content,finish)))
  c.put(p,dict(ids=entry['ids'],fingerprint=fp,seconds=time.perf_counter()-t,peak_allocated_bytes=torch.cuda.max_memory_allocated(),records=records));done+=len(records)
  seconds=time.perf_counter()-eval_begin;eta=seconds/(j+1)*(len(batches)-j-1)+cfg['return_reserve_seconds'];progress('evaluating',done,500,eta)
  del inputs,mask,result
  if j in [4,24]:budget(eta*1.05)
 c.put(out/'evaluation_done.json',dict(N=done,batches=len(batches),seconds=time.perf_counter()-eval_begin,epoch=time.time(),original_interface=True,GT_in_model_inputs=False))
 progress('GPU_done_return_pending',500,500,cfg['return_reserve_seconds']);c.put(out/'gpu_done.json',dict(epoch=time.time(),no_shutdown=True,N=done))
if __name__=='__main__':
 try:main()
 except BaseException as e:
  c.put(R/'results/failure.json',dict(error=type(e).__name__,message=str(e),epoch=time.time(),traceback=traceback.format_exc(),no_shutdown=True));raise
