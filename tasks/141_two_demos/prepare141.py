"""Prepare141 stage without GPU; only160 is currently authorized to package."""
from pathlib import Path
import argparse,ast,shutil,sys,tarfile
R=Path(__file__).resolve().parents[2];P=R/'.local_models/141_two_demos'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
from tokenizer_cpu105 import CPUPinnedTokenizer
from prompt141 import EXAMPLE_IDS,prompt_ids,messages,original136_messages
from initialize141 import freeze


def prior_receipts(inputs,demos_sha,adapter_sha):
    result={}
    for scope in ('screen160','old500','full1817'):
        for folder in (P/'evidence'/scope/'two_demos',P/scope/'evidence/two_demos'):
            for file in folder.glob('*.json'):
                row=c.read(file)
                if 'id' not in row:continue
                i=row['id']
                if i not in inputs or row.get('arm')!='two_demos' or row.get('adapter_sha256')!=adapter_sha or row.get('demos_sha256')!=demos_sha:
                    raise ValueError('Wrong prior141 identity')
                if row.get('target_prompt_token_sha256')!=inputs[i]['prompt_token_sha256']:raise ValueError('Changed original target')
                if i in result and row!=result[i]:raise ValueError('Conflicting first141 receipts')
                result[i]=row
    return result


def prepare(scope,compute_seconds=None):
    tok=CPUPinnedTokenizer(R/'.local_models/103_lora_selection/models/qwen3.5-9b')
    source=P/'source'
    if not (source/'freeze.json').exists():freeze(tok)
    proof=c.read(source/'freeze.json');settings=c.read(source/'settings.json');examples=c.rows(source/'examples.jsonl')
    demos_sha=c.sha(source/'examples.jsonl');assert demos_sha==proof['demos_sha256']
    inputs={r['id']:r for r in c.rows(source/'inputs136.jsonl')};old_lengths={r['id']:r for r in c.rows(source/'lengths136.jsonl')}
    screen=set(c.read(source/'screen160_ids.json'));old500=set(c.read(source/'old500_ids.json'))
    target=screen if scope=='screen160' else (old500 if scope=='old500' else set(inputs))
    prior=prior_receipts(inputs,demos_sha,settings['adapter_sha256'])
    if scope!='screen160':
        previous='screen160' if scope=='old500' else 'old500'
        report=c.read(R/'outputs/141_two_demos'/('two_demos_'+previous+'.json'))
        if report.get('screening',{}).get('continue_signal') is not True or report.get('source_adapter_sha256')!=settings['adapter_sha256']:
            raise ValueError('Prior scope has no matching positive signal')
        if report.get('demos_sha256')!=demos_sha:raise ValueError('Prior signal used different demonstrations')
        required=screen if scope=='old500' else old500
        if not required<=set(prior):raise ValueError('Prior scope first responses incomplete')
        if compute_seconds is None:raise ValueError('Expanded stage requires explicit compute-seconds')
    elif compute_seconds not in (None,1500):raise ValueError('Frozen screen computation cap1500')
    compute_seconds=compute_seconds or 1500
    if compute_seconds<300:raise ValueError('Insufficient computation allocation')
    needed=sorted(target-set(prior));assert len(needed)=={'screen160':160,'old500':340,'full1817':1317}[scope]
    work=P/scope;B=work/'bundle'
    if work.exists():raise FileExistsError('Prepared141 phase exists; no overwrite/replay')
    records=[];lengths=[]
    for i in needed:
        row=inputs[i];ids=prompt_ids(tok,row,examples);target_sha=row['prompt_token_sha256'];length=len(ids)
        assert messages(row,examples)[-1]==original136_messages(row)[-1]
        assert length<=old_lengths[i]['input_token_upper_bound'] and length+384<=32768
        full_sha=c.digest(c.canonical(ids))
        records.append(dict(id=i,claim=row['claim'],reference=row['reference'],prompt_token_sha256=full_sha,target_prompt_token_sha256=target_sha))
        lengths.append(dict(id=i,input_tokens=length,prompt_token_sha256=full_sha,
            target_input_tokens=old_lengths[i]['target_input_tokens'],target_prompt_token_sha256=target_sha,demos_sha256=demos_sha))
    order=sorted(needed,key=lambda i:(-next(r['input_tokens'] for r in lengths if r['id']==i),i))
    c.putl(B/'data/inputs.jsonl',records);c.putl(B/'data/lengths.jsonl',lengths)
    (B/'data').mkdir(parents=True,exist_ok=True);shutil.copy2(source/'examples.jsonl',B/'data/examples.jsonl')
    session=c.read(source/'session.json');c.put(B/'data/session.json',session)
    job=dict(settings,task=141,arm='two_demos',variant='two_demos',name='two_demos_'+scope,scope=scope,
        inputs='data/inputs.jsonl',examples='data/examples.jsonl',expected_N=len(needed),target_N=len(target),prior_N=len(target)-len(needed),
        ids=order,first_formal_ID=order[0],example_ids=list(EXAMPLE_IDS),demos_sha256=demos_sha,
        compute_limit_seconds=compute_seconds,save_reserve_seconds=600,total_stage_limit_seconds=compute_seconds+600,
        first_receipts_only=True,no_training=True,no_shutdown=True)
    c.put(B/'data/job.json',job);c.put(work/'job.json',job)
    rels=['tasks/141_two_demos/'+n for n in ('worker141.py','controller141.py','prompt141.py')]
    rels+=['tasks/139_full_repeat/prompt139.py','tasks/139_full_repeat/budget139.py','tasks/136_claim_repeat_transfer/prompt136.py',
           'tasks/104_supervision_evidence/training104.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py']
    for rel in rels:
        dest=B/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
        ast.parse(dest.read_text(encoding='utf-8-sig'))
    shutil.copy2(R/'tasks/141_two_demos/start141.py',work/'start.py')
    with tarfile.open(work/'bundle.tar.gz','w:gz',compresslevel=1) as archive:
        for file in B.rglob('*'):
            if file.is_file():archive.add(file,arcname=file.relative_to(B),recursive=False)
    summary=dict(task=141,status='CPU_PREPARED_NOT_RUN',scope=scope,N=len(needed),demos_sha256=demos_sha,
        max_input_tokens=max(r['input_tokens'] for r in lengths),longest_first_ID=order[0],
        reference_truncated=False,target_users_unchanged=True,exact_tokenized_targets=len(needed),
        all1817_not_retokenized=True,compute_seconds=compute_seconds,save_reserve_seconds=600,
        bundle_sha256=c.sha(work/'bundle.tar.gz'),bundle_bytes=(work/'bundle.tar.gz').stat().st_size,
        new_GPU=False,new_API=0)
    c.put(work/'preparation.json',summary);return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=['screen160','old500','full1817'],default='screen160')
    p.add_argument('--compute-seconds',type=int);a=p.parse_args();print(c.canonical(prepare(a.scope,a.compute_seconds)))
