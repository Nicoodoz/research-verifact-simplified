"""Promote already checked private preparation without retokenizing or rehashing it."""
from pathlib import Path
import argparse, shutil, sys
R=Path(__file__).resolve().parents[2];P=R/'.local_models/139_full_repeat';O=R/'outputs/139_full_repeat'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);a=p.parse_args()
    dest=P/'source'
    if dest.exists():raise FileExistsError('139 source snapshot already exists')
    source=a.source
    summary=c.read(source/'summary.json');check=c.read(source/'selfcheck.json')
    assert summary['N']==1817 and summary['screen_N']==160 and check['status']=='PASS'
    assert summary['maximum_with_384_output']==27145 and summary['GPU_used'] is False
    dest.mkdir(parents=True)
    for name in ['all1817_inputs.jsonl','all1817_lengths.jsonl','summary.json','selfcheck.json']:
        shutil.copy2(source/name,dest/name)
    B=R/'.local_models/134_author_baselines'
    shutil.copy2(B/'keys.jsonl',dest/'keys.jsonl')
    original=c.read(B/'job.json');c.put(dest/'screen160_ids.json',original['phases'][0]['ids'])
    old=c.read(source/'screen160_bundle/data/job.json')
    settings=dict(model_dir=old['model_dir'],adapter=old['adapter'],adapter_bytes=old['adapter_bytes'],
        adapter_sha256='47e129876475499628de7eca934ee9df156dbaef721f8de26abae31853c7a48a',max_seq_length=32768,
        generation=dict(dtype='bfloat16',thinking=False,max_new_tokens=384,total_answer_token_budget=384,
                        do_sample=False,num_beams=1,repetition_penalty=1.,batch_size=1))
    c.put(dest/'settings.json',settings)
    session=c.read(source/'screen160_bundle/data/session.json');session['save_reserve_seconds']=900
    c.put(dest/'session.json',session)
    public=dict(summary,task=139,status='CPU_PREPARED_NOT_RUN',compute_limit_seconds=2700,
        save_reserve_seconds=900,total_stage_limit_seconds=3600,stage_max_CNY=1.58,
        reuse_without_retokenization=True,source_adapter_sha256=settings['adapter_sha256'])
    public['forecast']['hard_screen_phase_seconds']=3600
    public['forecast']['hard_screen_phase_CNY']=1.58
    public['forecast']['interpretation']='Original2x-4x runtime forecast retained; actual compute cap2700 plus900 save, global budget prevails.'
    c.put(O/'cpu_preparation.json',public)
    print(c.canonical(dict(task=139,status='INITIALIZED',retokenized=False,rehash_original_inputs=False)))


if __name__=='__main__':main()
