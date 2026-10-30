"""Prepare one fixed training-order replication of120, no GPU/network activity."""
from pathlib import Path
import json,random,shutil,sys,tarfile

R=Path(__file__).resolve().parents[2]
P=R/'.local_models/133_shuffle_repeat'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'))
import common105 as c
from data105 import training_plan


def main():
    original=R/'.local_models/120_full_pool_sft/bundle/data/full_pool_sft120'
    rows=c.rows(original/'train.jsonl');lookup={r['id']:r for r in rows}
    if not len(rows)==len(lookup)==2945:raise ValueError('Expected2945 unique original training IDs')
    order=sorted(lookup);random.Random(118027).shuffle(order)
    new=[lookup[i] for i in order]
    if order==[r['id'] for r in rows]:raise ValueError('The independent order did not change')
    b=P/'bundle';data=b/'data/shuffle_repeat';data.mkdir(parents=True,exist_ok=True)
    c.frozen(data/'train.jsonl',''.join(c.canonical(r)+'\n' for r in new).encode())
    for name in ('lengths.jsonl','screen.jsonl','screen_lengths.jsonl'):
        c.frozen(data/name,(original/name).read_bytes())
    plan=training_plan(order,1,8)
    if len(plan)!=369 or plan[-1]['loss_divisor']!=1:raise ValueError('Training budget changed')
    c.frozen(data/'plan.json',(json.dumps(plan,ensure_ascii=False,indent=2)+'\n').encode())
    window=c.read(R/'.local_models/CURRENT_RESEARCH.json')['window']
    session=dict(start_epoch=window['start_epoch'],duration_seconds=window['deadline_epoch']-window['start_epoch'],
        GPU_cap_CNY=window['GPU_cap_CNY'],hourly_CNY=window['hourly_CNY'],no_shutdown=True)
    c.frozen(data/'session.json',(json.dumps(session,indent=2)+'\n').encode())
    job=c.read(R/'.local_models/120_full_pool_sft/job.json')
    job.update(name='shuffle_repeat',task=133,candidate='shuffle_repeat',seed=118027,
        source107_adapter='/root/autodl-tmp/verifact133/source107/checkpoint_a',
        train_path='data/shuffle_repeat/train.jsonl',lengths_path='data/shuffle_repeat/lengths.jsonl',
        plan_path='data/shuffle_repeat/plan.json',screen_inputs_path='data/shuffle_repeat/screen.jsonl',
        screen_lengths_path='data/shuffle_repeat/screen_lengths.jsonl',session_path='data/shuffle_repeat/session.json',
        decision_required=True,replication='Same107 initialization and2945 IDs; one fixed new order; no seed selection',
        implementation_lineage='Unmodified worker120; its fingerprint task120 denotes the inherited implementation, not an old result')
    c.frozen(data/'job.json',(json.dumps(job,ensure_ascii=False,indent=2)+'\n').encode())
    files=['tasks/133_shuffle_repeat/run133.py','tasks/133_shuffle_repeat/check133.py','tasks/120_full_pool_sft/run120.py',
        'tasks/120_full_pool_sft/worker120.py','tasks/105_brief_supervision/common105.py',
        'tasks/105_brief_supervision/data105.py','tasks/105_brief_supervision/loss105.py',
        'tasks/105_brief_supervision/parse105.py','tasks/104_supervision_evidence/training104.py',
        'tasks/107_support_aux/checkpoint107.py']
    for name in files:
        dest=b/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,dest)
    with tarfile.open(P/'bundle133.tar.gz','w:gz',compresslevel=1) as t:
        for f in b.rglob('*'):
            if f.is_file():t.add(f,arcname=f.relative_to(b),recursive=False)
    c.put(P/'prepared.json',dict(status='CPU_READY_CONDITIONAL_NO_GPU',N=2945,steps=369,seed=118027,
        old_seed=117027,same_source107=True,same_original_labels_and_inputs=True,
        only_training_random_order_changes=True,no_new_loss_or_modules=True,
        original_outputs_preserved=True,run_only_after_pending132_and_training_fit_review=True))
    print('One fixed shuffle replication prepared; no GPU launched')


if __name__=='__main__':main()
