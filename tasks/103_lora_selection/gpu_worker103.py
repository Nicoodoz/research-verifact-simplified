"""Portable, isolated BF16 LoRA probe/train/inference. Requires supplied GPU instance."""
import argparse,json,time,os,hashlib,signal
from pathlib import Path
from contextlib import nullcontext
from prompt103 import messages
from parse103 import parse_content
from parse_label103 import parse_label

def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');tmp.replace(p)
def append(p,x):
 with Path(p).open('a',encoding='utf-8') as f:f.write(json.dumps(x,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
STOP=False
def stop(sig,frame):
 global STOP
 STOP=True
def remaining(a):
 state=read(a.out/'gpu_ledger.json');elapsed=time.time()-state['billing_start_epoch'];spent=state['prior_gpu_cny']+elapsed/3600*(state['gpu_hourly_cny']+state['storage_hourly_cny'])+state['storage_fixed_cny']
 return min(8*3600-state['prior_seconds']-elapsed,(60-spent)/(state['gpu_hourly_cny']+state['storage_hourly_cny'])*3600)
def require_time(a,seconds=180):
 if STOP or remaining(a)<seconds:raise TimeoutError('GPU budget/time stopping; resume state preserved')
def load(a):
 # Import Unsloth before transformers/torch; do not reuse old vLLM environment.
 from unsloth import FastLanguageModel
 import torch
 from transformers import AutoTokenizer
 meta=read(a.bundle/'model_metadata.json')[a.model]
 modeldir=a.model_root/a.model
 assert (modeldir/'REVISION').read_text().strip()==meta['revision']
 for file in ['config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja']:
  assert digest(modeldir/file)==meta['files'][file]['sha256'],file
 tokenizer=AutoTokenizer.from_pretrained(str(modeldir),trust_remote_code=False)
 token_lengths=rows(a.bundle/'token_lengths.jsonl')
 maximum=max(r['native'] for r in token_lengths if r['model']==a.model and (r['train512'] or r['api240']))+5000
 start=time.perf_counter()
 model,_=FastLanguageModel.from_pretrained(model_name=str(modeldir),max_seq_length=maximum,dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False)
 assert not getattr(model,'is_loaded_in_4bit',False) and not getattr(model,'is_loaded_in_8bit',False)
 assert all(p.device.type=='cuda' for p in model.parameters()),'No silent CPU offload'
 from collections import Counter
 dtypes=Counter()
 for p in model.parameters():dtypes[str(p.dtype)]+=p.numel()
 write(a.work/'load.json',dict(seconds=time.perf_counter()-start,gpu=torch.cuda.get_device_name(),capability=torch.cuda.get_device_capability(),max_seq_length=maximum,revision=meta['revision'],requested_bf16=True,parameter_dtypes=dict(dtypes)))
 return model,tokenizer,FastLanguageModel,torch
def prompt_ids(tok,r,mode):
 ids=tok.apply_chat_template(messages(r['claim'],r['reference'],mode),tokenize=True,add_generation_prompt=True,enable_thinking=mode=='native',reasoning_effort='low')
 assert isinstance(ids,list) and ids
 return ids
def encode_lists(tok,r):
 prefix=prompt_ids(tok,r,'label');answer=json.dumps({'verdict':r['GT']},ensure_ascii=False,separators=(',',':'))
 suffix=tok.encode(answer,add_special_tokens=False)+[tok.convert_tokens_to_ids('<|im_end|>')]
 ids=prefix+suffix;labels=[-100]*len(prefix)+suffix
 assert len(ids)==len(labels) and all(x==-100 for x in labels[:len(prefix)]) and tok.decode(suffix[:-1])==answer
 return ids,labels,len(suffix)
def encoded(tok,r,torch):
 ids,labels,n=encode_lists(tok,r)
 return {'input_ids':torch.tensor([ids],device='cuda'),'attention_mask':torch.ones((1,len(ids)),dtype=torch.long,device='cuda'),'labels':torch.tensor([labels],device='cuda')},len(ids),n
def adapt(model,Fast,torch,a):
 experts={n:list(p.shape) for n,p in model.named_parameters() if '.experts.' in n and p.ndim==3 and 'visual' not in n}
 expert_linears=[n for n,m in model.named_modules() if '.experts.' in n and isinstance(m,torch.nn.Linear)]
 config_before=getattr(model.config,'text_config',model.config)
 is_moe=bool(getattr(config_before,'num_experts',0))
 assert not is_moe or experts or expert_linears,'MoE architecture but no expert parameters identified'
 model=Fast.get_peft_model(model,r=16,lora_alpha=32,lora_dropout=0,bias='none',target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj','out_proj','in_proj_qkv','in_proj_z','in_proj_b','in_proj_a'],use_gradient_checkpointing=True,random_state=103027,use_rslora=False,finetune_vision_layers=False,finetune_language_layers=True)
 named={n:p for n,p in model.named_parameters() if p.requires_grad}
 assert named and all('lora_' in n for n in named),'Only LoRA parameters may update'
 assert not any('visual' in n or 'vision' in n for n in named),'Vision must stay frozen'
 config=model.peft_config['default'];targets=list(config.target_parameters or [])
 if experts:
  assert targets,'MoE experts missing from adapters'
  for n in experts:assert any(n.endswith(t) or t.endswith(n) for t in targets),('Unadapted expert tensor',n)
 for n in expert_linears:assert any(n+'.lora_' in x for x in named),('Unadapted expert linear',n)
 write(a.work/'trainable_parameters.json',dict(total=sum(p.numel() for p in named.values()),names={n:list(p.shape) for n,p in named.items()},expert_shapes=experts,expert_linear_modules=expert_linears,expert_targets=targets,is_moe=is_moe,all_expert_tensor_targets_covered=is_moe,vision_frozen=True))
 return model
def checkpoint(model,opt,torch,a,step,samples):
 folder=a.work/f'checkpoint-{samples}';folder.mkdir(parents=True,exist_ok=True)
 model.save_pretrained(folder,safe_serialization=True)
 state=dict(optimizer=opt.state_dict(),step=step,samples=samples,cpu_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all())
 tmp=folder/'training_state.pt.tmp';torch.save(state,tmp);tmp.replace(folder/'training_state.pt')
 write(a.work/'resume.json',dict(checkpoint=str(folder),samples=samples,step=step,phase=a.phase,model=a.model))
def training(model,tok,Fast,torch,a):
 setup_start=time.perf_counter();model=adapt(model,Fast,torch,a);Fast.for_training(model)
 write(a.work/'adapter_setup.json',dict(seconds=time.perf_counter()-setup_start))
 train=rows(a.bundle/'train512.jsonl');all_lengths={r['id']:r['label'] for r in rows(a.bundle/'token_lengths.jsonl') if r['model']==a.model}
 if a.phase=='probe':
  ordered=sorted(train,key=lambda r:all_lengths[r['id']]);chosen=[]
  for q in [.5,.9,.99,1.]:
   i=min(len(ordered)-8,max(0,int(q*(len(ordered)-1))-4));chosen+=ordered[i:i+8]
  train=chosen
 else:train=train[:a.limit]
 params=[p for p in model.parameters() if p.requires_grad]
 opt=torch.optim.AdamW(params,lr=1e-4,weight_decay=0.)
 samples=0;step=0
 if a.resume:
  assert a.phase=='train';state=read(a.work/'resume.json');folder=Path(state['checkpoint'])
  from peft import set_peft_model_state_dict
  from safetensors.torch import load_file
  set_peft_model_state_dict(model,load_file(str(folder/'adapter_model.safetensors')))
  saved=torch.load(folder/'training_state.pt',weights_only=False);opt.load_state_dict(saved['optimizer']);samples=saved['samples'];step=saved['step'];torch.set_rng_state(saved['cpu_rng']);torch.cuda.set_rng_state_all(saved['cuda_rng'])
 before={n:p.detach().float().cpu().clone() for n,p in model.named_parameters() if p.requires_grad and 'lora_B' in n}
 try:
  while samples<len(train):
   require_time(a,300);opt.zero_grad(set_to_none=True);tokens=0;supervised=0;forward=0;backward=0;losses=[];torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
   for r in train[samples:samples+8]:
    batch,n,nt=encoded(tok,r,torch);tokens+=n;supervised+=nt;torch.cuda.synchronize();t=time.perf_counter()
    with torch.autocast('cuda',dtype=torch.bfloat16):loss=model(**batch,use_cache=False).loss/8
    torch.cuda.synchronize();forward+=time.perf_counter()-t;t=time.perf_counter();loss.backward();torch.cuda.synchronize();backward+=time.perf_counter()-t;losses.append(float(loss.detach())*8)
   torch.nn.utils.clip_grad_norm_(params,1.);t=time.perf_counter();opt.step();torch.cuda.synchronize();optimizer=time.perf_counter()-t;samples+=8;step+=1
   append(a.work/'steps.jsonl',dict(step=step,samples=samples,ids=[r['id'] for r in train[samples-8:samples]],loss=sum(losses)/8,tokens=tokens,supervised_tokens=supervised,forward_seconds=forward,backward_seconds=backward,optimizer_seconds=optimizer,total_seconds=time.perf_counter()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),first_compile_step=step==1))
   if a.phase=='train' and (samples%64==0 or samples==len(train)):checkpoint(model,opt,torch,a,step,samples)
  changes={n:float((p.detach().float().cpu()-before[n]).abs().max()) for n,p in model.named_parameters() if n in before}
  assert any(v>0 for v in changes.values()),'No adapter update'
  expert_updates={}
  for module_name,module in model.named_modules():
   if getattr(module,'num_experts',1)>1 and hasattr(module,'lora_B'):
    for adapter,layer in module.lora_B.items():
     name=module_name+'.lora_B.'+adapter+'.weight'
     if name not in before:continue
     delta=layer.weight.detach().float().cpu()-before[name];e=module.num_experts
     if delta.ndim==2 and delta.shape[1]%e==0:
      per=delta.reshape(delta.shape[0],-1,e).abs().amax(dim=(0,1));expert_updates[name]=dict(experts=e,updated=int((per>0).sum()),unchanged=int((per==0).sum()),max_abs_delta_by_expert=per.tolist())
  write(a.work/'weight_update.json',dict(lora_B_max_abs_delta=changes,any_update=True,nonzero_tensors=sum(v>0 for v in changes.values()),zero_tensors=sum(v==0 for v in changes.values()),expert_updates=expert_updates,probe_discarded=a.phase=='probe'))
  write(a.work/'training_done.json',dict(samples=samples,steps=step,phase=a.phase))
  try:
   from torch._dynamo.utils import compilation_time_metrics
   write(a.work/'compiler_timings.json',dict(torch_dynamo_metrics={k:list(v) for k,v in compilation_time_metrics.items()},first_step_timing_separate=True,not_all_triton_compilations_necessarily_visible=True))
  except (ImportError,AttributeError,TypeError):write(a.work/'compiler_timings.json',dict(torch_dynamo_metrics=None,first_step_timing_separate=True,pure_compiler_time_unavailable=True))
 except BaseException:
  if a.phase=='train':checkpoint(model,opt,torch,a,step,samples)
  raise
def inference(model,tok,Fast,torch,a):
 from transformers import StoppingCriteria,StoppingCriteriaList
 class StopThink(StoppingCriteria):
  def __call__(self,input_ids,scores,**kwargs):return bool(input_ids[0,-1].item()==tok.convert_tokens_to_ids('</think>'))
 class StopBudget(StoppingCriteria):
  def __call__(self,input_ids,scores,**kwargs):return STOP or remaining(a)<150
 Fast.for_inference(model);model.eval()
 if a.arm=='lora_label':
  from peft import PeftModel
  state=read(a.out/a.model/'train/resume.json');model=PeftModel.from_pretrained(model,state['checkpoint'],is_trainable=False);Fast.for_inference(model)
 sample=[r for r in rows(a.bundle/'sample240.jsonl') if r['local180']]
 if a.bridge:sample=[r for r in sample if r['id'] in read(a.bundle/'gpu_plan.json')['bridge_ids']]
 if a.speed:sample=[r for r in sample if r['id'] in read(a.bundle/'gpu_plan.json')['speed_ids']]
 path=a.work/(a.arm+('_bridge' if a.bridge else '_speed' if a.speed else '')+'.jsonl');done={r['id'] for r in rows(path)} if path.exists() else set()
 if not a.bridge and not a.speed:
  by_id={r['id']:r for r in sample}
  for origin in [a.work/(a.arm+'_speed.jsonl'),a.work/(a.arm+'_bridge.jsonl')]:
   if not origin.exists():continue
   for saved in rows(origin):
    if saved['id'] in done or saved['id'] not in by_id or saved['parsed'].get('finish_reason')!='stop':continue
    mode='native' if a.arm=='native_base' else 'label';ids=prompt_ids(tok,by_id[saved['id']],mode)
    assert saved['prompt_sha256']==hashlib.sha256(bytes(str(ids),'utf-8')).hexdigest()
    append(path,dict(saved,reused_from=origin.name));done.add(saved['id'])
 for r in sample:
  if r['id'] in done:continue
  require_time(a,180);mode='native' if a.arm=='native_base' else 'label';ids=prompt_ids(tok,r,mode);input_ids=torch.tensor([ids],device='cuda');start=time.perf_counter();torch.cuda.reset_peak_memory_stats();forced=False;thought_n=0
  gen=dict(do_sample=False,repetition_penalty=1.,use_cache=True,pad_token_id=tok.eos_token_id)
  with torch.inference_mode():
   if mode=='native':
    seq=model.generate(input_ids=input_ids,attention_mask=torch.ones_like(input_ids),max_new_tokens=4096,stopping_criteria=StoppingCriteriaList([StopThink(),StopBudget()]),**gen);thought_n=seq.shape[1]-len(ids)
    tail=seq[0,len(ids):].tolist();closed=tok.convert_tokens_to_ids('</think>') in tail
    if not closed and thought_n>=4096:
     forced=True;end=tok.encode('\n</think>\n\n',add_special_tokens=False);seq=torch.cat([seq,torch.tensor([end],device='cuda')],dim=1)
    if closed or forced:
     base=seq.shape[1];answer=model.generate(input_ids=seq,attention_mask=torch.ones_like(seq),max_new_tokens=768,stopping_criteria=StoppingCriteriaList([StopBudget()]),**gen);output=answer[0,base:].tolist();content=tok.decode(output,skip_special_tokens=True)
    else:output=tail;content=tok.decode(tail,skip_special_tokens=True)
   else:
    seq=model.generate(input_ids=input_ids,attention_mask=torch.ones_like(input_ids),max_new_tokens=768,stopping_criteria=StoppingCriteriaList([StopBudget()]),**gen);output=seq[0,len(ids):].tolist();content=tok.decode(output,skip_special_tokens=True)
  torch.cuda.synchronize();seconds=time.perf_counter()-start
  stopped=STOP or remaining(a)<150;finish='budget_stop' if stopped else 'length' if len(output)>=768 else 'stop'
  parsed=parse_content(content,finish) if mode=='native' else parse_label(content,finish)
  append(path,dict(id=r['id'],model=a.model,arm=a.arm,prompt_sha256=hashlib.sha256(bytes(str(ids),'utf-8')).hexdigest(),input_tokens=len(ids),output_tokens=len(output),thinking_tokens=thought_n,forced_thinking_boundary=forced,seconds=seconds,peak_allocated_bytes=torch.cuda.max_memory_allocated(),content=content,parsed=parsed))
  if finish!='stop':raise RuntimeError('Preserve incomplete inference; inspect engineering/budget')
def main():
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--model-root',type=Path,required=True);p.add_argument('--model',required=True);p.add_argument('--phase',choices=['probe','train','eval'],required=True);p.add_argument('--arm',choices=['native_base','label_base','lora_label'],default='native_base');p.add_argument('--limit',type=int,choices=[256,512],default=512);p.add_argument('--resume',action='store_true');p.add_argument('--bridge',action='store_true');p.add_argument('--speed',action='store_true');a=p.parse_args()
 a.work=a.out/a.model/a.phase;a.work.mkdir(parents=True,exist_ok=True);signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);require_time(a,300)
 model,tok,Fast,torch=load(a)
 if a.phase in ['probe','train']:training(model,tok,Fast,torch,a)
 else:inference(model,tok,Fast,torch,a)
if __name__=='__main__':main()
