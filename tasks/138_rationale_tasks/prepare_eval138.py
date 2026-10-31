"""Prepare missing138 evaluation IDs from frozen136 inputs; no tokenizer/model."""
from pathlib import Path, PurePosixPath
import argparse, json, re, shutil, sys, tarfile
R=Path(__file__).resolve().parents[2];P=R/'.local_models/138_rationale_tasks';E=P/'extension'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
ARMS=('rationale_tasks','label_replay')


def keep_first(found,row,arm,sha,inputs):
    i=row['id']
    if i not in inputs or row.get('arm')!=arm or row.get('adapter_sha256')!=sha:
        raise ValueError('Wrong138 arm/checkpoint/ID in prior first receipt')
    if row.get('prompt_token_sha256')!=inputs[i]['prompt_token_sha256']:
        raise ValueError('Prior answer used another prompt')
    if i in found and found[i]!=row:raise ValueError('Conflicting first receipts')
    found[i]=row


def source136():
    """Reuse bytes/SHAs and input lengths already observed by136, never encode."""
    cache=E/'source'
    if (cache/'ready.json').exists():
        return ({r['id']:r for r in c.rows(cache/'inputs.jsonl')},
                {r['id']:r for r in c.rows(cache/'lengths.jsonl')})
    inputs={};lengths={};base=R/'.local_models/136_claim_repeat_transfer'
    for scope in ('screen160','old500','full1817'):
        for row in c.rows(base/('claim_repeat_'+scope)/'bundle/data/inputs.jsonl'):
            i=row['id']
            if i in inputs and inputs[i]!=row:raise ValueError('Frozen136 inputs conflict')
            inputs[i]=row
        for f in (base/'evidence'/scope/'claim_repeat').glob('*.json'):
            row=c.read(f)
            if 'id' not in row:continue
            value=dict(id=row['id'],input_tokens=row['input_tokens'],prompt_token_sha256=row['prompt_token_sha256'])
            if value['id'] in lengths and lengths[value['id']]!=value:raise ValueError('Frozen136 lengths conflict')
            lengths[value['id']]=value
    if len(inputs)!=1817 or set(inputs)!=set(lengths):raise ValueError('Incomplete136 source cache')
    for i,row in inputs.items():
        assert set(row)=={'id','claim','reference','prompt_token_sha256'}
        assert row['prompt_token_sha256']==lengths[i]['prompt_token_sha256'] and lengths[i]['input_tokens']+384<=16384
    c.putl(cache/'inputs.jsonl',[inputs[i] for i in sorted(inputs)])
    c.putl(cache/'lengths.jsonl',[lengths[i] for i in sorted(lengths)])
    c.put(cache/'ready.json',dict(N=1817,source='Existing136 input strings, token SHA and measured lengths',retokenized=False))
    return inputs,lengths


