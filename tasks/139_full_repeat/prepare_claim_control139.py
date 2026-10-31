"""Prepare only missing fixed-scope runtime controls; no inference/retokenization."""
from pathlib import Path
import ast,json,shutil,sys,tarfile
R=Path(__file__).resolve().parents[2];P=R/'.local_models/139_full_repeat'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
RUNS={'screen160':'claim_control160','old500':'claim_control_old500','full1817':'claim_control_full1817'}


def source136():
    original=R/'.local_models/136_claim_repeat_transfer';inputs={};receipts={}
    for scope in RUNS:
        for row in c.rows(original/('claim_repeat_'+scope)/'bundle/data/inputs.jsonl'):
            i=row['id']
            if i in inputs and inputs[i]!=row:raise ValueError('Conflicting136 input')
            inputs[i]=row
        for file in (original/'evidence'/scope/'claim_repeat').glob('*.json'):
            row=c.read(file)
            if 'id' not in row:continue
            i=row['id']
            if i in receipts and receipts[i]!=row:raise ValueError('Conflicting136 first receipt')
            receipts[i]=row
    assert len(inputs)==len(receipts)==1817 and set(inputs)==set(receipts)
    for i,row in inputs.items():
        assert set(row)=={'id','claim','reference','prompt_token_sha256'}
        assert row['prompt_token_sha256']==receipts[i]['prompt_token_sha256']
    return inputs,receipts


