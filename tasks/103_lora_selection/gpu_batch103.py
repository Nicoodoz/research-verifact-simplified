"""Same-model inference in fixed batches of8; identical label_base/lora_label groups."""
import time,hashlib
import gpu_worker103 as gw
from parse103 import parse_content
from parse_label103 import parse_label
def inference(model,tok,Fast,torch,a):
 from transformers import StoppingCriteria,StoppingCriteriaList
 class ThinkEnd(StoppingCriteria):
  def __call__(self,input_ids,scores,**kw):return input_ids[:,-1]==tok.convert_tokens_to_ids('</think>')
 class Budget(StoppingCriteria):
  def __call__(self,input_ids,scores,**kw):return torch.full((input_ids.shape[0],),gw.STOP or gw.remaining(a)<150,dtype=torch.bool,device=input_ids.device)
 Fast.for_inference(model);model.eval()
 if a.arm=='lora_label':
  from peft import PeftModel
  saved=gw.read(a.out/a.model/'train/resume.json');model=PeftModel.from_pretrained(model,saved['checkpoint'],is_trainable=False);Fast.for_inference(model);model.eval()
 mode='native' if a.arm=='native_base' else 'label';sample=[r for r in gw.rows(a.bundle/'sample240.jsonl') if r['local180']]
 if a.bridge:sample=[r for r in sample if r['id'] in gw.read(a.bundle/'gpu_plan.json')['bridge_ids']]
 if a.speed:sample=[r for r in sample if r['id'] in gw.read(a.bundle/'gpu_plan.json')['speed_ids']]
 encoded={r['id']:gw.prompt_ids(tok,r,mode) for r in sample}
 sample.sort(key=lambda r:(len(encoded[r['id']]),r['id']))
 path=a.work/(a.arm+('_bridge' if a.bridge else '_speed' if a.speed else '')+'.jsonl');done={r['id'] for r in gw.rows(path)} if path.exists() else set()
 pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
 def padded(seqs):
  n=max(map(len,seqs));return torch.tensor([[pad]*(n-len(s))+s for s in seqs],device='cuda'),torch.tensor([[0]*(n-len(s))+[1]*len(s) for s in seqs],device='cuda')
 gen=dict(do_sample=False,repetition_penalty=1.,use_cache=True,pad_token_id=pad)
 def strip_eos(seq):
  stops={tok.eos_token_id,pad}
  for i,x in enumerate(seq):
   if x in stops:return seq[:i+1]
  return seq
 # Keep original fixed batches on resume; do not replace earlier successful rows.
 for start in range(0,len(sample),8):
  batch=sample[start:start+8]
  if all(r['id'] in done for r in batch):continue
  gw.require_time(a,180);seqs=[encoded[r['id']] for r in batch];ids,mask=padded(seqs);torch.cuda.synchronize();begin=time.perf_counter();torch.cuda.reset_peak_memory_stats();meta=[dict(thinking_tokens=0,forced=False) for r in batch];outputs=[None]*len(batch)
  with torch.inference_mode():
   if mode=='native':
    first=model.generate(input_ids=ids,attention_mask=mask,max_new_tokens=4096,stopping_criteria=StoppingCriteriaList([ThinkEnd(),Budget()]),**gen);second=[];which=[];end_id=tok.convert_tokens_to_ids('</think>')
    for i,r in enumerate(batch):
     tail=first[i,ids.shape[1]:].tolist()
     if end_id in tail:
      tail=tail[:tail.index(end_id)+1];meta[i]['thinking_tokens']=len(tail);second.append(seqs[i]+tail);which.append(i)
     else:
      tail=strip_eos(tail)
      if len(tail)>=4096:
       meta[i].update(thinking_tokens=len(tail),forced=True);second.append(seqs[i]+tail+tok.encode('\n</think>\n\n',add_special_tokens=False));which.append(i)
      else:outputs[i]=tail
    if second:
     final_ids,final_mask=padded(second);final=model.generate(input_ids=final_ids,attention_mask=final_mask,max_new_tokens=768,stopping_criteria=StoppingCriteriaList([Budget()]),**gen)
     for j,i in enumerate(which):outputs[i]=strip_eos(final[j,final_ids.shape[1]:].tolist())
   else:
    result=model.generate(input_ids=ids,attention_mask=mask,max_new_tokens=768,stopping_criteria=StoppingCriteriaList([Budget()]),**gen)
    outputs=[strip_eos(result[i,ids.shape[1]:].tolist()) for i in range(len(batch))]
  torch.cuda.synchronize();elapsed=time.perf_counter()-begin
  for i,r in enumerate(batch):
   out=outputs[i];content=tok.decode(out,skip_special_tokens=True);finish='budget_stop' if gw.STOP or gw.remaining(a)<150 else 'length' if len(out)>=768 else 'stop';parsed=parse_content(content,finish) if mode=='native' else parse_label(content,finish)
   if r['id'] not in done:
    gw.append(path,dict(id=r['id'],model=a.model,arm=a.arm,prompt_sha256=hashlib.sha256(bytes(str(seqs[i]),'utf-8')).hexdigest(),input_tokens=len(seqs[i]),output_tokens=len(out),thinking_tokens=meta[i]['thinking_tokens'],forced_thinking_boundary=meta[i]['forced'],seconds=elapsed/len(batch),batch_seconds=elapsed,batch_size=len(batch),batch_ids=[b['id'] for b in batch],peak_allocated_bytes=torch.cuda.max_memory_allocated(),content=content,parsed=parsed));done.add(r['id'])
   if finish!='stop':raise RuntimeError('inference budget/truncation: preserve response and inspect')
if __name__=='__main__':gw.inference=inference;gw.main()
