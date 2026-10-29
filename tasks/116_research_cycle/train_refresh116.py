"""Small fixed low-rate continuation of107; unchanged original JSON objective."""
from pathlib import Path
import os,sys,time,signal,argparse,random
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
from data105 import encode,shared,training_plan
from parse105 import parse
sys.path.insert(0,str(R/'tasks/107_support_aux'))
STOP=False

def stop(*_):
 global STOP;STOP=True

def constant_lr(torch,optimizer,lr):
 """Loading Adam state restores old param-group LR: explicitly replace it."""
 for group in optimizer.param_groups:group['lr']=lr;group['initial_lr']=lr
 scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lr_lambda=lambda _:1.)
 assert all(group['lr']==lr for group in optimizer.param_groups)
 assert scheduler.base_lrs==[lr]*len(optimizer.param_groups)
 return scheduler

def append(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('ab') as f:f.write((c.canonical(value)+'\n').encode());f.flush()

def main():
 p=argparse.ArgumentParser();p.add_argument('--job',required=True);a=p.parse_args()
 job=c.read(R/'data'/a.job);cfg=c.read(R/job['config']);session=c.read(R/'session.json');out=R/'results'/job['name'];out.mkdir(parents=True,exist_ok=True)
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);started=time.time()
 deadline=min(session['start_epoch']+session['duration_seconds']-600,started+job['phase_limit_seconds'])
 def budget(seconds=90):
  if STOP or time.time()+seconds>deadline:raise TimeoutError('Preserve refresh checkpoint; no shutdown')
 def progress(stage,n,total,eta=None):c.put(out/'progress.json',dict(stage=stage,completed=n,total=total,remaining_seconds=eta,epoch=time.time()))
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
 from unsloth import FastLanguageModel as Fast
 import torch,numpy as np
 from transformers import AutoTokenizer
 from peft import set_peft_model_state_dict
 from safetensors.torch import load_file
 from loss105 import backbone_loss
 import checkpoint107 as ckpt
 tr=cfg['training'];lr=tr['learning_rate'];assert lr==2e-5
 random.seed(cfg['seed']);np.random.seed(cfg['seed']);torch.manual_seed(cfg['seed']);torch.cuda.manual_seed_all(cfg['seed'])
 progress('loading',0,25);tok=AutoTokenizer.from_pretrained(cfg['model_dir'],local_files_only=True)
 rows=c.rows(R/'data/gentle/train.jsonl');meta={r['id']:r for r in c.rows(R/'data/gentle/lengths.jsonl')};plan=training_plan([r['id'] for r in rows],1,8)
 assert len(rows)==len({r['id'] for r in rows})==196 and len(plan)==25 and plan[-1]['loss_divisor']==4
 encoded={r['id']:encode(tok,r) for r in rows}
 for i,e in encoded.items():assert e['prompt_token_sha256']==meta[i]['prompt_token_sha256'] and e['answer_sha256']==meta[i]['answer_sha256'] and len(e['input_ids'])<=cfg['max_seq_length']
 model,_=Fast.from_pretrained(model_name=cfg['model_dir'],max_seq_length=cfg['max_seq_length'],dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
 model=Fast.get_peft_model(model,r=tr['lora_r'],lora_alpha=tr['lora_alpha'],lora_dropout=0.,bias=tr['bias'],target_modules=tr['target_modules'],use_gradient_checkpointing=True,random_state=cfg['seed'],use_rslora=False,finetune_vision_layers=False,finetune_language_layers=True);Fast.for_training(model)
 named=[(n,p) for n,p in model.named_parameters() if p.requires_grad];params=[p for n,p in named]
 assert sum(p.numel() for p in params)==tr['expected_trainable_parameters'] and all('lora_' in n for n,p in named)
 assert not getattr(model,'is_loaded_in_4bit',False) and all(p.device.type=='cuda' for p in model.parameters())
 opt=torch.optim.AdamW(params,lr=lr,betas=tuple(tr['betas']),eps=tr['eps'],weight_decay=0.);sched=constant_lr(torch,opt,lr)
 work=out/'train';work.mkdir(exist_ok=True)
 fp=dict(task=116,candidate=job['candidate'],config=c.sha(R/job['config']),data=c.sha(R/'data/gentle/train.jsonl'),code=c.sha(Path(__file__)),source107=cfg['source_adapter_sha256'])
 def restore(folder):set_peft_model_state_dict(model,load_file(str(folder/'adapter_model.safetensors')))
 if (work/'resume.json').exists():
  step,consumed,_=ckpt.load(opt,sched,work,fp,restore)
 else:
  source=Path(cfg['source_root']);pointer=c.read(source/'resume.json');assert pointer['fingerprint']['arm']=='label_only'
  source_step,source_n,folder=ckpt.load(opt,sched,source,pointer['fingerprint'],restore)
  assert (source_step,source_n)==(50,392) and c.sha(folder/'adapter_model.safetensors')==cfg['source_adapter_sha256']
  old_lrs=[g['lr'] for g in opt.param_groups];sched=constant_lr(torch,opt,lr)
  c.put(out/'initialization.json',dict(source107_steps=source_step,source107_presentations=source_n,optimizer_moments_retained=True,old_lrs=old_lrs,new_lrs=[g['lr'] for g in opt.param_groups],source_adapter_sha256=cfg['source_adapter_sha256'],new_training_head=False))
  # One real longest backward, without an optimizer update or RNG drift.
  rng=(torch.get_rng_state(),torch.cuda.get_rng_state_all(),random.getstate(),np.random.get_state());i=max(encoded,key=lambda i:len(encoded[i]['input_ids']));e=encoded[i]
  batch=dict(input_ids=torch.tensor([e['input_ids']],device='cuda'),attention_mask=torch.ones((1,len(e['input_ids'])),device='cuda',dtype=torch.long),groups=torch.tensor([e['groups']],device='cuda'))
  torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
  with torch.autocast('cuda',dtype=torch.bfloat16):loss,_=backbone_loss(model,batch,chunk_tokens=16)
  loss.backward();norm=torch.nn.utils.clip_grad_norm_(params,1.);torch.cuda.synchronize();assert torch.isfinite(loss) and torch.isfinite(norm) and norm>0
  free,total=torch.cuda.mem_get_info();external=max(0,total-free-torch.cuda.memory_reserved());margin=total-external-torch.cuda.max_memory_allocated();assert margin>=256*1024**2
  c.put(out/'gpu_gate.json',dict(tokens=len(e['input_ids']),seconds=time.perf_counter()-t,peak_allocated_bytes=torch.cuda.max_memory_allocated(),headroom_bytes=margin,LoRA_gradient=True,optimizer_updates=0,source_optimizer_moments_resident=True))
  del batch,loss;opt.zero_grad(set_to_none=True);torch.cuda.empty_cache();torch.set_rng_state(rng[0]);torch.cuda.set_rng_state_all(rng[1]);random.setstate(rng[2]);np.random.set_state(rng[3]);step=consumed=0;ckpt.save(model,opt,sched,work,0,0,fp)
 assert all(g['lr']==lr and g['initial_lr']==lr for g in opt.param_groups) and sched.base_lrs==[lr]*len(opt.param_groups)
 train_start=time.perf_counter()
 for entry in plan[step:]:
  budget(180);opt.zero_grad(set_to_none=True);t=time.perf_counter();losses=[]
  for i in entry['ids']:
   budget(90);e=encoded[i];batch=dict(input_ids=torch.tensor([e['input_ids']],device='cuda'),attention_mask=torch.ones((1,len(e['input_ids'])),device='cuda',dtype=torch.long),groups=torch.tensor([e['groups']],device='cuda'))
   with torch.autocast('cuda',dtype=torch.bfloat16):loss,_=backbone_loss(model,batch,chunk_tokens=16)
   assert torch.isfinite(loss);(loss/entry['loss_divisor']).backward();losses.append(float(loss.detach()));del batch,loss
  norm=torch.nn.utils.clip_grad_norm_(params,1.);assert torch.isfinite(norm);opt.step();sched.step();assert all(g['lr']==lr for g in opt.param_groups);torch.cuda.synchronize();ckpt.save(model,opt,sched,work,entry['step'],entry['consumed'],fp)
  append(out/'steps.jsonl',dict(step=entry['step'],source_plus_new_step=50+entry['step'],consumed=entry['consumed'],loss_divisor=entry['loss_divisor'],loss=sum(losses)/len(losses),gradient_norm=float(norm),lr=opt.param_groups[0]['lr'],seconds=time.perf_counter()-t))
  progress('training',entry['step'],25,(time.perf_counter()-train_start)/max(1,entry['step']-step)*(25-entry['step'])+360)
 pointer=c.read(work/'resume.json');assert (pointer['step'],pointer['consumed'])==(25,196)
 folder=work/pointer['slot'];sha=c.sha(folder/'adapter_model.safetensors');c.put(out/'best.json',dict(step=25,checkpoint=str(folder),selection='fixed final25; no evaluation selection',adapter_sha256=sha))
 c.put(out/'training_done.json',dict(steps=25,consumed=196,selected_step=25,selected_checkpoint=str(folder),source107_step=50,fingerprint=fp,epoch=time.time()))
 opt.zero_grad(set_to_none=True);del opt,sched;torch.cuda.empty_cache();Fast.for_inference(model);model.eval()
 pool={r['id']:r for r in c.rows(R/'data/inputs.jsonl')};assert all(not {'GT','sid','panel'}&set(pool[i]) for i in job['eval_ids'])
 seq={i:shared.prompt_ids(tok,pool[i]) for i in job['eval_ids']}
 for i,x in seq.items():assert c.digest(c.canonical(x))==pool[i]['expected_prompt_sha256'] and len(x)+384<=cfg['max_seq_length']
 ordered=sorted(seq,key=lambda i:(len(seq[i]),i));groups=[]
 while ordered:
  n=1 if len(seq[ordered[0]])>12701 else min(2,len(ordered));groups.append(ordered[:n]);ordered=ordered[n:]
 pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id;eos=tok.convert_tokens_to_ids('<|im_end|>');done=0;eval_start=time.perf_counter()
 for k,ids in enumerate(groups):
  path=out/'batches'/f'{k:04d}.json'
  if path.exists():
   prior=c.read(path);assert prior['ids']==ids;done+=len(ids);continue
  budget(90);mx=max(len(seq[i]) for i in ids);x=torch.tensor([[pad]*(mx-len(seq[i]))+seq[i] for i in ids],device='cuda');mask=torch.tensor([[0]*(mx-len(seq[i]))+[1]*len(seq[i]) for i in ids],device='cuda')
  with torch.inference_mode():v=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos)
  records=[]
  for n,i in enumerate(ids):
   tail=v[n,mx:].tolist();finish='length'
   if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
   text=tok.decode(tail,skip_special_tokens=True);records.append(dict(id=i,content=text,finish_reason=finish,parsed=parse(text,finish),source_prompt_sha256_104=pool[i]['expected_prompt_sha256'],internal_prompt_sha256=pool[i]['expected_prompt_sha256'],input_tokens=len(seq[i]),adapter_sha256=sha))
  c.put(path,dict(ids=ids,records=records));done+=len(ids);progress('development_screen',done,180,(time.perf_counter()-eval_start)/done*(180-done));del x,mask,v
 c.put(out/'complete.json',dict(N=done,steps=25,consumed=196,adapter_sha256=sha,epoch=time.time(),no_confirmation40=True));progress('complete',done,180)

if __name__=='__main__':main()