def plan(scope):
    inputs,receipts=source136();settings=c.read(P/'source/settings.json')
    keys={r['id']:r for r in c.rows(R/'.local_models/134_author_baselines/keys.jsonl')}
    screen=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
    old500={i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')}
    target=screen if scope=='screen160' else (old500 if scope=='old500' else set(keys))
    required=set() if scope=='screen160' else (screen if scope=='old500' else old500)
    prior={}
    for run in RUNS.values():
        for file in (P/run/'evidence/claim_control').glob('*.json'):
            row=c.read(file)
            if 'id' not in row:continue
            i=row['id']
            if i not in inputs or row.get('arm')!='claim_control' or row.get('adapter_sha256')!=settings['adapter_sha256']:
                raise ValueError('Wrong prior control arm/checkpoint/ID')
            if row['prompt_token_sha256']!=inputs[i]['prompt_token_sha256']:raise ValueError('Changed prior control prompt')
            if i in prior and prior[i]!=row:raise ValueError('Conflicting first control receipts')
            prior[i]=row
    if not required<=set(prior):raise ValueError('Previous control scope lacks returned first receipts; no expansion')
    needed=sorted(target-set(prior),key=lambda i:(-receipts[i]['input_tokens'],i))
    expected={'screen160':160,'old500':340,'full1817':1317}[scope]
    if len(needed)!=expected:raise ValueError(f'Expected exactly{expected} missing IDs, found{len(needed)}; inspect existing work')
    rows=[inputs[i] for i in needed]
    lengths=[dict(id=i,input_tokens=receipts[i]['input_tokens'],prompt_token_sha256=inputs[i]['prompt_token_sha256']) for i in needed]
    assert all(r['input_tokens']+384<=32768 for r in lengths)
    return rows,lengths,needed,target,prior


def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=list(RUNS),default='screen160')
    ap.add_argument('--compute-seconds',type=int);ap.add_argument('--check-only',action='store_true');args=ap.parse_args()
    scope=args.scope;run=RUNS[scope];Q=P/run
    rows,lengths,order,targets,prior=plan(scope)
    if args.check_only:
        print(c.canonical(dict(scope=scope,target_N=len(targets),new_IDs=len(order),prior_N=len(targets&prior.keys()),
            prior_invalid=sum(not prior[i]['parsed']['valid'] for i in targets&prior.keys()),no_files_written=True,no_GPU=True)))
        return
    if args.compute_seconds is None or args.compute_seconds<300:ap.error('--compute-seconds must explicitly allocate at least300 seconds')
    if Q.exists():raise FileExistsError(run+' already prepared; preserve first-request identity')
    compute_seconds=args.compute_seconds
    settings=c.read(P/'source/settings.json');session=c.read(P/'source/session.json')
    job=dict(settings,task=139,name=run,variant='claim_control',scope=scope,
        inputs='data/inputs.jsonl',expected_N=len(order),target_N=len(targets),prior_N=len(targets)-len(order),ids=order,first_formal_ID=order[0],
        compute_limit_seconds=compute_seconds,save_reserve_seconds=900,total_stage_limit_seconds=compute_seconds+900,
        first_receipts_only=True,no_training=True,no_shutdown=True)
    assert job['generation']['batch_size']==1 and job['max_seq_length']==32768
    B=Q/'bundle';c.putl(B/'data/inputs.jsonl',rows);c.putl(B/'data/lengths.jsonl',lengths)
    c.put(B/'data/job.json',job);c.put(Q/'job.json',job);c.put(B/'data/session.json',session)
    T=B/'tasks/139_full_repeat';T.mkdir(parents=True)
    worker=(R/'tasks/139_full_repeat/worker139.py').read_text(encoding='utf-8-sig')
    anchor='from prompt139 import prompt_ids, assert_unchanged_rope'
    assert worker.count(anchor)==1
    worker=worker.replace(anchor,"from prompt139 import assert_unchanged_rope\nsys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'))\nfrom prompt136 import prompt_ids")
    worker=worker.replace('full_repeat','claim_control')
    #The only change to the completed runtime is prompt source and arm naming.
    (T/'worker_claim_control139.py').write_bytes(worker.encode('utf-8'))
    controller=(R/'tasks/139_full_repeat/controller139.py').read_text(encoding='utf-8-sig')
    assert controller.count('worker139.py')==1
    controller=controller.replace('worker139.py','worker_claim_control139.py')
    (T/'controller_claim_control139.py').write_bytes(controller.encode('utf-8'))
    for rel in ['tasks/139_full_repeat/prompt139.py','tasks/139_full_repeat/budget139.py',
                'tasks/136_claim_repeat_transfer/prompt136.py','tasks/104_supervision_evidence/training104.py',
                'tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']:
        dest=B/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
    start=(R/'tasks/139_full_repeat/start139.py').read_text(encoding='utf-8-sig').replace('controller139.py','controller_claim_control139.py')
    (Q/'start.py').write_bytes(start.encode('utf-8'))
    monitor=(R/'tasks/139_full_repeat/monitor139.py').read_text(encoding='utf-8-sig')
    before="parser=argparse.ArgumentParser();parser.add_argument('--scope',required=True,choices=['screen160','old500','full1817'])"
    assert before in monitor
    monitor=monitor.replace(before,'parser=argparse.ArgumentParser()').replace("scope=args.scope","scope="+repr(run))
    monitor=monitor.replace("R=Path(__file__).resolve().parents[2]", "R=next(p for p in Path(__file__).resolve().parents if (p/'tasks/139_full_repeat/PROTOCOL.md').exists())")
    monitor=monitor.replace("remote='/root/autodl-tmp/verifact139_full_repeat_'+scope","remote="+repr('/root/autodl-tmp/verifact139_'+run))
    monitor=monitor.replace("evidence=P/'evidence'/scope","evidence=local/'evidence'")
    before="folders=[P/'evidence'/s/'full_repeat' for s in ['screen160','old500','full1817'] if (P/'evidence'/s/'full_repeat').exists()]"
    assert before in monitor
    monitor=monitor.replace(before,"folders=[local/'evidence'/'claim_control'] if (local/'evidence'/'claim_control').exists() else []")
    before="command=[sys.executable,'-B',str(R/'tasks/139_full_repeat/analyze139.py'),'--scope',scope,'--results',*[str(f) for f in folders],'--out',str(O)]"
    assert before in monitor
    monitor=monitor.replace(before,"command=[sys.executable,'-B',str(R/'tasks/139_full_repeat/analyze_claim_control139.py'),'--scope',"+repr(scope)+",'--out',str(local/'comparison')]")
    monitor=monitor.replace("if scope=='full1817':command.append('--bootstrap')","if job['scope']=='full1817':command.append('--bootstrap')")
    monitor=monitor.replace('#139 full_repeat实时进度','#139 claim_control实时进度')
    (Q/'monitor.py').write_bytes(monitor.encode('utf-8'))
    for file in list(B.rglob('*.py'))+[Q/'start.py',Q/'monitor.py']:
        ast.parse(file.read_text(encoding='utf-8'),filename=str(file));assert not file.read_bytes().startswith(b'\xef\xbb\xbf')
    assert "variant'] == 'claim_control'" in worker and "from prompt136 import prompt_ids" in worker
    assert "batch_size'] == 1" in worker and "max_seq_length'] == 32768" in worker
    with tarfile.open(Q/'bundle.tar.gz','w:gz',compresslevel=1) as archive:
        for file in B.rglob('*'):
            if file.is_file():archive.add(file,arcname=file.relative_to(B),recursive=False)
    result=dict(task=139,status='CPU_READY_NOT_RUN',arm='claim_control',scope=scope,N=len(order),target_N=len(targets),
        prior_N=len(targets)-len(order),prior_invalid=sum(not prior[i]['parsed']['valid'] for i in targets&prior.keys()),
        input='Exact136 claim_repeat caches',new_tokenization=False,max_input_tokens=max(x['input_tokens'] for x in lengths),
        batch_size=1,capacity=32768,compute_limit_seconds=compute_seconds,save_reserve_seconds=900,total_stage_limit_seconds=compute_seconds+900,
        source_worker_sha256=c.sha(R/'tasks/139_full_repeat/worker139.py'),source_adapter_sha256=job['adapter_sha256'],
        archive_sha256=c.sha(Q/'bundle.tar.gz'),archive_bytes=(Q/'bundle.tar.gz').stat().st_size,
        static_check='PASS',new_GPU=False,new_API=0)
    c.put(Q/'preparation.json',result);print(c.canonical(result))


if __name__=='__main__':main()