def plan(arm,scope):
    if arm not in ARMS or scope not in ('old500','full1817'):raise ValueError('Unfrozen arm/scope')
    done=c.read(P/arm/'evidence/training_done.json')
    if (done.get('steps'),done.get('consumed'),done.get('arm'))!=(48,384,arm):raise ValueError('Actual completed48-step arm required')
    sha=done['adapter_sha256'];checkpoint=PurePosixPath(done['final_checkpoint'])
    expected=PurePosixPath('/root/autodl-tmp/verifact138_'+arm+'/results/train')
    if checkpoint.parent!=expected or not checkpoint.name.startswith('checkpoint_') or not re.fullmatch('[0-9a-f]{64}',sha):
        raise ValueError('Unexpected actual138 checkpoint path/SHA')
    inputs,lengths=source136()
    keys={r['id']:r for r in c.rows(R/'.local_models/134_author_baselines/keys.jsonl')}
    screen=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
    old500={i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')}
    assert len(screen)==160 and len(old500)==500 and len(keys)==1817
    target=old500 if scope=='old500' else set(keys)
    prior={}
    folders=[P/arm/'evidence/predictions',P/arm/'evidence/old500',P/arm/'evidence/full1817']
    folders += [E/arm/stage/'evidence'/arm for stage in ('old500','full1817')]
    for folder in folders:
        for f in folder.glob('*.json'):
            row=c.read(f)
            if 'id' in row:keep_first(prior,row,arm,sha,inputs)
    #Committed batch containers also count if a later interruption prevented
    #writing some convenience per-ID files; never issue those answers again.
    batch_folders=[P/arm/'evidence/batches']+[E/arm/stage/'evidence/batches' for stage in ('old500','full1817')]
    for folder in batch_folders:
        for f in folder.glob('*.json'):
            for row in c.read(f)['records']:keep_first(prior,row,arm,sha,inputs)
    required=screen if scope=='old500' else old500
    if not required<=set(prior):raise ValueError('Previous stage lacks returned first receipts')
    needed=sorted(target-set(prior),key=lambda i:(lengths[i]['input_tokens'],i))
    expected_new=340 if scope=='old500' else 1317
    if len(needed)!=expected_new:
        raise ValueError('Expected exactly'+str(expected_new)+'new IDs; existing extension must be inspected')
    return done,inputs,lengths,prior,target,needed


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=ARMS,required=True)
    ap.add_argument('--scope',choices=['old500','full1817'],required=True)
    ap.add_argument('--compute-seconds',type=int,required=True);args=ap.parse_args()
    if args.compute_seconds<300:raise ValueError('Explicit compute allocation must be at least300 seconds')
    done,inputs,lengths,prior,target,needed=plan(args.arm,args.scope)
    work=E/args.arm/args.scope;bundle=work/'bundle'
    if work.exists():raise FileExistsError('Extension exists; do not overwrite or rerun first receipts')
    c.putl(bundle/'data/inputs.jsonl',[inputs[i] for i in needed])
    c.putl(bundle/'data/lengths.jsonl',[lengths[i] for i in needed])
    session=c.read(P/args.arm/'bundle/data/session.json');session['save_reserve_seconds']=900
    c.put(bundle/'data/session.json',session)
    job=dict(task=138,kind='evaluation_extension',arm=args.arm,scope=args.scope,
        model_dir='/root/verifact_image/models/qwen3.5-9b',adapter=done['final_checkpoint'],adapter_sha256=done['adapter_sha256'],
        checkpoint_steps=48,checkpoint_consumed=384,max_seq_length=16384,inputs='data/inputs.jsonl',
        expected_N=len(needed),target_N=len(target),prior_N=len(target)-len(needed),ids=needed,
        generation=dict(dtype='bfloat16',thinking=False,max_new_tokens=384,do_sample=False,num_beams=1,
                        repetition_penalty=1.,batch_size=2,single_if_prompt_above=12701),
        compute_limit_seconds=args.compute_seconds,save_reserve_seconds=900,
        total_stage_limit_seconds=args.compute_seconds+900,first_receipts_only=True,new_training=False,no_shutdown=True)
    c.put(bundle/'data/job.json',job);c.put(work/'job.json',job)
    rels=['tasks/138_rationale_tasks/worker_eval138.py','tasks/136_claim_repeat_transfer/prompt136.py',
          'tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']
    for rel in rels:
        dest=bundle/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
    for name in ['start.py','monitor.py']:shutil.copy2(E/'templates'/name,work/name)
    with tarfile.open(work/'bundle.tar.gz','w:gz',compresslevel=1) as archive:
        for f in bundle.rglob('*'):
            if f.is_file():archive.add(f,arcname=f.relative_to(bundle),recursive=False)
    summary=dict(status='PREPARED_NOT_RUN',arm=args.arm,scope=args.scope,new_IDs=len(needed),target_N=len(target),
        reused_first_receipts=len(target)-len(needed),reused_invalid=sum(not prior[i]['parsed']['valid'] for i in target&prior.keys()),
        adapter=done['final_checkpoint'],adapter_sha256=done['adapter_sha256'],checkpoint_steps=48,
        max_input_tokens=max(lengths[i]['input_tokens'] for i in needed),source136_retokenized=False,
        compute_limit_seconds=args.compute_seconds,save_reserve_seconds=900,total_stage_limit_seconds=args.compute_seconds+900,
        same_generation_as136=True,screen138_used_batch2_for_all=True,extension_uses_long_input_batch1=True,new_API=0)
    c.put(work/'preparation.json',summary);print(c.canonical(summary))


if __name__=='__main__':main()
