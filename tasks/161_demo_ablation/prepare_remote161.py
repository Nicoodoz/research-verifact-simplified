"""CPU-only preparation of two fixed demonstration deletions; no GPU/API call."""
from pathlib import Path
import argparse,json,shutil,sys,time
BASE=Path('/root/autodl-tmp');S=BASE/'verifact136_claim_repeat_screen160';OLD=BASE/'verifact152_demo_na'
ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['ns_na_demo','s_na_demo'],required=True);a=ap.parse_args()
P=BASE/('verifact161_'+a.arm)
if (P/'data/job.json').exists():raise FileExistsError('161 arm already prepared')
P.mkdir(exist_ok=True);shutil.copytree(OLD/'tasks',P/'tasks',dirs_exist_ok=True);T=P/'tasks/161_demo_ablation';T.mkdir(exist_ok=True)
shutil.copy2(P/'prompt161.py',T/'prompt161.py')
shutil.copytree(BASE/'verifact155_train_error_risk/tasks/144_native_confidence',P/'tasks/144_native_confidence',dirs_exist_ok=True)
for sub in ('105_brief_supervision','104_supervision_evidence','136_claim_repeat_transfer','161_demo_ablation'):sys.path.insert(0,str(P/'tasks'/sub))
import common105 as c
examples=c.rows(OLD/'data/examples.jsonl');assert len(examples)==3
selected=examples[1:] if a.arm=='ns_na_demo' else [examples[0],examples[2]]
c.putl(P/'data/examples.jsonl',selected)
from prompt161 import prompt_ids
from prompt136 import prompt_ids as original_ids
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained('/root/verifact_image/models/qwen3.5-9b',local_files_only=True)
records=[];lengths=[]
for r in c.rows(S/'data/inputs.jsonl'):
    before=original_ids(tok,r)
    if hasattr(before,'get'):before=before['input_ids']
    if before and isinstance(before[0],list):before=before[0]
    after=prompt_ids(tok,r);assert len(after)+384<=16384
    source=c.read(S/'results/claim_repeat'/(r['id']+'.json'));assert c.digest(c.canonical(before))==source['prompt_token_sha256']
    sha=c.digest(c.canonical(after));records.append(dict(id=r['id'],claim=r['claim'],reference=r['reference'],prompt_token_sha256=sha,source_prompt_token_sha256=source['prompt_token_sha256']))
    lengths.append(dict(id=r['id'],input_tokens=len(after),source_input_tokens=len(before),prompt_token_sha256=sha))
assert len(records)==160
ls={r['id']:r['input_tokens'] for r in lengths};order=sorted(ls,key=lambda i:(ls[i],i));batches=[]
while order:
    batch=order[:2] if ls[order[0]]<=12701 else order[:1]
    if max(ls[i] for i in batch)>12701:batch=batch[:1]
    batches.append(batch);order=order[len(batch):]
old=c.read(OLD/'data/job.json');job=dict(old,task=161,arm=a.arm,scope='screen160',ids=[r['id'] for r in records],batches=batches,expected_N=160,target_N=160,prior_N=0,compute_limit_seconds=900,save_reserve_seconds=180,demonstration_change='remove_S' if a.arm=='ns_na_demo' else 'remove_NS')
c.putl(P/'data/inputs.jsonl',records);c.putl(P/'data/lengths.jsonl',lengths);c.put(P/'data/job.json',job);shutil.copy2(OLD/'data/session.json',P/'data/session.json')
worker=(BASE/'verifact155_train_error_risk/tasks/155_train_error_risk/worker155.py').read_text().replace("job['task']==155 and arm=='native_train'","job['task']==161 and arm in ('ns_na_demo','s_na_demo')").replace('task=155','task=161').replace("sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'));from prompt136 import prompt_ids","sys.path.insert(0,str(R/'tasks/161_demo_ablation'));from prompt161 import prompt_ids")
(T/'worker161.py').write_text(worker,encoding='utf-8');compile(worker,str(T/'worker161.py'),'exec')
c.put(P/'preparation.json',dict(arm=a.arm,N=160,input_tokens_total=sum(ls.values()),max_input_tokens=max(ls.values()),added_demo_tokens=sorted({r['input_tokens']-r['source_input_tokens'] for r in lengths}),target_reference_changed=False,new_GT=False,model_calls=0,prepared_epoch=time.time()))
print(json.dumps(c.read(P/'preparation.json')))
