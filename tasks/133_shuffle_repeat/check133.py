"""Check only this new order/package; do not repeat old GPU tests."""
from collections import Counter
from pathlib import Path
import ast,sys

R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'))
import common105 as c
P=R/'.local_models/133_shuffle_repeat'
def main():
    original=c.rows(R/'.local_models/120_full_pool_sft/bundle/data/full_pool_sft120/train.jsonl')
    data=P/'bundle/data/shuffle_repeat'
    new=c.rows(data/'train.jsonl');job=c.read(data/'job.json');plan=c.read(data/'plan.json')
    assert {r['id']:r for r in original}=={r['id']:r for r in new}
    assert len(new)==2945 and len({r['id'] for r in new})==2945
    assert len({r['sid'] for r in new})==32
    assert [r['id'] for r in new]!=[r['id'] for r in original]
    assert [i for row in plan for i in row['ids']]==[r['id'] for r in new]
    assert len(plan)==369 and plan[-1]['loss_divisor']==1 and plan[-1]['consumed']==2945
    screen=c.rows(data/'screen.jsonl');assert len(screen)==160
    assert not {r['id'] for r in screen}&{r['id'] for r in new}
    assert not any({'GT','answer','verdict','sid'}&set(r) for r in screen)
    original_job=c.read(R/'.local_models/120_full_pool_sft/job.json')
    assert job['training']==original_job['training'] and job['evaluation']==original_job['evaluation']
    assert job['seed']==118027 and job['source_adapter_sha256']==original_job['source_adapter_sha256']
    for name in ('prepare133.py','run133.py','check133.py'):
        ast.parse((R/'tasks/133_shuffle_repeat'/name).read_text(encoding='utf-8'))
    result=dict(status='PASS_CPU_ONLY',new_order_N=2945,patients=32,GT=dict(Counter(r['GT'] for r in new)),
        same_IDs_labels_full_inputs=True,only_random_order_changed=True,same_training_settings=True,
        original160_screen_preserved=True,new_GPU_started=False)
    c.put(P/'cpu_check.json',result);print(c.canonical(result))
if __name__=='__main__':main()
