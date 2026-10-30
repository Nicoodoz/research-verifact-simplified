"""Prepare one fixed presentation candidate using existing120 weights."""
from pathlib import Path
import argparse,json,shutil,sys,tarfile
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'.local_models/130_header_blocks'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as c
from data105 import shared
from tokenizer_cpu105 import CPUPinnedTokenizer
sys.path.insert(0,str(ROOT/'tasks/120_full_pool_sft'))
from analyze120 import collect
from format130 import group_reference


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',choices=['screen160','old500'],default='screen160')
    a=p.parse_args()
    keys=c.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    ids=c.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids']
    target=ids if a.scope=='screen160' else sorted(r['id'] for r in keys if r['old_panel'] in ('natural','pressure'))
    prior=collect([P/'evidence/header_blocks_screen160']) if a.scope=='old500' else []
    if a.scope=='old500':
        decision=c.read(ROOT/'outputs/130_header_blocks/screen160.json')['screen']
        if not decision['continue_']:raise RuntimeError('Fixed160 did not justify expansion')
        if len(prior)!=160:raise ValueError('Expansion must reuse all160 first receipts')
    complete={r['id'] for r in prior};needed=[i for i in target if i not in complete]
    source={r['id']:r for r in c.rows(ROOT/'.local_models/116_research_cycle/inputs_selection1817.jsonl')}
    tokenizer=CPUPinnedTokenizer(ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    inputs=[];mapping=[]
    for i in needed:
        r=source[i];changed,fragments,counts=group_reference(r['reference'])
        row=dict(id=i,claim=r['claim'],reference=changed)
        tokens=shared.prompt_ids(tokenizer,row)
        if len(tokens)+384>16384:raise ValueError('Complete transformed context too long')
        row['expected_prompt_sha256']=c.digest(c.canonical(tokens));inputs.append(row)
        original_n=len(shared.prompt_ids(tokenizer,r))
        mapping.append(dict(id=i,original_prompt_sha256=r['expected_prompt_sha256'],
            changed_prompt_sha256=row['expected_prompt_sha256'],source_input_tokens=original_n,
            input_tokens=len(tokens),fragments=fragments,**counts))
    done=c.read(ROOT/'.local_models/120_full_pool_sft/resume369/evidence/full_pool_sft/training_done.json')
    if (done['steps'],done['consumed'])!=(369,2945):raise ValueError('Use retained120 final369 only')
    if any(r['source_adapter_sha256']!=done['adapter_sha256'] for r in prior):raise ValueError('Wrong prior checkpoint')
    window=c.read(ROOT/'.local_models/CURRENT_RESEARCH.json')['window']
    session=dict(start_epoch=window['start_epoch'],duration_seconds=window['deadline_epoch']-window['start_epoch'],
        GPU_cap_CNY=window['GPU_cap_CNY'],hourly_CNY=window['hourly_CNY'],no_shutdown=True)
    bundle=P/'bundle';relative='data/header_blocks/'+a.scope;data=bundle/relative
    data.mkdir(parents=True,exist_ok=True)
    c.frozen(data/'session.json',(json.dumps(session,indent=2)+'\n').encode())
    c.frozen(data/'inputs.jsonl',''.join(c.canonical(r)+'\n' for r in inputs).encode())
    c.putl(P/(a.scope+'_source_map.jsonl'),mapping)
    job=dict(name='header_blocks_'+a.scope,task=130,candidate='header_blocks',
        model_dir='/root/verifact_image/models/qwen3.5-9b',final_adapter=done['final_checkpoint'],
        adapter_sha256=done['adapter_sha256'],inputs_path=relative+'/inputs.jsonl',
        session_path=relative+'/session.json',session_sha256=c.sha(data/'session.json'),ids=needed,N=len(needed),
        max_seq_length=16384,seed=117027,evaluation=dict(batch_size=2,max_new_tokens=384,
            do_sample=False,num_beams=1,repetition_penalty=1.,parser='parse105.parse'),
        phase_limit_seconds=1200 if a.scope=='screen160' else 1800,save_reserve_seconds=90,
        no_training=True,no_shutdown=True,first_receipts_only=True)
    c.frozen(data/'job.json',(json.dumps(job,indent=2)+'\n').encode())
    for relative_file in ['tasks/130_header_blocks/run130.py','tasks/128_sqrt_weight_refresh/extend128.py',
        'tasks/120_full_pool_sft/analyze120.py','tasks/105_brief_supervision/common105.py',
        'tasks/105_brief_supervision/parse105.py','tasks/105_brief_supervision/data105.py',
        'tasks/104_supervision_evidence/training104.py']:
        destination=bundle/relative_file;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/relative_file,destination)
    with tarfile.open(P/('bundle130_'+a.scope+'.tar.gz'),'w:gz',compresslevel=1) as t:
        for f in bundle.rglob('*'):
            if f.is_file():t.add(f,arcname=f.relative_to(bundle),recursive=False)
    original=sum(r['source_input_tokens'] for r in mapping);current=sum(r['input_tokens'] for r in mapping)
    report=dict(scope=a.scope,N=len(inputs),prior_first_receipts_reused=len(prior),
        original_input_tokens=original,grouped_input_tokens=current,input_reduction_fraction=1-current/original,
        full_text_and_order_preserved=True,GT_free_inputs=True,source_adapter_sha256=done['adapter_sha256'],
        training=False,API=0,GPU_started=False)
    c.put(ROOT/'outputs/130_header_blocks'/(a.scope+'_preparation.json'),report)
    print(c.canonical(report))


if __name__=='__main__':main()
