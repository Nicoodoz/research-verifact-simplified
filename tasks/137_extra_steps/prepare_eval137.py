"""Prepare missing evaluation IDs only after the fixed518 checkpoint exists."""
from pathlib import Path
import argparse,json,shutil,sys,tarfile
R=Path(__file__).resolve().parents[2];P=R/'.local_models/137_extra_steps'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
from tokenizer_cpu105 import CPUPinnedTokenizer
sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'));from prompt136 import prompt_ids
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=['screen160','old500','full1817']);a=parser.parse_args()
 trained=c.read(P/'evidence/extra_steps/training_done.json');assert (trained['steps'],trained['consumed'])==(518,4137)
 pointer=c.read(P/'evidence/extra_steps/train/resume.json');local=P/'evidence/extra_steps/train'/pointer['slot']
 complete=c.read(local/'checkpoint_complete.json');sha=complete['files']['adapter_model.safetensors'];assert sha==trained['adapter_sha256']
 keys=c.rows(R/'.local_models/134_author_baselines/keys.jsonl');assert len(keys)==1817 and len({r['sid'] for r in keys})==20
 target=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids']) if a.scope=='screen160' else {r['id'] for r in keys if a.scope=='full1817' or r['old_panel'] in ('natural','pressure')}
 prior={}
 def keep(row):
  i=row['id']
  if i not in target:return
  assert row['adapter_sha256']==sha and row['arm']=='extra_steps'
  if i in prior:assert prior[i]['content']==row['content']
  prior[i]=row
 for folder in [P/'evidence/extra_steps/predictions',P/'evidence/screen160/extra_steps',P/'evidence/old500/extra_steps',P/'evidence/full1817/extra_steps']:
  for f in folder.glob('*.json'):
   keep(c.read(f))
 # A committed initial batch remains a first response even if a later
 # interruption happened before writing every per-ID convenience file.
 for f in (P/'evidence/extra_steps/batches').glob('*.json'):
  for row in c.read(f)['records']:keep(row)
 needed=sorted(target-prior.keys());assert needed
 inputs={r['id']:r for r in c.rows(R/'.local_models/134_author_baselines/bundle/data/inputs.jsonl')}
 baseline={}
 for folder in ['screen160','old500','full1817']:
  for f in (R/'.local_models/136_claim_repeat_transfer/evidence'/folder/'claim_repeat').glob('*.json'):
   row=c.read(f);baseline[row['id']]=row
 tok=CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b');records=[];lengths=[]
 for i in needed:
  row={k:inputs[i][k] for k in ('id','claim','reference')};ids=prompt_ids(tok,row);digest=c.digest(c.canonical(ids))
  assert digest==baseline[i]['prompt_token_sha256'] and len(ids)+384<=16384
  records.append(dict(row,prompt_token_sha256=digest));lengths.append(len(ids))
 root=P/a.scope;bundle=root/'bundle';c.putl(bundle/'data/inputs.jsonl',records)
 session=c.read(R/'.local_models/134_author_baselines/session.json');c.put(bundle/'data/session.json',session)
 job=dict(task=137,name='extra_steps_'+a.scope,variant='extra_steps',arms=['extra_steps'],
  model_dir='/root/verifact_image/models/qwen3.5-9b',adapter=trained['final_checkpoint'],
  adapter_bytes=(local/'adapter_model.safetensors').stat().st_size,adapter_sha256=sha,max_seq_length=16384,
  inputs='data/inputs.jsonl',session='data/session.json',expected_N=len(needed),target_N=len(target),prior_N=len(prior),prefix_tokens=0,response_prefix='',
  generation=dict(dtype='bfloat16',thinking=False,max_new_tokens=384,total_answer_token_budget=384,do_sample=False,num_beams=1,repetition_penalty=1.,batch_size=2,single_if_prompt_above=12701),
  phases=[dict(name=a.scope,ids=needed)],phase_limit_seconds=max(2400,len(needed)*7+600),first_receipts_only=True,no_training=True,no_shutdown=True)
 c.put(bundle/'data/job.json',job);c.put(root/'job.json',job)
 for rel in ['tasks/137_extra_steps/infer137.py','tasks/137_extra_steps/prompt137.py','tasks/136_claim_repeat_transfer/prompt136.py',
             'tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/parse105.py','tasks/105_brief_supervision/common105.py']:
  dest=bundle/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
 with tarfile.open(root/'bundle.tar.gz','w:gz',compresslevel=1) as t:
  for f in bundle.rglob('*'):
   if f.is_file():t.add(f,arcname=f.relative_to(bundle),recursive=False)
 summary=dict(status='PREPARED_NOT_RUN',scope=a.scope,target_N=len(target),prior_N=len(prior),new_calls=len(needed),
  reused_invalid=sum(not r['parsed']['valid'] for r in prior.values()),max_input_tokens=max(lengths),same_input_tokens_as136=True,
  fixed_checkpoint_step=518,new_training=False,new_API=0,source_adapter=sha,GPU_window_start=session['start_local'])
 c.put(R/'outputs/137_extra_steps'/(a.scope+'_preparation.json'),summary);c.put(root/'preparation.json',summary)
 print(c.canonical(summary))
if __name__=='__main__':main()
