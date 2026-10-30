"""One diagnostic on already trained IDs; reuse cached107 predictions.

This is not a new training recipe or a generalization evaluation.
"""
from collections import Counter
from pathlib import Path
import argparse
import json
import sys
import tarfile

R=Path(__file__).resolve().parents[2]
P=R/'.local_models/120_full_pool_sft/training_fit'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'))
import common105 as c
from final_compare120 import metrics,paired
from analyze120 import collect


def prepare():
    train=c.rows(R/'.local_models/120_full_pool_sft/bundle/data/full_pool_sft120/train.jsonl')
    by_id={r['id']:r for r in train}
    lengths={r['id']:r for r in c.rows(R/'.local_models/120_full_pool_sft/bundle/data/full_pool_sft120/lengths.jsonl')}
    cached=[]
    for phase in ('mining_a','mining_s'):
        cached+=c.rows(R/'.local_models/109_boundary_replay/gpu_evidence/results'/phase/'predictions.jsonl')
    if len(cached)!=527 or len({r['id'] for r in cached})!=527:
        raise ValueError('Expected527 unique original107 mining receipts')
    cached={r['id']:r for r in cached if r['id'] in by_id}
    if len(cached)!=415:
        raise ValueError('The frozen120-trained intersection changed')
    source=R/'.local_models/120_full_pool_sft/resume369/evidence/full_pool_sft/train/checkpoint_b'
    done=c.read(source/'checkpoint_complete.json')
    sha='47e129876475499628de7eca934ee9df156dbaef721f8de26abae31853c7a48a'
    bundle=P/'bundle';data=bundle/'data/training_fit120';data.mkdir(parents=True,exist_ok=True)
    inputs=[];metadata=[]
    for i in sorted(cached):
        old=cached[i];row=by_id[i]
        if str(old['sid'])!=str(row['sid']) or old['prompt_token_sha256']!=lengths[i]['prompt_token_sha256']:
            raise ValueError('Original patient/prompt differs')
        if old['checkpoint_adapter_sha256']!='096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8':
            raise ValueError('Not the original107 cached prediction')
        if not old['parsed']['valid']:
            raise ValueError('Report invalid cached107 explicitly before paired analysis')
        inputs.append(dict(id=i,claim=row['claim'],reference=row['reference'],expected_prompt_sha256=old['prompt_token_sha256']))
        metadata.append(dict(id=i,sid=str(row['sid']),GT=row['GT'],baseline107=old['parsed']['verdict'],
            prompt_token_sha256=old['prompt_token_sha256']))
    selection=c.rows(R/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    if {r['sid'] for r in metadata}&{str(r['sid']) for r in selection}:
        raise ValueError('Selection patient entered the training-fit diagnostic')
    window=c.read(R/'.local_models/CURRENT_RESEARCH.json')['window']
    session=dict(start_epoch=window['start_epoch'],duration_seconds=window['deadline_epoch']-window['start_epoch'],
        GPU_cap_CNY=window['GPU_cap_CNY'],hourly_CNY=window['hourly_CNY'],no_shutdown=True)
    c.frozen(data/'session.json',(json.dumps(session,indent=2)+'\n').encode())
    c.frozen(data/'inputs.jsonl',''.join(c.canonical(r)+'\n' for r in inputs).encode())
    c.frozen(P/'metadata.jsonl',''.join(c.canonical(r)+'\n' for r in metadata).encode())
    job=dict(name='training_fit120',task=120,candidate='full_pool120_training_fit',
        model_dir='/root/verifact_image/models/qwen3.5-9b',final_adapter='/root/autodl-tmp/verifact132/adapters/full_pool120',
        adapter_sha256=sha,inputs_path='data/training_fit120/inputs.jsonl',session_path='data/training_fit120/session.json',
        session_sha256=c.sha(data/'session.json'),ids=[r['id'] for r in inputs],N=len(inputs),max_seq_length=16384,seed=117027,
        evaluation=dict(batch_size=2,max_new_tokens=384,do_sample=False,num_beams=1,repetition_penalty=1.,parser='parse105.parse'),
        phase_limit_seconds=1800,save_reserve_seconds=180,no_training=True,no_shutdown=True,first_receipts_only=True)
    c.frozen(data/'job.json',(json.dumps(job,indent=2)+'\n').encode())
    summary=dict(status='CPU_READY_NOT_RUN',N=len(metadata),training_patients=len({r['sid'] for r in metadata}),
        GT=dict(Counter(r['GT'] for r in metadata)),cached107=415,new120=415,new_training=False,
        selection_patients_used=False,claim_reference_prompt_unchanged=True,
        purpose='Does120 still misclassify already trained minority examples? This does not measure generalization.',
        sample_limit='All available527 historical mining receipts intersecting actual120 gradient IDs; mining-enriched, not a random sample.',
        estimated_GPU_minutes=[12,20],no_candidate_selection_from_this_diagnostic=True)
    c.put(P/'prepared.json',summary)
    with tarfile.open(P/'inputs.tar.gz','w:gz',compresslevel=1) as t:
        for f in data.iterdir():t.add(f,arcname=f.relative_to(bundle),recursive=False)
    with tarfile.open(P/'adapter120.tar.gz','w:gz',compresslevel=1) as t:
        for name in ('adapter_model.safetensors','adapter_config.json','checkpoint_complete.json'):
            t.add(source/name,arcname='adapters/full_pool120/'+name,recursive=False)
    print(c.canonical(summary))


def analysis_metadata():
    source={r['id']:r for r in c.rows(R/'.local_models/109_boundary_replay/gpu_bundle/data/pool_metadata.jsonl')}
    original107=set(c.read(R/'.local_models/109_boundary_replay/gpu_bundle/data/source_ids.json'))
    meta=c.rows(P/'metadata.jsonl')
    for row in meta:
        if row['GT']!=source[row['id']]['GT']:
            raise ValueError('Original GT changed')
        row['paper_r1']=source[row['id']]['paper_r1']
        row['also_in_original107_training']=row['id'] in original107
    return meta


def analyze():
    meta=analysis_metadata();old={r['id']:dict(verdict=r['baseline107']) for r in meta}
    receipts=collect([P/'evidence/training_fit120']);new={r['id']:r for r in receipts}
    if len(new)!=len(receipts) or set(new)!={r['id'] for r in meta}:
        raise ValueError('Need all415 unique first receipts')
    for r in meta:
        if new[r['id']]['source_prompt_sha256_104']!=r['prompt_token_sha256']:
            raise ValueError('Actual inference prompt changed')
        if new[r['id']]['source_adapter_sha256']!='47e129876475499628de7eca934ee9df156dbaef721f8de26abae31853c7a48a':
            raise ValueError('Wrong120 checkpoint')
    common=[r for r in meta if new[r['id']]['valid']]
    result=dict(N=415,valid_N=len(common),invalid_N=415-len(common),
        scores=dict(label_only107=metrics(common,{r['id']:r['baseline107'] for r in common}),
                    full_pool120=metrics(common,{r['id']:new[r['id']]['verdict'] for r in common})),
        paired=paired(common,old,new,'label_only107'),diagnostic_only=True,generalization_claim=False,
        new_training=False,source_sample=c.read(P/'prepared.json')['sample_limit'])
    result['by_original107_training']={}
    for flag in (True,False):
        group=[r for r in common if r['also_in_original107_training']==flag]
        result['by_original107_training'][str(flag)]=paired(group,old,new,'label_only107')
    out=R/'outputs/120_full_pool_sft';c.put(out/'training_fit415.json',result)
    c.putl(out/'training_fit415_predictions_sanitized.jsonl',[dict(r,candidate120=new[r['id']]['verdict'],valid=new[r['id']]['valid']) for r in meta])
    lines=['# 120已训练样本的少数类拟合诊断','',result['source_sample'],
        '全部来自120实际梯度训练32人；仅补120预测，107的415条原回执直接复用。样本来自旧困难挖掘，并非随机训练样本或泛化测试。','',
        '|模型|有效N|正确数|MCC|false-S/非S|S/NS/NA召回|','|---|---:|---:|---:|---:|---|']
    for name,m in result['scores'].items():
        recall='/'.join(f"{100*x['recall']:.2f}%" for x in m['per_class'].values())
        lines.append(f"|{name}|{len(common)}|{m['correct']}|{m['mcc']:.4f}|{m['false_S']}/{m['non_S']}|{recall}|")
    lines+=['','该结果只用于区分训练拟合与评价泛化问题，不据此选择新超参数、重标或补训练。无效首次输出保留。','']
    (out/'training_fit415.md').write_bytes('\n'.join(lines).encode())
    print(c.canonical({k:{f:m[f] for f in ('correct','mcc','false_S')} for k,m in result['scores'].items()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','analyze']);a=p.parse_args()
    (prepare if a.action=='prepare' else analyze)()
