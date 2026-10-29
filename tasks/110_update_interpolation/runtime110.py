"""Fixed110 inference helpers; no optimizer, training, network or cloud action."""
from pathlib import Path
import json,os,sys,time,platform
ROOT=Path(__file__).resolve().parents[2]
OLD_TASK=Path('/root/autodl-tmp/verifact109/bundle/tasks/109_boundary_replay')
sys.path.insert(0,str(OLD_TASK if OLD_TASK.exists() else ROOT/'tasks/109_boundary_replay'))
import common109 as c
def budget(session,seconds=120):
    s=c.read(session)
    if s['task']!=110 or not s['authorized'] or platform.node()!=s['bound_instance']:raise PermissionError('Wrong110 authorized instance')
    if (time.time()+seconds-s['billing_start_epoch'])*s['hourly_cny']/3600>s['cap_cny']-.2:raise TimeoutError('110 whole-wall budget requires stopping and saving')
def progress(work,stage,**kw):c.put(Path(work)/'progress.json',dict(stage=stage,utc=c.utc(),**kw))
def load(a):
    budget(a.session)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
        TORCH_EXTENSIONS_DIR=str(a.old/'results/cache/torch_extensions'),TRITON_CACHE_DIR=str(a.old/'results/cache/triton'),TORCHINDUCTOR_CACHE_DIR=str(a.old/'results/cache/inductor'))
    from unsloth import FastLanguageModel
    import torch
    from transformers import AutoTokenizer
    sys.path.insert(0,str(a.old/'bundle/tasks/105_brief_supervision'));sys.path.insert(0,str(a.old/'bundle/tasks/104_supervision_evidence'))
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():raise RuntimeError('Original BF16 CUDA required')
    model,_=FastLanguageModel.from_pretrained(model_name=str(a.model),max_seq_length=13097,dtype=torch.bfloat16,
        load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
    tok=AutoTokenizer.from_pretrained(a.model,trust_remote_code=False,local_files_only=True)
    if any(p.device.type!='cuda' for p in model.parameters()) or getattr(model,'is_loaded_in_4bit',False):raise RuntimeError('No offload or quantization')
    return model,tok,FastLanguageModel,torch
def activate(model,name):
    model.set_adapter(name);model.eval()
    for p in model.parameters():p.requires_grad_(False)
    if list(model.active_adapters)!=[name]:raise ValueError('Exactly one adapter must be active')
def predict(a,model,tok,torch,rows,batches,phase,identity):
    from training104 import prompt_ids
    from parse105 import parse
    folder=a.work/phase;folder.mkdir(parents=True,exist_ok=True)
    expected_file=a.old/('bundle/frozen/eval_token_lengths.jsonl' if phase in {'update_quarter','update_half'} else 'bundle/data/pool_metadata.jsonl')
    expected={r['id']:r.get('prompt_token_sha256',r.get('input_token_sha256')) for r in c.rows(expected_file)}
    pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id;eos=tok.convert_tokens_to_ids('<|im_end|>')
    progress(a.work,phase,completed=0,total=sum(len(b['ids']) for b in batches))
    for entry in batches:
        path=folder/f"batch-{entry['batch']:04d}.json"
        if path.exists():
            if c.read(path)['identity']!=identity or c.read(path)['ids']!=entry['ids']:raise ValueError('Existing receipt is another adapter/request')
            continue
        budget(a.session);seqs=[prompt_ids(tok,rows[i]) for i in entry['ids']];length=max(map(len,seqs))
        if any(c.digest(c.canonical(seq))!=expected[i] for i,seq in zip(entry['ids'],seqs)):raise ValueError('Original107/109 prompt changed')
        x=torch.tensor([[pad]*(length-len(s))+s for s in seqs],device='cuda');mask=torch.tensor([[0]*(length-len(s))+[1]*len(s) for s in seqs],device='cuda')
        c.put(folder/f"batch-{entry['batch']:04d}.inflight.json",dict(ids=entry['ids'],identity=identity))
        torch.cuda.synchronize();begin=time.perf_counter()
        with torch.inference_mode():y=model.generate(input_ids=x,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,
            max_new_tokens=384,repetition_penalty=1.,use_cache=True,pad_token_id=pad,eos_token_id=eos)
        torch.cuda.synchronize();records=[]
        for n,i in enumerate(entry['ids']):
            tail=y[n,length:].tolist();finish='length'
            if eos in tail:tail=tail[:tail.index(eos)+1];finish='stop'
            content=tok.decode(tail,skip_special_tokens=True)
            records.append(dict(id=i,sid=rows[i]['sid'],identity=identity,prompt_token_sha256=c.digest(c.canonical(seqs[n])),input_tokens=len(seqs[n]),output_tokens=len(tail),finish_reason=finish,content=content,parsed=parse(content,finish)))
        c.put(path,dict(ids=entry['ids'],identity=identity,seconds=time.perf_counter()-begin,records=records))
        (folder/f"batch-{entry['batch']:04d}.inflight.json").unlink()
        progress(a.work,phase,completed=sum(len(b['ids']) for b in batches[:entry['batch']+1]),total=sum(len(b['ids']) for b in batches))
    saved=[c.read(folder/f"batch-{b['batch']:04d}.json") for b in batches];records=[r for b in saved for r in b['records']]
    c.putl(folder/'predictions.jsonl',records);c.put(folder/'done.json',dict(N=len(records),invalid=sum(not r['parsed']['valid'] for r in records),seconds=sum(b['seconds'] for b in saved),identity=identity))
