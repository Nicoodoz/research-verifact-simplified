"""Prepare only missing IDs for the chosen native-order experiment; CPU only."""
from pathlib import Path
import argparse,json,shutil,sys,tarfile
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'.local_models/135_reason_first';O=ROOT/'outputs/135_reason_first'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));import common105 as c
from tokenizer_cpu105 import CPUPinnedTokenizer
import prompt135

def main():
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=['screen160','old500','full1817'],required=True)
    p.add_argument('--variant',choices=['reason_first','verdict_prefix'],default='reason_first');p.add_argument('--prior',type=Path,nargs='*',default=[])
    args=p.parse_args();B=ROOT/'.local_models/134_author_baselines';original=c.read(B/'job.json')
    keys=c.rows(B/'keys.jsonl');all_ids={r['id'] for r in keys}
    target=set(original['phases'][0]['ids']) if args.scope=='screen160' else ({r['id'] for r in keys if r['old_panel'] in ('natural','pressure')} if args.scope=='old500' else all_ids)
    prior={}
    for folder in args.prior:
        for f in folder.glob('*.json'):
            r=c.read(f)
            if 'id' not in r:continue
            if r.get('arm')!=args.variant or r['id'] not in target:raise ValueError('Wrong prior scope or variant')
            if r['id'] in prior and prior[r['id']]['content']!=r['content']:raise ValueError('Conflicting prior first receipt')
            prior[r['id']]=r
    needed=sorted(target-set(prior));assert needed
    prefix=prompt135.configure(args.variant)
    assert all(label not in prefix for label in c.LABELS)
    inputs={r['id']:r for r in c.rows(B/'bundle/data/inputs.jsonl')}
    tok=CPUPinnedTokenizer(ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    records=[];lengths=[];prefix_lengths=set()
    for i in needed:
        row={k:inputs[i][k] for k in ('id','claim','reference')}
        ids=prompt135.prompt_ids(tok,row);base=prompt135.unprefilled_ids(tok,row)
        added=len(ids)-len(base);prefix_lengths.add(added)
        assert added>0 and tok.decode(ids[-50:]).endswith(prefix)
        row['prompt_token_sha256']=c.digest(c.canonical(ids));records.append(row);lengths.append(len(ids))
    assert len(prefix_lengths)==1;prefix_tokens=prefix_lengths.pop()
    max_new=768-prefix_tokens;assert max(lengths)+max_new<=16384
    run=args.variant+'_'+args.scope;root=P/run;bundle=root/'bundle'
    c.putl(bundle/'data/inputs.jsonl',records)
    session=c.read(B/'session.json');c.put(bundle/'data/session.json',session)
    job=dict(task=135,name=run,variant=args.variant,arms=[args.variant],model_dir=original['model_dir'],adapter=original['adapter'],
        adapter_bytes=original['adapter_bytes'],max_seq_length=16384,inputs='data/inputs.jsonl',session='data/session.json',
        expected_N=len(needed),target_N=len(target),prior_N=len(prior),prefix_tokens=prefix_tokens,response_prefix=prefix,
        generation=dict(dtype='bfloat16',thinking=False,max_new_tokens=max_new,total_answer_token_budget=768,do_sample=False,num_beams=1,repetition_penalty=1.,batch_size=2,single_if_prompt_above=12500),
        phases=[dict(name=args.scope,ids=needed)],phase_limit_seconds=max(2400,int(len(needed)*7+600)),first_receipts_only=True,no_training=True,no_shutdown=True)
    c.put(bundle/'data/job.json',job);c.put(root/'job.json',job)
    for rel in ['tasks/135_reason_first/worker135.py','tasks/135_reason_first/prompt135.py','tasks/134_author_baselines/prompt134.py',
                'tasks/103_lora_selection/parse103.py','tasks/105_brief_supervision/common105.py']:
        dest=bundle/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest)
    with tarfile.open(root/'bundle.tar.gz','w:gz',compresslevel=1) as t:
        for f in bundle.rglob('*'):
            if f.is_file():t.add(f,arcname=f.relative_to(bundle),recursive=False)
    summary=dict(status='PREPARED_NOT_RUN',variant=args.variant,scope=args.scope,target_N=len(target),prior_receipts=len(prior),
        prior_invalid=sum(not r['parsed']['valid'] for r in prior.values()),new_calls=len(needed),prefix_tokens=prefix_tokens,
        generated_token_cap=max_new,total_answer_token_budget=768,max_input_tokens=max(lengths),same_claim_reference=True,
        same_120_weights=True,new_training=False,new_API=0,global_window_start=session['start_local'],GPU_cap_CNY=session['GPU_cap_CNY'])
    O.mkdir(parents=True,exist_ok=True);c.put(O/(run+'_preparation.json'),summary);c.put(root/'preparation.json',summary)
    print(c.canonical(summary))

if __name__=='__main__':main()
