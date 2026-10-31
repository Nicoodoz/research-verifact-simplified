"""Run only missing first responses for two fixed inputs on one133 adapter."""
from pathlib import Path
import argparse,json,os,signal,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as c
from parse105 import parse
from prompt133 import prompt_ids
STOP=False

def worker():
 global STOP
 signal.signal(signal.SIGTERM,lambda *_:globals().update(STOP=True));signal.signal(signal.SIGINT,lambda *_:globals().update(STOP=True))
 job=c.read(ROOT/'data/job.json');session=c.read(ROOT/'data/session.json');out=ROOT/'results';out.mkdir(exist_ok=True)
 started=time.time();deadline=min(session['start_epoch']+session['duration_seconds'],started+job['phase_limit_seconds'])-900
 def progress(stage,**extra):
  counts={a:len(list((out/a).glob('*.json'))) for a in job['arms']}
  c.put(out/'progress.json',dict(stage=stage,counts=counts,expected=job['expected_per_arm'],target_N=job['target_N'],prior=job['prior_per_arm'],epoch=time.time(),elapsed_seconds=time.time()-started,GPU_CNY=(time.time()-session['start_epoch'])*session['hourly_CNY']/3600,API_CNY=0,no_shutdown=True,**extra))
 if time.time()+180>=deadline:raise TimeoutError('Insufficient loading and return reserve')
 identity=dict(job=c.sha(ROOT/'data/job.json'),inputs=c.sha(ROOT/'data/inputs.jsonl'))
 if (out/'identity.json').exists():assert c.read(out/'identity.json')==identity
 c.put(out/'identity.json',identity)
 if (out/'inflight.json').exists():raise RuntimeError('Uncommitted generation exists; inspect before resuming')
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact134/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact134/cache/inductor')
 progress('loading')
 from unsloth import FastLanguageModel as Fast
 import torch
 from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList
 from peft import PeftModel
 class Deadline(StoppingCriteria):
  def __call__(self,input_ids,scores,**kwargs):return torch.full((input_ids.shape[0],),STOP or time.time()>=deadline,dtype=torch.bool,device=input_ids.device)
 rows={r['id']:r for r in c.rows(ROOT/'data/inputs.jsonl')}
 assert all(set(r)=={'id','claim','reference','prompt_token_sha256'} for r in rows.values())
 tokenizer=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True);encoded={}
 for arm,ids in job['ids_by_arm'].items():
  encoded[arm]={i:prompt_ids(tokenizer,rows[i],arm) for i in ids}
  for i,tokens in encoded[arm].items():
   assert c.digest(c.canonical(tokens))==rows[i]['prompt_token_sha256'][arm]
   assert len(tokens)+384<=16384
 model,_=Fast.from_pretrained(model_name=job['model_dir'],max_seq_length=16384,dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,device_map={'':0},local_files_only=True)
 assert c.read(Path(job['adapter'])/'checkpoint_complete.json')['files']['adapter_model.safetensors']==job['adapter_sha256']
 model=PeftModel.from_pretrained(model,job['adapter'],adapter_name='shuffle_repeat',is_trainable=False)
 Fast.for_inference(model);model.eval();model.requires_grad_(False)
 eos=tokenizer.convert_tokens_to_ids('<|im_end|>');pad=tokenizer.pad_token_id or tokenizer.eos_token_id
 generated=0;seconds=0.;total=sum(job['expected_per_arm'].values())
 for arm in job['arms']:
  model.set_adapter('shuffle_repeat');enc=encoded[arm]
  order=sorted([i for i in job['ids_by_arm'][arm] if not (out/arm/(i+'.json')).exists()],key=lambda i:(len(enc[i]),i))
  cursor=0
  while cursor<len(order):
   ids=order[cursor:cursor+(1 if len(enc[order[cursor]])>12701 else 2)]
   if max(len(enc[i]) for i in ids)>12701:ids=ids[:1]
   if STOP or time.time()+60>=deadline:raise TimeoutError('Save reserve reached')
   progress('inference',arm=arm,remaining_seconds=None if not generated else seconds/generated*(total-generated))
   c.put(out/'inflight.json',dict(arm=arm,ids=ids,epoch=time.time()))
   width=max(len(enc[i]) for i in ids)
   x=torch.tensor([[pad]*(width-len(enc[i]))+enc[i] for i in ids],device='cuda')
   mask=torch.tensor([[0]*(width-len(enc[i]))+[1]*len(enc[i]) for i in ids],device='cuda')
   torch.cuda.synchronize();began=time.perf_counter();torch.cuda.reset_peak_memory_stats()
   with torch.inference_mode():result=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos,stopping_criteria=StoppingCriteriaList([Deadline()]))
   torch.cuda.synchronize();elapsed=time.perf_counter()-began;peak=torch.cuda.max_memory_allocated()
   for n,i in enumerate(ids):
    tail=result[n,width:].tolist();finish='length'
    if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
    if STOP or time.time()>=deadline:finish='budget_stop'
    content=tokenizer.decode(tail,skip_special_tokens=True);parsed=parse(content,finish);parsed['valid']=bool(parsed['valid'] and finish=='stop')
    dest=out/arm/(i+'.json')
    if dest.exists():raise FileExistsError('Cannot replace first response')
    c.put(dest,dict(id=i,arm=arm,content=content,parsed=parsed,finish_reason=finish,input_tokens=len(enc[i]),output_tokens=len(tail),prompt_token_sha256=rows[i]['prompt_token_sha256'][arm],adapter_sha256=job['adapter_sha256'],checkpoint_step=369,seconds=elapsed/len(ids),batch_seconds=elapsed,batch_size=len(ids),peak_allocated_bytes=peak,epoch=time.time()))
   (out/'inflight.json').unlink();cursor+=len(ids);generated+=len(ids);seconds+=elapsed;del x,mask,result
  c.put(out/(arm+'_complete.json'),dict(N=len(job['ids_by_arm'][arm]),epoch=time.time()))
 progress('complete',remaining_seconds=0);c.put(out/'complete.json',dict(expected_per_arm=job['expected_per_arm'],epoch=time.time(),new_training=False,new_API=0,no_shutdown=True))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--worker',action='store_true');args=ap.parse_args()
 if args.worker:
  try:worker()
  except BaseException as e:c.put(ROOT/'results/failure.json',dict(type=type(e).__name__,error=str(e),epoch=time.time()));raise
 else:
  if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
  s=c.read(ROOT/'data/session.json');limit=s['start_epoch']+s['duration_seconds']-time.time()-300
  child=subprocess.Popen([sys.executable,'-u','-B',__file__,'--worker'],cwd=ROOT,start_new_session=True)
  try:code=child.wait(timeout=max(1,limit))
  except subprocess.TimeoutExpired:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=45)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
   code=124
  c.put(ROOT/'controller_done.json',dict(exit_code=code,epoch=time.time(),no_shutdown=True));raise SystemExit(code)
if __name__=='__main__':main()
