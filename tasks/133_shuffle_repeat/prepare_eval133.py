"""Package missing evaluation IDs only after the fixed369 state is returned."""
from pathlib import Path
import argparse,json,shutil,sys,tarfile,time
from records133 import R,Q,ARMS,read,rows,receipts,target_ids
sys.path.insert(0,str(R/'tasks/105_brief_supervision'))
from tokenizer_cpu105 import CPUPinnedTokenizer
import common105 as c
from prompt133 import prompt_ids

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=['screen160','old500','full1817'],required=True);args=ap.parse_args()
 done=read(Q/'evidence/shuffle_repeat/training_done.json');assert (done['steps'],done['consumed'])==(369,2945)
 pointer=read(Q/'evidence/shuffle_repeat/train/resume.json');checkpoint=Q/'evidence/shuffle_repeat/train'/pointer['slot']
 assert pointer['step']==369 and read(checkpoint/'checkpoint_complete.json')['files']['adapter_model.safetensors']==done['adapter_sha256']
 keys,target=target_ids(args.scope);prior=receipts();needed={a:sorted(target-prior[a].keys()) for a in ARMS};union=sorted(set().union(*map(set,needed.values())))
 assert union,'All requested IDs already attempted'
 for a in ARMS:
  for i,row in prior[a].items():assert row['adapter_sha256']==done['adapter_sha256']
 inputs={r['id']:r for r in rows(R/'.local_models/134_author_baselines/bundle/data/inputs.jsonl')}
 plain={r['id']:r for r in rows(R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
 repeat={}
 for scope in ['screen160','old500','full1817']:
  for f in (R/'.local_models/136_claim_repeat_transfer/evidence'/scope/'claim_repeat').glob('*.json'):
   row=read(f)
   if 'id' in row:repeat[row['id']]=row
 tok=CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b');records=[];lens=[]
 for i in union:
  row={k:inputs[i][k] for k in ['id','claim','reference']};hashes={}
  for arm in ARMS:
   if i not in needed[arm]:continue
   tokens=prompt_ids(tok,row,arm);digest=c.digest(c.canonical(tokens));expected=plain[i]['prompt_token_sha256'] if arm=='plain104' else repeat[i]['prompt_token_sha256']
   assert digest==expected and len(tokens)+384<=16384;hashes[arm]=digest;lens.append(len(tokens))
  records.append(dict(row,prompt_token_sha256=hashes))
 session=read(Q/'session.json');phase=Q/args.scope;bundle=phase/'bundle'
 c.putl(bundle/'data/inputs.jsonl',records);c.put(bundle/'data/session.json',session)
 estimate=sum(repeat[i]['seconds'] for a in ARMS for i in needed[a])*1.35+180+900
 remaining=session['start_epoch']+session['duration_seconds']-time.time()
 assert estimate<remaining,'Insufficient conservative return-inclusive budget'
 job=dict(task=133,scope=args.scope,model_dir='/root/verifact_image/models/qwen3.5-9b',adapter=done['final_checkpoint'],adapter_sha256=done['adapter_sha256'],arms=list(ARMS),
  ids_by_arm=needed,expected_per_arm={a:len(needed[a]) for a in ARMS},prior_per_arm={a:len(target&prior[a].keys()) for a in ARMS},target_N=len(target),
  phase_limit_seconds=max(3600,sum(map(len,needed.values()))*6+600),max_seq_length=16384,max_new_tokens=384,thinking=False,greedy=True,first_responses_only=True,no_shutdown=True)
 c.put(bundle/'data/job.json',job);c.put(phase/'job.json',job)
 for rel in ['tasks/133_shuffle_repeat/infer133.py','tasks/133_shuffle_repeat/prompt133.py','tasks/136_claim_repeat_transfer/prompt136.py','tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']:
  dest=bundle/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
 with tarfile.open(phase/'bundle.tar.gz','w:gz',compresslevel=1) as t:
  for f in bundle.rglob('*'):
   if f.is_file():t.add(f,arcname=f.relative_to(bundle),recursive=False)
 summary=dict(status='PREPARED_NOT_RUN',scope=args.scope,target_N_per_arm=len(target),new_calls=job['expected_per_arm'],prior_N=job['prior_per_arm'],max_input_tokens=max(lens),same_input_tokens_as_existing_baselines=True,checkpoint_step=369,
  expected_total_seconds_including_return_reserve=estimate,remaining_window_seconds=remaining,new_API=0,invalid_first_responses_not_retried=True)
 c.put(R/'outputs/133_shuffle_repeat'/(args.scope+'_preparation.json'),summary);print(c.canonical(summary))
if __name__=='__main__':main()
