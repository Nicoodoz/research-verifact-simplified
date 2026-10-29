"""Frozen107, three full answer paths, reused106 score function; no GT."""
from pathlib import Path
import sys,os,json,time,signal,hashlib,argparse
R=Path('/root/autodl-tmp/verifact113');sys.path.insert(0,str(R/'tasks/104_supervision_evidence'));import training104 as interface
sys.path.insert(0,str(R/'tasks/106_label_preparation'))
LABELS=('Supported','Not Supported','Not Addressed');STOP=False
def stop(*_):
 global STOP;STOP=True
def read(p):return json.loads(p.read_text())
def put(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.tmp');q.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');q.replace(p)
def remaining():
 s=read(R/'session.json');return s['start_epoch']+3600/s['rate']-60-time.time()
def budget(seconds=60):
 if STOP or remaining()<seconds:raise TimeoutError('113 budget stop; preserve committed scores, no shutdown')
def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['pilot','confirm'],required=True);phase=p.parse_args().phase
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
 from unsloth import FastLanguageModel
 import torch
 from peft import PeftModel
 from transformers import AutoTokenizer
 from loss106 import complete_path_scores
 cfg=read(R/'data/config.json');data={r['id']:r for r in map(json.loads,(R/'data/inputs.jsonl').read_text().splitlines())};wanted=cfg[phase+'_ids'];tok=AutoTokenizer.from_pretrained('/root/verifact_image/models/qwen3.5-9b',local_files_only=True)
 encoded={i:interface.prompt_ids(tok,data[i]) for i in data}
 for i,ids in encoded.items():assert hashlib.sha256(interface.canonical(ids).encode()).hexdigest()==data[i]['expected_prompt_sha256'],'107 prompt changed'
 sequences={g:tok.encode(interface.canonical({'verdict':g}),add_special_tokens=False)+[tok.convert_tokens_to_ids('<|im_end|>')] for g in LABELS};assert sequences==cfg['label_sequences']
 put(R/'results/input_lengths.json',dict(lengths={i:len(x) for i,x in encoded.items()},max_input_tokens=max(map(len,encoded.values())),sequences=sequences))
 budget(120);put(R/'results/progress.json',dict(phase=phase,stage='loading',completed=0,total=len(wanted)))
 model,_=FastLanguageModel.from_pretrained(model_name='/root/verifact_image/models/qwen3.5-9b',max_seq_length=max(13097,max(map(len,encoded.values()))+9),dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
 folder=Path(cfg['adapter_path']);assert hashlib.sha256((folder/'adapter_model.safetensors').read_bytes()).hexdigest()==cfg['adapter_sha256']
 model=PeftModel.from_pretrained(model,folder,is_trainable=False);FastLanguageModel.for_inference(model);model.eval()
 ordered=sorted(wanted,key=lambda i:(len(encoded[i]),i));rep=[ordered[-1],ordered[len(ordered)//2],ordered[0]];order=rep+[i for i in ordered if i not in rep];saved=[]
 for n,i in enumerate(order):
  outpath=R/'results/scores'/f'{i}.json'
  if outpath.exists():r=read(outpath);assert r['adapter_sha256']==cfg['adapter_sha256'];saved.append(r);continue
  budget(90);put(R/'results/progress.json',dict(phase=phase,stage='scoring',completed=n,total=len(order)))
  torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();begin=time.perf_counter()
  with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):v=complete_path_scores(model,encoded[i],sequences,4,cfg['branch_ids'],'cuda',16)
  torch.cuda.synchronize();seconds=time.perf_counter()-begin
  import math
  assert all(math.isfinite(s) and s<=0 for s in v['complete_JSON_EOS_sum_logP'].values()),'Nonfinite or invalid log probabilities'
  r=dict(id=i,scores=v['complete_JSON_EOS_sum_logP'],restricted_q=v['restricted_legal_q'],verdict=max(LABELS,key=lambda g:v['complete_JSON_EOS_sum_logP'][g]),first_branch=v['first_value_branch_raw_full_vocab_probabilities'],seconds=seconds,input_tokens=len(encoded[i]),adapter_sha256=cfg['adapter_sha256'],prompt_token_sha256=data[i]['expected_prompt_sha256'],peak_allocated_bytes=torch.cuda.max_memory_allocated())
  put(outpath,r);saved.append(r)
  if n==4:
   warm=saved[1:];rate=sum(r['seconds'] for r in warm)/sum(r['input_tokens'] for r in warm);estimate=rate*sum(len(encoded[j]) for j in order[n+1:])*1.3+90
   put(R/f'results/{phase}_throughput.json',dict(seconds_per_input_token_for_all_three_paths=rate,estimated_remaining_seconds=estimate,formal_first_scores_kept=5));budget(estimate)
 warm=saved[1:] or saved;put(R/f'results/{phase}_complete.json',dict(N=len(saved),seconds=sum(r['seconds'] for r in saved),warm_seconds_per_input_token=sum(r['seconds'] for r in warm)/sum(r['input_tokens'] for r in warm),epoch=time.time()))
if __name__=='__main__':main()
