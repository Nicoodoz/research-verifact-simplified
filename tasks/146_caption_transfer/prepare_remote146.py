"""Prepare one bounded transfer screen from existing142 inputs; no GT access."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib,json,shutil,sys,time

BASE=Path('/root/autodl-tmp')
P=BASE/'verifact146_caption_transfer'
if (P/'data/job.json').exists():raise FileExistsError('Preserve existing146')
source=BASE/'verifact142_relevance_order_full1817'
old145=BASE/'verifact145_order_caption_old500'
P.mkdir(exist_ok=True)
if not (P/'tasks').exists():shutil.copytree(old145/'tasks',P/'tasks')
for sub in ['104_supervision_evidence','105_brief_supervision','136_claim_repeat_transfer']:
    sys.path.insert(0,str(P/'tasks'/sub))
import common105 as c
from prompt136 import prompt_ids
from transformers import AutoTokenizer
rows=c.rows(source/'data/inputs.jsonl')
old=c.read(source/'data/job.json')
assert len(rows)==1317
selected=sorted(rows,key=lambda r:hashlib.sha256(('caption_transfer|'+r['id']).encode()).hexdigest())[:400]
exemplar=c.rows(old145/'data/inputs.jsonl')[0]
oldref=rows[0]['reference'];newref=exemplar['reference']
OLD='Ordered by Time (Earliest to Latest):'
NEW='Ordered by BM25 Relevance (Highest to Lowest):'
assert OLD in oldref and NEW in newref
tok=AutoTokenizer.from_pretrained(old['model_dir'],local_files_only=True)
def encode(row):
    value=prompt_ids(tok,row)
    if hasattr(value,'get'):value=value['input_ids']
    if value and isinstance(value[0],list):value=value[0]
    return value
records=[];lengths=[]
for row in selected:
    assert row['reference'].count(OLD)==1 and row['reference'].index(OLD)==123
    out=dict(row)
    before=encode(row)
    assert c.digest(c.canonical(before))==row['prompt_token_sha256']
    out['reference']=row['reference'].replace(OLD,NEW,1)
    after=encode(out)
    if len(after)-len(before)!=3 or len(after)+384>16384:
        raise ValueError(f'Token lengths: before={len(before)}, after={len(after)}, before_type={type(before).__name__}')
    out['source_prompt_token_sha256']=row['prompt_token_sha256']
    out['prompt_token_sha256']=c.digest(c.canonical(after))
    records.append(out)
    lengths.append(dict(id=row['id'],input_tokens=len(after),prompt_token_sha256=out['prompt_token_sha256']))
ids=[r['id'] for r in records];ls={r['id']:r['input_tokens'] for r in lengths}
order=sorted(ids,key=lambda i:(ls[i],i));batches=[]
while order:
    batch=order[:2] if ls[order[0]]<=12701 else order[:1]
    if max(ls[i] for i in batch)>12701:batch=batch[:1]
    batches.append(batch);order=order[len(batch):]
start=datetime(2026,10,31,21,12,tzinfo=timezone(timedelta(hours=8))).timestamp()
session=dict(start_epoch=start,duration_seconds=43200,hourly_CNY=1.58,GPU_cap_CNY=18.96,
             API_cap_CNY=80,API_used_CNY=0,no_shutdown=True,end_epoch=start+43200)
job=dict(old,task=146,arm='order_caption',scope='transfer400',expected_N=400,target_N=400,prior_N=0,
         ids=ids,batches=batches,compute_limit_seconds=1500,save_reserve_seconds=180,new_training=False,
         selection_rule='lowest400 SHA256(caption_transfer|ID) among existing142 new1317; no GT',
         inputs='data/inputs.jsonl')
c.putl(P/'data/inputs.jsonl',records);c.putl(P/'data/lengths.jsonl',lengths)
c.put(P/'data/job.json',job);c.put(P/'data/session.json',session)
worker=(old145/'tasks/145_order_caption/worker145.py').read_text()
worker=worker.replace("assert job['task']==145", "assert job['task']==146").replace('task=145','task=146')
(P/'tasks/145_order_caption/worker145.py').write_text(worker,encoding='utf-8')
c.put(P/'preparation.json',dict(task=146,N=400,token_delta=3,new_training=False,GT_used_for_selection=False,
    prepared_epoch=time.time(),selection=job['selection_rule'],global_end_epoch=start+43200))
print(json.dumps(dict(prepared=True,N=400,batches=len(batches),path=str(P))))
