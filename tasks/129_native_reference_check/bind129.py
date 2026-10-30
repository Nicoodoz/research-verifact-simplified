"""Choose a retained native checkpoint before129 outputs; prepare two jobs."""
from pathlib import Path
import argparse
import json
import re
import shutil
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as common


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate-name',required=True)
    p.add_argument('--training-done',type=Path,required=True)
    p.add_argument('--predictions',type=Path,required=True)
    p.add_argument('--selection-reason',required=True)
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    if not re.fullmatch('[a-zA-Z0-9_]+',a.candidate_name):raise ValueError('Simple candidate name required')
    private=ROOT/'.local_models/129_native_reference_check';bundle=private/'bundle'
    done=common.read(a.training_done)
    if (done.get('steps'),done.get('consumed'))!=(369,2945) or done['fingerprint'].get('task') not in (120,128):
        raise ValueError('A completed120 or128 native checkpoint is required')
    inputs=common.rows(private/'inputs160.jsonl');keys=common.rows(private/'analysis_keys.jsonl')
    predictions={r['id']:r for r in common.rows(a.predictions)}
    baseline={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    if len(inputs)!=160 or any(predictions.get(r['id'],{}).get('source_adapter_sha256')!=done['adapter_sha256'] for r in inputs):
        raise ValueError('Selected native model does not cover the exact160 with original first receipts')
    if any(r['full_prompt_sha256']!=baseline[r['id']]['prompt_token_sha256'] for r in keys):
        raise ValueError('Full-reference pairing does not match the original107 prompt')
    if a.dry_run:
        print(common.canonical(dict(status='CPU_CHECK_ONLY',N=160,candidate_selected=False,GPU_started=False)))
        return
    if any(list((private/'evidence').glob('*/batches/*.json'))):
        raise RuntimeError('Diagnostic predictions already exist; do not reselect a model')
    choice=dict(candidate_name=a.candidate_name,task=done['fingerprint']['task'],
        adapter_sha256=done['adapter_sha256'],selection_reason=a.selection_reason,
        source_predictions=str(a.predictions.resolve()),source_training_done=str(a.training_done.resolve()),
        selection_before_diagnostic=True)
    common.frozen(private/'choice.json',(json.dumps(choice,ensure_ascii=False,indent=2)+'\n').encode())
    state=common.read(ROOT/'.local_models/CURRENT_RESEARCH.json')['window']
    session=dict(start_epoch=state['start_epoch'],duration_seconds=state['deadline_epoch']-state['start_epoch'],
        GPU_cap_CNY=state['GPU_cap_CNY'],hourly_CNY=state['hourly_CNY'],no_shutdown=True)
    data=bundle/'data/native_reference_check129';data.mkdir(parents=True,exist_ok=True)
    common.frozen(data/'session.json',(json.dumps(session,indent=2)+'\n').encode())
    common.frozen(data/'inputs.jsonl',(private/'inputs160.jsonl').read_bytes())
    arms={
        'reference_blank107':('/root/autodl-tmp/verifact109/bundle/source107/checkpoint_a',
           '096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8'),
        'reference_blank_native':(done['final_checkpoint'],done['adapter_sha256'])}
    for name,(checkpoint,sha) in arms.items():
        job=dict(name=name,task=129,candidate='reference_blank',model_dir='/root/verifact_image/models/qwen3.5-9b',
            final_adapter=checkpoint,adapter_sha256=sha,inputs_path='data/native_reference_check129/inputs.jsonl',
            session_path='data/native_reference_check129/session.json',session_sha256=common.sha(data/'session.json'),
            ids=[r['id'] for r in inputs],N=160,max_seq_length=16384,seed=117027,
            evaluation=dict(batch_size=2,max_new_tokens=384,do_sample=False,num_beams=1,repetition_penalty=1.,parser='parse105.parse'),
            phase_limit_seconds=900,save_reserve_seconds=60,no_training=True,no_shutdown=True,first_receipts_only=True)
        common.frozen(data/(name+'.json'),(json.dumps(job,indent=2)+'\n').encode())
    files=['tasks/129_native_reference_check/run129.py','tasks/128_sqrt_weight_refresh/extend128.py',
        'tasks/120_full_pool_sft/analyze120.py','tasks/105_brief_supervision/common105.py','tasks/105_brief_supervision/parse105.py',
        'tasks/105_brief_supervision/data105.py','tasks/104_supervision_evidence/training104.py']
    for relative in files:
        dest=bundle/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,dest)
    with tarfile.open(private/'bundle129.tar.gz','w:gz',compresslevel=1) as archive:
        for file in bundle.rglob('*'):
            if file.is_file():archive.add(file,arcname=file.relative_to(bundle),recursive=False)
    print(common.canonical(dict(jobs=list(arms),candidate=a.candidate_name,N_each=160,model_download=False,GPU_started=False)))


if __name__=='__main__':main()
