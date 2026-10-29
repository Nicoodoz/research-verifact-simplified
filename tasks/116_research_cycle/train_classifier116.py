"""One supervised three-class recipe, selected only on internal train patients."""
from pathlib import Path
import os,sys,json,time,math,random,signal,argparse,shutil
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/107_support_aux'))
sys.path.insert(0,str(Path(__file__).parent))
STOP=False
def stop(*_):
 global STOP;STOP=True
def append(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('ab') as f:f.write((c.canonical(v)+'\n').encode());f.flush()
def point(truth,pred):
 m=[[sum(a==i and b==j for a,b in zip(truth,pred)) for j in range(3)] for i in range(3)];n=len(truth);t=[sum(r) for r in m];p=[sum(m[i][j] for i in range(3)) for j in range(3)];correct=sum(m[i][i] for i in range(3));den=math.sqrt((n*n-sum(x*x for x in t))*(n*n-sum(x*x for x in p)))
 return dict(N=n,correct=correct,PA=correct/n,MCC=(correct*n-sum(x*y for x,y in zip(t,p)))/den if den else 0.,false_S=m[1][0]+m[2][0],confusion=m,recall=[m[i][i]/t[i] if t[i] else None for i in range(3)])
def main():
 p=argparse.ArgumentParser();p.add_argument('--job',required=True);args=p.parse_args();job=c.read(R/'data'/args.job);cfg=c.read(R/job['config']);session=c.read(R/'session.json');out=R/'results'/job['name'];out.mkdir(parents=True,exist_ok=True)
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);started=time.time();deadline=min(session['start_epoch']+session['duration_seconds']-180,session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY']-180,started+job['phase_limit_seconds'])
 def budget(seconds=90):
  if STOP or time.time()+seconds>deadline:raise TimeoutError('Cycle classifier deadline; preserve current checkpoints')
 def progress(stage,completed,total,eta=None):c.put(out/'progress.json',dict(stage=stage,completed=completed,total=total,remaining_seconds=eta,epoch=time.time()))
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
 from unsloth import FastLanguageModel as Fast
 import torch,numpy as np
 from transformers import AutoTokenizer
 import classifier116 as method
 import checkpoint107 as checkpoint
 from peft import set_peft_model_state_dict
 from safetensors.torch import load_file
 budget(180);seed=cfg['seed'];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
 progress('loading',0,cfg['training']['total_steps']);tok=AutoTokenizer.from_pretrained(cfg['model_dir'],local_files_only=True);codeids=method.label_token_ids(tok);assert list(codeids)==cfg['code_token_ids']
 data=c.rows(R/'data/cls/train.jsonl');validation=c.rows(R/'data/cls/validation.jsonl');plan=c.read(R/'data/cls/plan.json')
 assert len(data)==768 and len(validation)==128 and not {r['sid'] for r in data}&{r['sid'] for r in validation}
 enc={r['id']:method.prompt_ids(tok,r) for r in data+validation};lengths={r['id']:r for r in c.rows(R/'data/cls/lengths.jsonl')}
 for i,x in enc.items():assert c.digest(c.canonical(x))==lengths[i]['prompt_sha256'] and len(x)<=cfg['max_seq_length']
 model,_=Fast.from_pretrained(model_name=cfg['model_dir'],max_seq_length=cfg['max_seq_length'],dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
 tr=cfg['training'];model=Fast.get_peft_model(model,r=tr['lora_r'],lora_alpha=tr['lora_alpha'],lora_dropout=tr['lora_dropout'],bias=tr['bias'],target_modules=tr['target_modules'],use_gradient_checkpointing=True,random_state=seed,use_rslora=False,finetune_vision_layers=False,finetune_language_layers=True);Fast.for_training(model)
 named=[(n,p) for n,p in model.named_parameters() if p.requires_grad];params=[p for n,p in named]
 assert sum(p.numel() for p in params)==tr['expected_trainable_parameters'] and all('lora_' in n for n,p in named)
 assert not getattr(model,'is_loaded_in_4bit',False) and all(p.device.type=='cuda' for p in model.parameters())
 assert all(not p.detach().count_nonzero() for n,p in named if 'lora_B' in n)
 opt=torch.optim.AdamW(params,lr=tr['learning_rate'],betas=tuple(tr['betas']),eps=tr['eps'],weight_decay=0.)
 def multiplier(step):return (step+1)/4 if step<4 else .1+.9*(1+math.cos(math.pi*min(1,(step-4)/max(1,tr['total_steps']-4))))/2
 sched=torch.optim.lr_scheduler.LambdaLR(opt,multiplier);work=out/'train';work.mkdir(exist_ok=True);fp=dict(config=c.sha(R/job['config']),train=c.sha(R/'data/cls/train.jsonl'),plan=c.sha(R/'data/cls/plan.json'),code=c.sha(Path(__file__)))
 by={r['id']:r for r in data};pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
 def tensor(ids):
  seq=[enc[i] for i in ids];mx=max(map(len,seq));return dict(input_ids=torch.tensor([[pad]*(mx-len(x))+x for x in seq],device='cuda'),attention_mask=torch.tensor([[0]*(mx-len(x))+[1]*len(x) for x in seq],device='cuda'))
 if (work/'resume.json').exists():
  step,consumed,_=checkpoint.load(opt,sched,work,fp,lambda f:set_peft_model_state_dict(model,load_file(str(f/'adapter_model.safetensors'))))
 else:
  # The probe never advances the optimizer or changes the initialized RNG.
  rng=(torch.get_rng_state(),torch.cuda.get_rng_state_all(),random.getstate(),np.random.get_state());i=max(by,key=lambda i:len(enc[i]));batch=tensor([i]);reserve=[torch.zeros_like(p) for p in params for _ in range(2)];torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
  with torch.autocast('cuda',dtype=torch.bfloat16):loss,_=method.classification_loss(model,batch,codeids,[method.LABEL_TO_INDEX[by[i]['GT']]])
  loss.backward();norm=torch.nn.utils.clip_grad_norm_(params,1.);torch.cuda.synchronize();assert torch.isfinite(loss) and torch.isfinite(norm)
  assert any(p.grad is not None and p.grad.count_nonzero() for n,p in named if 'lora_B' in n)
  free,total=torch.cuda.mem_get_info();external=max(0,total-free-torch.cuda.memory_reserved());margin=total-external-torch.cuda.max_memory_allocated();assert margin>=256*1024**2
  c.put(out/'gpu_gate.json',dict(tokens=len(enc[i]),seconds=time.perf_counter()-t,LoRA_gradient=True,peak_allocated_bytes=torch.cuda.max_memory_allocated(),headroom_bytes=margin,probe_optimizer_updates=0,restricted_logits=3))
  del batch,loss,reserve;opt.zero_grad(set_to_none=True);torch.cuda.empty_cache();torch.set_rng_state(rng[0]);torch.cuda.set_rng_state_all(rng[1]);random.setstate(rng[2]);np.random.set_state(rng[3]);step=consumed=0;checkpoint.save(model,opt,sched,work,0,0,fp)
 def validate(step):
  path=out/'validation'/f'step-{step:03d}.json'
  if path.exists():result=c.read(path);stats=result['stats']
  else:
   budget(120);progress('internal_validation',step,tr['total_steps']);model.eval();records=[];order=sorted(validation,key=lambda r:(len(enc[r['id']]),r['id']))
   for k in range(0,len(order),2):
    rows=order[k:k+2];batch=tensor([r['id'] for r in rows])
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):pred=method.predict(model,batch,codeids)
    records.extend(dict(id=r['id'],GT=r['GT'],**z) for r,z in zip(rows,pred));del batch
   stats=point([method.LABEL_TO_INDEX[r['GT']] for r in records],[r['class_index'] for r in records]);result=dict(step=step,stats=stats,records=records);c.put(path,result)
  bestfile=out/'best.json';old=c.read(bestfile) if bestfile.exists() else None;rank=lambda s:(s['MCC'],s['PA'],-s['false_S'])
  if old is None or rank(stats)>rank(old['stats']):
   pointer=c.read(work/'resume.json');dest=out/'selection'/f'step-{step:03d}-{time.time_ns()}';dest.parent.mkdir(exist_ok=True)
   shutil.copytree(work/pointer['slot'],dest)
   c.put(bestfile,dict(step=step,stats=stats,checkpoint=str(dest),selected_only_on_internal_validation=True))
  model.train();return result
 if step in cfg['validation_steps']:validate(step)
 train_start=time.perf_counter()
 for it in plan[step:]:
  budget(180);opt.zero_grad(set_to_none=True);t=time.perf_counter();losses=[];tokens=0;torch.cuda.reset_peak_memory_stats()
  for i in it['ids']:
   batch=tensor([i])
   with torch.autocast('cuda',dtype=torch.bfloat16):loss,logits=method.classification_loss(model,batch,codeids,[method.LABEL_TO_INDEX[by[i]['GT']]])
   assert torch.isfinite(loss);(loss/it['divisor']).backward();losses.append(float(loss.detach()));tokens+=len(enc[i]);del batch,loss,logits
  norm=torch.nn.utils.clip_grad_norm_(params,1.);assert torch.isfinite(norm);opt.step();sched.step();torch.cuda.synchronize();checkpoint.save(model,opt,sched,work,it['step'],it['consumed'],fp)
  append(out/'steps.jsonl',dict(step=it['step'],consumed=it['consumed'],mean_loss=sum(losses)/len(losses),tokens=tokens,seconds=time.perf_counter()-t,lr=opt.param_groups[0]['lr'],peak_allocated_bytes=torch.cuda.max_memory_allocated()))
  progress('training',it['step'],tr['total_steps'],(time.perf_counter()-train_start)/max(1,it['step']-step)*(tr['total_steps']-it['step'])+480)
  if it['step'] in cfg['validation_steps']:validate(it['step'])
 best=c.read(out/'best.json');c.put(out/'training_done.json',dict(steps=96,consumed=768,selected_step=best['step'],selected_checkpoint=best['checkpoint'],selection='internal128_only',epoch=time.time(),fingerprint=fp))
 set_peft_model_state_dict(model,load_file(str(Path(best['checkpoint'])/'adapter_model.safetensors')));opt.zero_grad(set_to_none=True);del opt,sched;Fast.for_inference(model);model.eval()
 # Only fixed development IDs are used after checkpoint selection is complete.
 pool={r['id']:r for r in c.rows(R/'data/inputs.jsonl')};assert all(not {'GT','sid','panel'}&set(pool[i]) for i in job['eval_ids'])
 for i in job['eval_ids']:enc[i]=method.prompt_ids(tok,pool[i])
 order=sorted(job['eval_ids'],key=lambda i:(len(enc[i]),i));records=[];started_eval=time.perf_counter()
 for k in range(0,len(order),2):
  budget(45);ids=order[k:k+2];batch=tensor(ids)
  with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):pred=method.predict(model,batch,codeids)
  for i,z in zip(ids,pred):
   rec=dict(id=i,source_prompt_sha256_104=pool[i]['expected_prompt_sha256'],internal_prompt_sha256=c.digest(c.canonical(enc[i])),input_tokens=len(enc[i]),selected_step=best['step'],**z);c.put(out/'predictions'/f'{i}.json',rec);records.append(rec)
  progress('development_screen',len(records),len(order));del batch
 c.put(out/'complete.json',dict(N=len(records),selected_step=best['step'],checkpoint=best['checkpoint'],seconds=time.perf_counter()-started_eval,epoch=time.time(),raw_logits_scope='three_fixed_codes',no_confirmation40=True))
 progress('complete',len(records),len(order))
if __name__=='__main__':main()
