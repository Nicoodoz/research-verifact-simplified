"""Only missing103 trigger predictions; independent original103 prompt/parser."""
from pathlib import Path
import sys,json,time,os,signal,hashlib
R=Path('/root/autodl-tmp/verifact112');sys.path.insert(0,str(R/'tasks/103_lora_selection'))
import gpu_worker103 as original
from parse_label103 import parse_label
STOP=False
def stop(*_):
    global STOP;STOP=True
def read(p):return json.loads(p.read_text())
def put(p,v):original.write(p,v)
def rows(p):return original.rows(p)
def budget(seconds=60):
    s=read(R/'session.json')
    if STOP or time.time()+seconds>s['start_epoch']+3600/s['rate']-60:raise TimeoutError('112 budget; save results, no shutdown')
def main():
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
    from unsloth import FastLanguageModel
    import torch
    from transformers import AutoTokenizer,StoppingCriteria,StoppingCriteriaList
    from peft import PeftModel
    cfg=read(R/'data/config.json');inputs=rows(R/'data/inputs.jsonl');lookup={r['id']:r for r in inputs};assert len(lookup)==138
    modeldir='/root/verifact_image/models/qwen3.5-9b';tok=AutoTokenizer.from_pretrained(modeldir,local_files_only=True,trust_remote_code=False)
    encoded={r['id']:original.prompt_ids(tok,r,'label') for r in inputs};ordered=sorted(lookup,key=lambda i:(len(encoded[i]),i));rep=[ordered[-1],ordered[len(ordered)//2],ordered[0]]
    pending=[i for i in ordered if i not in rep];batches=[[i] for i in rep]+[pending[i:i+2] for i in range(0,len(pending),2)]
    put(R/'results/plan.json',dict(N=138,max_input_tokens=max(map(len,encoded.values())),batches=batches,no_truncation=True,original_prompt=True))
    budget(120);put(R/'results/progress.json',dict(stage='loading_original103',completed=0,total=138))
    model,_=FastLanguageModel.from_pretrained(model_name=modeldir,max_seq_length=max(17736,max(map(len,encoded.values()))+768),dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
    adapter=Path(cfg['adapter_path']);assert hashlib.sha256((adapter/'adapter_model.safetensors').read_bytes()).hexdigest()==cfg['adapter_sha256']
    model=PeftModel.from_pretrained(model,adapter,is_trainable=False);FastLanguageModel.for_inference(model);model.eval()
    pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    deadline=read(R/'session.json')['start_epoch']+3600/1.58-60
    class Budget(StoppingCriteria):
        def __call__(self,input_ids,scores,**kw):return torch.full((input_ids.shape[0],),STOP or time.time()>deadline,dtype=torch.bool,device=input_ids.device)
    done=[];timings=[]
    for number,ids in enumerate(batches):
        path=R/f'results/batch-{number:04d}.json'
        if path.exists():saved=read(path);assert saved['ids']==ids;done.extend(saved['records']);timings.append(saved);continue
        budget(90);seqs=[encoded[i] for i in ids];length=max(map(len,seqs));x=torch.tensor([[pad]*(length-len(s))+s for s in seqs],device='cuda');mask=torch.tensor([[0]*(length-len(s))+[1]*len(s) for s in seqs],device='cuda')
        put(R/'results/progress.json',dict(stage='predicting103',completed=len(done),total=138,batch=number))
        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();begin=time.perf_counter()
        with torch.inference_mode():out=model.generate(input_ids=x,attention_mask=mask,max_new_tokens=768,stopping_criteria=StoppingCriteriaList([Budget()]),do_sample=False,repetition_penalty=1.,use_cache=True,pad_token_id=pad)
        torch.cuda.synchronize();seconds=time.perf_counter()-begin;records=[]
        for j,i in enumerate(ids):
            tail=out[j,length:].tolist()
            for k,t in enumerate(tail):
                if t in {tok.eos_token_id,pad}:tail=tail[:k+1];break
            content=tok.decode(tail,skip_special_tokens=True);finish='budget_stop' if STOP or time.time()>deadline else 'length' if len(tail)>=768 else 'stop'
            records.append(dict(id=i,content=content,parsed=parse_label(content,finish),finish_reason=finish,input_tokens=len(encoded[i]),output_tokens=len(tail),prompt_sha256=hashlib.sha256(str(encoded[i]).encode()).hexdigest(),adapter_sha256=cfg['adapter_sha256']))
        saved=dict(ids=ids,records=records,seconds=seconds,peak_allocated_bytes=torch.cuda.max_memory_allocated());put(path,saved);done.extend(records);timings.append(saved)
        if number==4:
            warm=timings[1:];rate=sum(b['seconds'] for b in warm)/sum(r['input_tokens'] for b in warm for r in b['records']);remaining=sum(len(encoded[i]) for b in batches[number+1:] for i in b);estimate=max(rate,.00024)*remaining*1.35+90
            put(R/'results/throughput.json',dict(formal_records_kept=len(done),seconds_per_input_token=rate,estimated_remaining_seconds=estimate));budget(estimate)
    put(R/'results/predictions.json',done);put(R/'results/complete.json',dict(N=len(done),invalid=sum(not r['parsed']['valid'] for r in done),generation_seconds=sum(b['seconds'] for b in timings),epoch=time.time()))
if __name__=='__main__':main()
