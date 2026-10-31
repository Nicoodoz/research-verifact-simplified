"""Small fixed-budget native multitask probe; atomic full-state checkpoints."""
from pathlib import Path
from collections import Counter
import json,os,random,signal,sys,time
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));sys.path.insert(0,str(R/'tasks/107_support_aux'))
import common105 as c
from parse105 import parse
STOP=False
def main():
 global STOP
 signal.signal(signal.SIGTERM,lambda *_:globals().update(STOP=True));signal.signal(signal.SIGINT,lambda *_:globals().update(STOP=True))
 job=c.read(R/'data/job.json');session=c.read(R/'data/session.json');out=R/'results';out.mkdir(exist_ok=True);work=out/'train';work.mkdir(exist_ok=True)
 start=time.time();deadline=min(session['start_epoch']+session['duration_seconds'],start+job['phase_limit_seconds'])-job['save_reserve_seconds']
 optimizer=scheduler=model=save_current=None;step=consumed=0;partial=updating=False;partial_rng=None;stage='starting'
 def budget(seconds=0):
  if STOP or time.time()+seconds>=deadline:raise TimeoutError('Stop and preserve committed state')
 def progress(value,n,total,eta=None):
  nonlocal stage
  stage=value;c.put(out/'progress.json',dict(stage=value,completed=n,total=total,remaining_seconds=eta,epoch=time.time(),GPU_CNY=(time.time()-session['start_epoch'])*1.58/3600,no_shutdown=True))
 try:
  os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact134/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact134/cache/inductor')
  progress('loading',0,48,2700)
  from unsloth import FastLanguageModel as Fast
  import torch,numpy as np
  from transformers import AutoTokenizer
  from peft import set_peft_model_state_dict
  from safetensors.torch import load_file
  import checkpoint107 as ckpt
  from loss105 import backbone_loss
  from loss138 import reason_backbone_loss
  budget(1800);assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
  random.seed(job['seed']);np.random.seed(job['seed']);torch.manual_seed(job['seed']);torch.cuda.manual_seed_all(job['seed'])
  tokens={r['sample_id']:r for r in c.rows(R/'data/train_tokens.jsonl')};plan=c.read(R/'data/plan.json');evals={r['id']:r for r in c.rows(R/'data/eval_tokens.jsonl')}
  assert len(tokens)==192 and len(plan)==48 and plan[-1]['consumed']==384 and len(evals)==160
  assert all(len(x['input_ids'])<=16384 for x in tokens.values())
  source=Path(job['source_adapter']);assert c.sha(source/'adapter_model.safetensors')==job['source_sha256'];config=c.read(source/'adapter_config.json')
  tokenizer=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True)
  model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=16384,dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,device_map={'':0},local_files_only=True)
  model=Fast.get_peft_model(model,r=config['r'],lora_alpha=config['lora_alpha'],lora_dropout=config.get('lora_dropout',0.),bias=config.get('bias','none'),target_modules=config['target_modules'],use_gradient_checkpointing=True,random_state=job['seed'],use_rslora=config.get('use_rslora',False),finetune_vision_layers=False,finetune_language_layers=True)
  def restore(folder):
   result=set_peft_model_state_dict(model,load_file(str(folder/'adapter_model.safetensors')))
   assert not any('lora_' in x for x in getattr(result,'missing_keys',[])) and not getattr(result,'unexpected_keys',[])
  restore(source);Fast.for_training(model)
  params=[p for p in model.parameters() if p.requires_grad];assert params and all(not p.requires_grad for p in model.get_base_model().lm_head.parameters())
  optimizer=torch.optim.AdamW(params,lr=1e-5,betas=(.9,.999),eps=1e-8,weight_decay=0.)
  scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda _:1.)
  fp=dict(job=c.sha(R/'data/job.json'),data=c.sha(R/'data/train_tokens.jsonl'),source=job['source_sha256'],code=c.sha(Path(__file__)),loss=c.sha(Path(__file__).parent/'loss138.py'))
  def rng():return torch.get_rng_state(),torch.cuda.get_rng_state_all(),random.getstate(),np.random.get_state()
  def restore_rng(state):torch.set_rng_state(state[0]);torch.cuda.set_rng_state_all(state[1]);random.setstate(state[2]);np.random.set_state(state[3])
  def save():return ckpt.save(model,optimizer,scheduler,work,step,consumed,fp)
  save_current=save
  if (work/'resume.json').exists():step,consumed,_=ckpt.load(optimizer,scheduler,work,fp,restore)
  else:save()
  def tensor(row):return dict(input_ids=torch.tensor([row['input_ids']],device='cuda'),attention_mask=torch.ones((1,len(row['input_ids'])),dtype=torch.long,device='cuda'),groups=torch.tensor([row['groups']],device='cuda'))
  def loss_for(row):
   batch=tensor(row)
   with torch.autocast('cuda',dtype=torch.bfloat16):return (backbone_loss if row['kind']=='label' else reason_backbone_loss)(model,batch,chunk_tokens=16)[0]
  if not (out/'gpu_gate.json').exists():
   progress('longest_backward',step,48);partial_rng=rng();partial=True
   reserve=[] if optimizer.state else [torch.zeros_like(p) for p in params for _ in range(2)]
   longest=max(tokens.values(),key=lambda r:len(r['input_ids']));torch.cuda.reset_peak_memory_stats();loss=loss_for(longest);loss.backward();norm=torch.nn.utils.clip_grad_norm_(params,1.);torch.cuda.synchronize()
   assert bool(torch.isfinite(loss) and torch.isfinite(norm)) and float(norm)>0
   c.put(out/'gpu_gate.json',dict(sample_id=longest['sample_id'],kind=longest['kind'],tokens=len(longest['input_ids']),peak_allocated_bytes=torch.cuda.max_memory_allocated(),gradient_norm=float(norm),no_optimizer_update=True))
   del reserve,loss;optimizer.zero_grad(set_to_none=True);restore_rng(partial_rng);partial=False;torch.cuda.empty_cache()
  train_start=time.time()
  for item in plan[step:]:
   budget(60);partial_rng=rng();partial=True;optimizer.zero_grad(set_to_none=True);began=time.time();losses=[];kinds=Counter()
   for i in item['ids']:
    budget(10);row=tokens[i];loss=loss_for(row);assert bool(torch.isfinite(loss));(loss/item['loss_divisor']).backward();losses.append(float(loss.detach()));kinds[row['kind']]+=1;del loss
   norm=torch.nn.utils.clip_grad_norm_(params,1.);assert bool(torch.isfinite(norm));updating=True;optimizer.step();scheduler.step();torch.cuda.synchronize();updating=partial=False
   step,consumed=item['step'],item['consumed']
   if step%16==0 or step==48:save()
   with (out/'steps.jsonl').open('ab') as f:f.write((c.canonical(dict(step=step,consumed=consumed,ids=item['ids'],kinds=dict(kinds),loss=sum(losses)/len(losses),gradient_norm=float(norm),seconds=time.time()-began))+'\n').encode());f.flush()
   progress('training',step,48,(time.time()-train_start)/max(1,step)*(48-step)+500)
  pointer=c.read(work/'resume.json');assert (pointer['step'],pointer['consumed'])==(48,384)
  final=work/pointer['slot'];sha=c.read(final/'checkpoint_complete.json')['files']['adapter_model.safetensors']
  c.put(out/'training_done.json',dict(steps=48,consumed=384,final_checkpoint=str(final),adapter_sha256=sha,epoch=time.time(),arm=job['arm']))
  optimizer.zero_grad(set_to_none=True);optimizer=scheduler=None;torch.cuda.empty_cache();Fast.for_inference(model);model.eval()
  eos=tokenizer.convert_tokens_to_ids('<|im_end|>');pad=tokenizer.pad_token_id or tokenizer.eos_token_id;order=sorted(evals,key=lambda i:(len(evals[i]['input_ids']),i));done=0
  for n in range(0,len(order),2):
   ids=order[n:n+2];path=out/'batches'/f'{n//2:04d}.json'
   if path.exists():done+=len(ids);continue
   budget(30);progress('evaluation',done,160);width=max(len(evals[i]['input_ids']) for i in ids)
   x=torch.tensor([[pad]*(width-len(evals[i]['input_ids']))+evals[i]['input_ids'] for i in ids],device='cuda');mask=torch.tensor([[0]*(width-len(evals[i]['input_ids']))+[1]*len(evals[i]['input_ids']) for i in ids],device='cuda')
   with torch.inference_mode():result=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos)
   records=[]
   for j,i in enumerate(ids):
    tail=result[j,width:].tolist();finish='length'
    if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
    content=tokenizer.decode(tail,skip_special_tokens=True);parsed=parse(content,finish);parsed['valid']=bool(parsed['valid'] and finish=='stop')
    records.append(dict(id=i,arm=job['arm'],content=content,finish_reason=finish,parsed=parsed,input_tokens=len(evals[i]['input_ids']),prompt_token_sha256=evals[i]['prompt_token_sha256'],adapter_sha256=sha))
   c.put(path,dict(ids=ids,records=records))
   for r in records:c.put(out/'predictions'/(r['id']+'.json'),r)
   done+=len(ids);del x,mask,result
  assert done==160;c.put(out/'complete.json',dict(N=160,steps=48,consumed=384,epoch=time.time(),arm=job['arm'],no_shutdown=True));progress('complete',160,160,0)
 except BaseException as e:
  error=None
  if optimizer is not None and save_current is not None and not updating:
   try:
    if partial and partial_rng is not None:restore_rng(partial_rng)
    optimizer.zero_grad(set_to_none=True);save_current()
   except BaseException as save_error:error=repr(save_error)
  c.put(out/'failure.json',dict(stage=stage,error=repr(e),step=step,consumed=consumed,checkpoint_error=error,epoch=time.time()));raise
if __name__=='__main__':main()
