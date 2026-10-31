"""Prepare the necessary160-ID runtime control; no inference or retokenization."""
from pathlib import Path
import ast,json,shutil,sys,tarfile
R=Path(__file__).resolve().parents[2];P=R/'.local_models/139_full_repeat';Q=P/'claim_control160'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c


def main():
    if Q.exists():raise FileExistsError('claim_control160 already prepared; preserve first-request identity')
    original=R/'.local_models/136_claim_repeat_transfer'
    rows=c.rows(original/'claim_repeat_screen160/bundle/data/inputs.jsonl')
    targets=set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
    assert len(rows)==160 and {r['id'] for r in rows}==targets
    receipts={}
    for file in (original/'evidence/screen160/claim_repeat').glob('*.json'):
        row=c.read(file)
        if 'id' in row:receipts[row['id']]=row
    assert set(receipts)==targets
    lengths=[]
    for row in rows:
        assert set(row)=={'id','claim','reference','prompt_token_sha256'}
        old=receipts[row['id']];assert row['prompt_token_sha256']==old['prompt_token_sha256']
        lengths.append(dict(id=row['id'],input_tokens=old['input_tokens'],prompt_token_sha256=row['prompt_token_sha256']))
    order=sorted(targets,key=lambda i:(-receipts[i]['input_tokens'],i))
    settings=c.read(P/'source/settings.json');session=c.read(P/'source/session.json')
    job=dict(settings,task=139,name='claim_control160',variant='claim_control',scope='claim_control160',
        inputs='data/inputs.jsonl',expected_N=160,target_N=160,prior_N=0,ids=order,first_formal_ID=order[0],
        compute_limit_seconds=1800,save_reserve_seconds=900,total_stage_limit_seconds=2700,
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
    monitor=monitor.replace(before,'parser=argparse.ArgumentParser()').replace("scope=args.scope","scope='claim_control160'")
    monitor=monitor.replace("R=Path(__file__).resolve().parents[2]", "R=next(p for p in Path(__file__).resolve().parents if (p/'tasks/139_full_repeat/PROTOCOL.md').exists())")
    monitor=monitor.replace("remote='/root/autodl-tmp/verifact139_full_repeat_'+scope","remote='/root/autodl-tmp/verifact139_claim_control160'")
    monitor=monitor.replace("evidence=P/'evidence'/scope","evidence=local/'evidence'")
    before="folders=[P/'evidence'/s/'full_repeat' for s in ['screen160','old500','full1817'] if (P/'evidence'/s/'full_repeat').exists()]"
    assert before in monitor
    monitor=monitor.replace(before,"folders=[local/'evidence'/'claim_control'] if (local/'evidence'/'claim_control').exists() else []")
    before="command=[sys.executable,'-B',str(R/'tasks/139_full_repeat/analyze139.py'),'--scope',scope,'--results',*[str(f) for f in folders],'--out',str(O)]"
    assert before in monitor
    monitor=monitor.replace(before,"command=[sys.executable,'-B',str(R/'tasks/139_full_repeat/analyze_claim_control139.py'),'--control',str(folders[0]),'--out',str(local/'comparison')]")
    monitor=monitor.replace('#139 full_repeat实时进度','#139 claim_control实时进度')
    (Q/'monitor.py').write_bytes(monitor.encode('utf-8'))
    for file in list(B.rglob('*.py'))+[Q/'start.py',Q/'monitor.py']:
        ast.parse(file.read_text(encoding='utf-8'),filename=str(file));assert not file.read_bytes().startswith(b'\xef\xbb\xbf')
    assert "variant'] == 'claim_control'" in worker and "from prompt136 import prompt_ids" in worker
    assert "batch_size'] == 1" in worker and "max_seq_length'] == 32768" in worker
    with tarfile.open(Q/'bundle.tar.gz','w:gz',compresslevel=1) as archive:
        for file in B.rglob('*'):
            if file.is_file():archive.add(file,arcname=file.relative_to(B),recursive=False)
    result=dict(task=139,status='CPU_READY_NOT_RUN',arm='claim_control',N=160,
        input='Exact136 screen160 claim_repeat cache',new_tokenization=False,max_input_tokens=max(x['input_tokens'] for x in lengths),
        batch_size=1,capacity=32768,compute_limit_seconds=1800,save_reserve_seconds=900,total_stage_limit_seconds=2700,
        source_worker_sha256=c.sha(R/'tasks/139_full_repeat/worker139.py'),source_adapter_sha256=job['adapter_sha256'],
        archive_sha256=c.sha(Q/'bundle.tar.gz'),archive_bytes=(Q/'bundle.tar.gz').stat().st_size,
        static_check='PASS',new_GPU=False,new_API=0)
    c.put(Q/'preparation.json',result);print(c.canonical(result))


if __name__=='__main__':main()
