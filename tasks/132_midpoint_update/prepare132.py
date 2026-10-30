"""Prepare the unchanged-input one-candidate inference package on CPU."""
from pathlib import Path
import argparse,json,shutil,sys,tarfile
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'.local_models/132_midpoint_update'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(ROOT/'tasks/120_full_pool_sft'));from analyze120 import collect


def main():
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=('screen160','old500','selection1817','internal687'),default='screen160')
    p.add_argument('--runtime-root',type=Path,default=P,help='A fresh private runtime folder preserves earlier frozen sessions')
    a=p.parse_args()
    comp=c.read(P/'adapter_final/composition.json')
    keys=c.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    screen=c.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids']
    target=screen if a.scope=='screen160' else sorted(r['id'] for r in keys if r['old_panel'] in ('natural','pressure'))
    if a.scope=='selection1817':target=sorted(r['id'] for r in keys)
    if a.scope=='internal687':
        internal=c.rows(ROOT/'outputs/120_full_pool_sft/internal687_predictions_sanitized.jsonl')
        target=sorted(r['id'] for r in internal)
        if len(target)!=687:raise ValueError('Expected the complete previously frozen687')
    prior=collect([P/'evidence/midpoint_screen160']) if a.scope=='old500' else []
    if a.scope=='old500':
        if not c.read(ROOT/'outputs/132_midpoint_update/screen160.json')['continue_']:raise ValueError('The fixed screening rule did not pass')
        if len(prior)!=160 or any(r['source_adapter_sha256']!=comp['adapter_sha256'] for r in prior):raise ValueError('Need the unchanged160 first receipts')
    if a.scope=='selection1817':
        if not c.read(ROOT/'outputs/132_midpoint_update/decision500.json')['continue_to1817']:
            raise ValueError('Complete500 did not justify the larger fixed evaluation')
        prior=collect([P/'evidence/midpoint_screen160',P/'evidence/midpoint_old500'])
        if len(prior)!=500 or any(r['source_adapter_sha256']!=comp['adapter_sha256'] for r in prior):
            raise ValueError('Reuse all500 first receipts, including invalid ones')
    complete={r['id'] for r in prior};needed=[i for i in target if i not in complete]
    input_path=ROOT/'.local_models/116_research_cycle/inputs_selection1817.jsonl'
    if a.scope=='internal687':input_path=ROOT/'.local_models/120_full_pool_sft/internal687/bundle/data/internal687/internal120_inputs.jsonl'
    lookup={r['id']:r for r in c.rows(input_path)}
    inputs=[{k:lookup[i][k] for k in ('id','claim','reference','expected_prompt_sha256')} for i in needed]
    window=c.read(ROOT/'.local_models/CURRENT_RESEARCH.json')['window']
    session=dict(start_epoch=window['start_epoch'],duration_seconds=window['deadline_epoch']-window['start_epoch'],
        GPU_cap_CNY=window['GPU_cap_CNY'],hourly_CNY=window['hourly_CNY'],no_shutdown=True)
    runtime=a.runtime_root.resolve()
    if not runtime.is_relative_to((ROOT/'.local_models').resolve()):raise ValueError('Runtime must remain private')
    bundle=runtime/'bundle';rel='data/midpoint/'+a.scope;data=bundle/rel;data.mkdir(parents=True,exist_ok=True)
    c.frozen(data/'session.json',(json.dumps(session,indent=2)+'\n').encode())
    c.frozen(data/'inputs.jsonl',''.join(c.canonical(r)+'\n' for r in inputs).encode())
    job=dict(name='midpoint_'+a.scope,task=132,candidate='midpoint_update',
        model_dir='/root/verifact_image/models/qwen3.5-9b',final_adapter='/root/autodl-tmp/verifact132/adapters/midpoint',
        adapter_sha256=comp['adapter_sha256'],inputs_path=rel+'/inputs.jsonl',session_path=rel+'/session.json',
        session_sha256=c.sha(data/'session.json'),ids=needed,N=len(needed),max_seq_length=16384,seed=117027,
        evaluation=dict(batch_size=2,max_new_tokens=384,do_sample=False,num_beams=1,repetition_penalty=1.,parser='parse105.parse'),
        phase_limit_seconds=1000 if a.scope=='screen160' else (1800 if a.scope=='old500' else (5400 if a.scope=='selection1817' else 2400)),save_reserve_seconds=180,
        no_training=True,no_shutdown=True,first_receipts_only=True)
    c.frozen(data/'job.json',(json.dumps(job,indent=2)+'\n').encode())
    files=['tasks/132_midpoint_update/compose132.py','tasks/132_midpoint_update/controller132.py',
           'tasks/128_sqrt_weight_refresh/extend128.py','tasks/120_full_pool_sft/analyze120.py',
           'tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/data105.py',
           'tasks/105_brief_supervision/parse105.py','tasks/104_supervision_evidence/training104.py']
    for name in files:
        dest=bundle/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    with tarfile.open(runtime/('bundle132_'+a.scope+'.tar.gz'),'w:gz',compresslevel=1) as t:
        for f in bundle.rglob('*'):
            if f.is_file():t.add(f,arcname=f.relative_to(bundle),recursive=False)
    print(c.canonical(dict(scope=a.scope,new_calls=len(needed),first_receipts_reused=len(prior),adapter_sha256=comp['adapter_sha256'])))


if __name__=='__main__':main()
