"""Conditional140 evaluation extension; imports/compilation never prepare or run."""
from pathlib import Path,PurePosixPath
import argparse,re,shutil,sys,tarfile
R=Path(__file__).resolve().parents[2];P=R/'.local_models/140_kl_anchor';E=P/'extension'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/138_rationale_tasks'));from prepare_eval138 import keep_first
ARM='kl_anchor'


def render_template(source):
    source=source.replace('worker_eval138.py','worker_eval140.py').replace('prepare_eval138.py','prepare_eval140.py')
    source=source.replace('tasks/138_rationale_tasks','tasks/140_kl_anchor').replace('.local_models/138_rationale_tasks/extension','.local_models/140_kl_anchor/extension')
    source=source.replace('outputs/138_rationale_tasks','outputs/140_kl_anchor')
    source=source.replace('verifact138_eval_','verifact140_eval_').replace('task=138','task=140')
    source=source.replace('return_eval138','return_eval140').replace('# 138 实时进度','# 140 实时进度')
    source=source.replace('Private138','Private140').replace('current138 control or any other task','current140 or any other task')
    source=source.replace('两臂48步训练及160首筛已完成','140固定48步训练及前阶段评价已完成')
    source=source.replace("choices=['rationale_tasks','label_replay'],required=True","choices=['kl_anchor'],default='kl_anchor'")
    return source.replace("P=R/'.local_models/140_kl_anchor/extension'/args.arm/args.scope","P=R/'.local_models/140_kl_anchor/extension'/args.scope")


def read_source136():
    """Read existing inputs/SHA/lengths only; no encoder or cache mutation."""
    inputs={};lengths={};base=R/'.local_models/136_claim_repeat_transfer'
    for scope in ('screen160','old500','full1817'):
        for row in c.rows(base/('claim_repeat_'+scope)/'bundle/data/inputs.jsonl'):
            i=row['id']
            if i in inputs and inputs[i]!=row:raise ValueError('Conflicting136 input')
            inputs[i]=row
        for file in (base/'evidence'/scope/'claim_repeat').glob('*.json'):
            row=c.read(file)
            if 'id' not in row:continue
            value=dict(id=row['id'],input_tokens=row['input_tokens'],prompt_token_sha256=row['prompt_token_sha256'])
            if value['id'] in lengths and lengths[value['id']]!=value:raise ValueError('Conflicting136 length/SHA')
            lengths[value['id']]=value
    if len(inputs)!=1817 or set(inputs)!=set(lengths):raise ValueError('Incomplete136 input inventory')
    for i,row in inputs.items():
        assert set(row)=={'id','claim','reference','prompt_token_sha256'}
        assert row['prompt_token_sha256']==lengths[i]['prompt_token_sha256'] and lengths[i]['input_tokens']+384<=16384
    return inputs,lengths


