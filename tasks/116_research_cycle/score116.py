"""Full legal label path MAP for a fixed checkpoint; no ground truth input."""
from pathlib import Path
import sys,os,json,time,signal,hashlib,argparse,math
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/104_supervision_evidence'));import training104 as interface
sys.path.insert(0,str(R/'tasks/106_label_preparation'))
STOP=False
def stop(*_):
 global STOP;STOP=True
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def put(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.tmp');q.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode());q.replace(p)
def main():
 p=argparse.ArgumentParser();p.add_argument('--job',required=True);args=p.parse_args();job=read(R/'data'/args.job);session=read(R/'session.json');out=R/'results'/job['name'];out.mkdir(parents=True,exist_ok=True)
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);start=time.time();deadline=min(session['start_epoch']+session['duration_seconds']-120,session['start_epoch']+3600*session['GPU_cap_CNY']/session['hourly_CNY']-120,start+job['phase_limit_seconds'])
 def budget(seconds=60):
  if STOP or time.time()+seconds>deadline:raise TimeoutError('Cycle/job budget boundary; preserve scores, no shutdown')
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TRITON_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/triton',TORCHINDUCTOR_CACHE_DIR='/root/autodl-tmp/verifact109/results/cache/inductor')
 from unsloth import FastLanguageModel
 import torch
 from peft import PeftModel
 from transformers import AutoTokenizer
 from loss106 import complete_path_scores
 data={r['id']:r for r in map(json.loads,(R/'data/inputs.jsonl').read_text().splitlines())};wanted=job['ids'];assert set(wanted)<=set(data)
 assert all(not {'GT','panel','sid','verdict'}&set(r) for r in data.values())
 tok=AutoTokenizer.from_pretrained(job['model_dir'],local_files_only=True);encoded={i:interface.prompt_ids(tok,data[i]) for i in wanted}
 for i,ids in encoded.items():assert hashlib.sha256(interface.canonical(ids).encode()).hexdigest()==data[i]['expected_prompt_sha256']
 labels=list(job['label_sequences']);sequences={g:tok.encode(interface.canonical({'verdict':g}),add_special_tokens=False)+[tok.convert_tokens_to_ids('<|im_end|>')] for g in labels};assert sequences==job['label_sequences']
 budget(120);put(out/'progress.json',dict(stage='loading',completed=0,total=len(wanted),epoch=time.time()))
 model,_=FastLanguageModel.from_pretrained(model_name=job['model_dir'],max_seq_length=job['max_seq_length'],dtype=torch.bfloat16,load_in_4bit=False,load_in_8bit=False,full_finetuning=False,device_map={'':0},trust_remote_code=False,local_files_only=True)
 folder=Path(job['adapter_path']);assert hashlib.sha256((folder/'adapter_model.safetensors').read_bytes()).hexdigest()==job['adapter_sha256']
 model=PeftModel.from_pretrained(model,folder,is_trainable=False);FastLanguageModel.for_inference(model);model.eval()
 ordered=sorted(wanted,key=lambda i:(len(encoded[i]),i));rep=[ordered[-1],ordered[len(ordered)//2],ordered[0]];order=rep+[i for i in ordered if i not in rep];saved=[]
 for n,i in enumerate(order):
  path=out/'scores'/f'{i}.json'
  if path.exists():r=read(path);assert r['adapter_sha256']==job['adapter_sha256'];saved.append(r);continue
  budget(45);put(out/'progress.json',dict(stage='scoring',completed=n,total=len(order),epoch=time.time()))
  torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();begin=time.perf_counter()
  with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):v=complete_path_scores(model,encoded[i],sequences,job['first_value_index'],job['branch_ids'],'cuda',16)
  torch.cuda.synchronize();secs=time.perf_counter()-begin;scores=v['complete_JSON_EOS_sum_logP'];assert all(math.isfinite(x) and x<=0 for x in scores.values())
  r=dict(id=i,verdict=max(labels,key=lambda g:scores[g]),scores=scores,restricted_q=v['restricted_legal_q'],first_branch=v['first_value_branch_raw_full_vocab_probabilities'],seconds=secs,input_tokens=len(encoded[i]),adapter_sha256=job['adapter_sha256'],prompt_token_sha256=data[i]['expected_prompt_sha256'],peak_allocated_bytes=torch.cuda.max_memory_allocated())
  put(path,r);saved.append(r)
  if n==4:
   warm=saved[1:];rate=sum(r['seconds'] for r in warm)/sum(r['input_tokens'] for r in warm);estimate=rate*sum(len(encoded[j]) for j in order[n+1:])*1.3+45
   put(out/'throughput.json',dict(seconds_per_token_three_paths=rate,estimated_remaining_seconds=estimate,first_formal_kept=5));budget(estimate)
 put(out/'complete.json',dict(N=len(saved),seconds=sum(r['seconds'] for r in saved),epoch=time.time(),warm_seconds_per_token=sum(r['seconds'] for r in saved[1:])/sum(r['input_tokens'] for r in saved[1:])))
 put(out/'progress.json',dict(stage='complete',completed=len(saved),total=len(order),epoch=time.time()))
if __name__=='__main__':main()
