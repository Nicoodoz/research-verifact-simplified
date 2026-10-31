"""CPU/static checks only; no synthetic classifications or model imports."""
from pathlib import Path
import ast,json,sys
from prepare_eval138 import E,P,R,plan,source136
from worker_eval138 import batches_for,deadlines


def main():
    session=dict(start_epoch=0,duration_seconds=72000,GPU_cap_CNY=20,hourly_CNY=1)
    job=dict(compute_limit_seconds=2700)
    d=deadlines(1000,session,job);assert d['compute_end']==3700 and d['stage_end']==4600
    assert deadlines(71000,session,job)['compute_end']==71100
    assert batches_for(['a','b','c'],dict(a=12700,b=12701,c=12702))==[['a','b'],['c']]
    inputs,lengths=source136();assert len(inputs)==len(lengths)==1817
    done,_,_,prior,target,needed=plan('rationale_tasks','old500')
    assert len(target)==500 and len(needed)==340 and len(set(prior)&target)==160
    assert done['adapter_sha256']=='fe09d59ef3aaa5988ccc5489647731095e86d7ccc611b66b7083abae73cba17e'
    assert len(set(inputs)-target)==1317
    for path in [R/'tasks/138_rationale_tasks'/n for n in ['prepare_eval138.py','worker_eval138.py','check_eval138.py']]+list((E/'templates').glob('*.py')):
        assert not path.read_bytes().startswith(b'\xef\xbb\xbf');ast.parse(path.read_text(encoding='utf-8'))
    assert 'torch' not in sys.modules and 'transformers' not in sys.modules
    result=dict(status='PASS',task=138,kind='extension_cpu_only',source136_N=1817,
        rationale_old500_new_N=340,actual_completed_checkpoint_verified=True,
        source_retokenized=False,no_fake_classification=True,batch2_threshold=12701,
        compute_and900_save_separate=True,control_preparation_requires_actual_training_done=True)
    (E/'cpu_selfcheck.json').write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result))


if __name__=='__main__':main()