def plan(scope):
    if scope not in ('old500','full1817'):raise ValueError('Only fixed500/1817 extensions are supported')
    done=c.read(P/'evidence/training_done.json')
    if (done.get('steps'),done.get('consumed'),done.get('arm'))!=(48,384,ARM):
        raise ValueError('Actual140 final48/384 completion is required')
    checkpoint=PurePosixPath(done['final_checkpoint']);sha=done['adapter_sha256']
    if checkpoint.parent!=PurePosixPath('/root/autodl-tmp/verifact140_kl_anchor/results/train'):
        raise ValueError('Unexpected140 actual checkpoint parent')
    if not checkpoint.name.startswith('checkpoint_') or not re.fullmatch('[0-9a-f]{64}',sha):
        raise ValueError('Invalid140 checkpoint path/SHA')
    original_job=c.read(P/'bundle/data/job.json')
    if done.get('source120_sha256')!=original_job['source_sha256']:
        raise ValueError('Final140 checkpoint did not originate from the frozen120 source')
    #Each expansion requires its immediately preceding frozen signal, as well
    #as complete first-response coverage. Do not silently expand a failed500.
    reports=['screen160']+(['old500'] if scope=='full1817' else [])
    decisions={}
    for name in reports:
        path=R/'outputs/140_kl_anchor'/('kl_anchor_'+name+'.json');report=c.read(path)
        if (report.get('task'),report.get('arm'),report.get('scope'))!=(140,ARM,name):
            raise ValueError('Wrong140 screening report')
        if report.get('source_adapter_sha256')!=sha or report.get('screening',{}).get('continue_signal') is not True:
            raise ValueError('Expansion signal absent or belongs to another checkpoint')
        if report['coverage']['candidate']['missing_ids']:
            raise ValueError('Prior140 screening report still has missing first responses')
        decisions[name]=c.sha(path)
    inputs,lengths=read_source136();keys={r['id']:r for r in c.rows(R/'.local_models/134_author_baselines/keys.jsonl')}
    screen=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
    old500={i for i,row in keys.items() if row['old_panel'] in ('natural','pressure')}
    assert len(screen)==160 and len(old500)==500 and len(keys)==1817
    target=old500 if scope=='old500' else set(keys);prior={}
    for folder in [P/'evidence/predictions']+[E/s/'evidence'/ARM for s in ('old500','full1817')]:
        for file in folder.glob('*.json'):
            row=c.read(file)
            if 'id' in row:keep_first(prior,row,ARM,sha,inputs)
    for folder in [P/'evidence/batches']+[E/s/'evidence/batches' for s in ('old500','full1817')]:
        for file in folder.glob('*.json'):
            for row in c.read(file)['records']:keep_first(prior,row,ARM,sha,inputs)
    required=screen if scope=='old500' else old500
    if not required<=set(prior):raise ValueError('Prior scope has missing first receipts')
    needed=sorted(target-set(prior),key=lambda i:(lengths[i]['input_tokens'],i))
    expected=340 if scope=='old500' else 1317
    if len(needed)!=expected:raise ValueError('Expected exactly'+str(expected)+'new IDs; inspect prior work')
    return done,inputs,lengths,prior,target,needed,decisions


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scope',choices=['old500','full1817'],required=True)
    parser.add_argument('--compute-seconds',type=int,required=True);args=parser.parse_args()
    if args.compute_seconds<300:raise ValueError('At least300 explicit computation seconds required')
    done,inputs,lengths,prior,target,needed,decisions=plan(args.scope)
    work=E/args.scope;B=work/'bundle'
    if work.exists():raise FileExistsError('Prepared140 extension already exists; no overwrite/replay')
    c.putl(B/'data/inputs.jsonl',[inputs[i] for i in needed]);c.putl(B/'data/lengths.jsonl',[lengths[i] for i in needed])
    session=c.read(P/'bundle/data/session.json');session['save_reserve_seconds']=900;c.put(B/'data/session.json',session)
    original_job=c.read(P/'bundle/data/job.json')
    job=dict(task=140,kind='evaluation_extension',arm=ARM,scope=args.scope,
        model_dir=original_job['model_dir'],adapter=done['final_checkpoint'],adapter_sha256=done['adapter_sha256'],
        checkpoint_steps=48,checkpoint_consumed=384,max_seq_length=16384,inputs='data/inputs.jsonl',
        expected_N=len(needed),target_N=len(target),prior_N=len(target)-len(needed),ids=needed,
        generation=dict(dtype='bfloat16',thinking=False,max_new_tokens=384,do_sample=False,num_beams=1,
                        repetition_penalty=1.,batch_size=2,single_if_prompt_above=12701),
        compute_limit_seconds=args.compute_seconds,save_reserve_seconds=900,total_stage_limit_seconds=args.compute_seconds+900,
        first_receipts_only=True,new_training=False,no_shutdown=True,screening_report_SHA256=decisions)
    c.put(B/'data/job.json',job);c.put(work/'job.json',job)
    for rel in ['tasks/140_kl_anchor/worker_eval140.py','tasks/136_claim_repeat_transfer/prompt136.py',
                'tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']:
        dest=B/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
    #Reuse the existing private138 launch/observation templates. Only names and
    #workspace paths change. No model/checkpoint or teacher cache is packaged.
    templates=R/'.local_models/138_rationale_tasks/extension/templates'
    for name in ('start.py','monitor.py'):
        source=render_template((templates/name).read_text(encoding='utf-8-sig'))
        (work/name).write_bytes(source.encode('utf-8'))
    with tarfile.open(work/'bundle.tar.gz','w:gz',compresslevel=1) as archive:
        for file in B.rglob('*'):
            if file.is_file():archive.add(file,arcname=file.relative_to(B),recursive=False)
    c.put(work/'preparation.json',dict(status='PREPARED_NOT_RUN',task=140,arm=ARM,scope=args.scope,
        new_IDs=len(needed),target_N=len(target),reused_invalid=sum(not prior[i]['parsed']['valid'] for i in target&prior.keys()),
        adapter_sha256=done['adapter_sha256'],max_input_tokens=max(lengths[i]['input_tokens'] for i in needed),
        source136_retokenized=False,compute_limit_seconds=args.compute_seconds,save_reserve_seconds=900,
        initial140_screen_batch2=True,extension_long_inputs_batch1=True,no_new_training=True,new_API=0))
    print(c.canonical(dict(task=140,scope=args.scope,new_IDs=len(needed),prepared=True,no_GPU_started=True)))


if __name__=='__main__':main()
