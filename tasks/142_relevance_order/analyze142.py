"""Analyze verified142 first outputs with the existing140/141 evaluators."""
from collections import Counter
from pathlib import Path
import argparse,math,statistics,sys

R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/140_kl_anchor'))
from analyze140 import c,checked_collect,valid_raw,indexed,common_table,paired_subset,coverage,screening,metrics,LABELS
sys.path.insert(0,str(R/'tasks/141_two_demos'))
from analyze141 import baseline136,historical_predictions
P=R/'.local_models/142_relevance_order';O=R/'outputs/142_relevance_order'
K=R/'.local_models/134_author_baselines';SCOPES=('screen160','old500','full1817')
SOURCE120_SHA='47e129876475499628de7eca934ee9df156dbaef721f8de26abae31853c7a48a'


def frozen_jobs(scope,keys):
    lengths={};jobs={};batches={}
    for part in SCOPES[:SCOPES.index(scope)+1]:
        folder=P/part/'bundle/data';path=folder/'job.json'
        if not path.exists():
            if part==scope:raise FileNotFoundError('No frozen142 job for '+scope)
            continue
        job=c.read(path);g=job.get('generation',{})
        if (job.get('task')!=142 or job.get('arm')!='relevance_order' or job.get('scope')!=part
            or job.get('adapter_sha256')!=SOURCE120_SHA or job.get('max_seq_length')!=16384
            or g.get('batch_size')!=2 or g.get('single_if_prompt_above')!=12701
            or g.get('dtype')!='bfloat16' or g.get('thinking') is not False or g.get('do_sample') is not False
            or g.get('max_new_tokens')!=384 or g.get('num_beams')!=1
            or g.get('repetition_penalty')!=1.0 or job.get('new_training') is not False):
            raise ValueError('Wrong fixed142 source/runtime: '+part)
        inputs=indexed(folder/'inputs.jsonl');new=indexed(folder/'lengths.jsonl')
        order=job['ids'];flat=[i for batch in job['batches'] for i in batch]
        if (len(inputs)!=job['expected_N'] or set(inputs)!=set(new) or set(inputs)!=set(order)
            or len(flat)!=len(set(flat)) or set(flat)!=set(order)):
            raise ValueError('142 inputs/lengths/batches differ')
        for batch in job['batches']:
            if len(batch) not in (1,2):raise ValueError('Unexpected142 batch size')
            for i in batch:batches[i]=len(batch)
        for i,row in new.items():
            if (i not in keys or i in lengths or row.get('prompt_token_sha256')!=inputs[i].get('prompt_token_sha256')
                or row.get('source_prompt_token_sha256')!=inputs[i].get('source_prompt_token_sha256')
                or not row.get('prompt_token_sha256') or not row.get('source_prompt_token_sha256')
                or row['input_tokens']+384>16384):
                raise ValueError('Wrong, duplicate or oversized frozen142 input: '+i)
            lengths[i]=row
        jobs[part]=dict(job_sha256=c.sha(path),expected_N=len(new),max_seq_length=16384,batch_size=2)
    return lengths,jobs,batches


def collect142(paths):
    raw=checked_collect(paths);seen={}
    for folder in paths:
        for path in Path(folder).glob('*.json'):
            row=c.read(path)
            if 'id' not in row:continue
            if row['id'] in seen and seen[row['id']]!=row:raise ValueError('Conflicting142 first receipt: '+row['id'])
            seen[row['id']]=row
    return raw


def inference_cost(raw,target,folders):
    rows=[raw[i] for i in sorted(target&raw.keys())]
    def field(key):
        values=[r[key] for r in rows if r.get(key) is not None]
        return dict(recorded_N=len(values),missing_N=len(rows)-len(values),
            sum=sum(values) if values else None,mean=statistics.mean(values) if values else None,
            median=statistics.median(values) if values else None)
    for row in rows:
        if all(row.get(k) is not None for k in ('seconds','batch_seconds','batch_size')):
            if not math.isclose(row['seconds']*row['batch_size'],row['batch_seconds'],rel_tol=1e-9,abs_tol=1e-8):
                raise ValueError('Expected batch-amortized seconds: '+row['id'])
    walls=[]
    for folder in folders:
        root=Path(folder).parent
        files=list(Path(folder).glob('*.json'))
        phase_ids={c.read(f).get('id') for f in files}-{None}
        if not phase_ids&target:continue
        value=None;kind='not_recorded'
        if phase_ids<=target:
            if (root/'pid.json').exists() and (root/'controller_done.json').exists():
                pid,done=c.read(root/'pid.json'),c.read(root/'controller_done.json')
                if pid.get('started') is not None:
                    value=done['epoch']-pid['started'];kind='controller_process_wall'
            if value is None and (root/'progress.json').exists():
                progress=c.read(root/'progress.json')
                if progress.get('stage')=='complete' and progress.get('elapsed_seconds') is not None:
                    value=progress['elapsed_seconds'];kind='worker_wall'
        walls.append(dict(source=str(root),received_N=len(phase_ids&target),seconds=value,kind=kind,
            whole_phase=phase_ids<=target))
    elapsed=field('seconds')
    return dict(received_N=len(rows),valid_N=sum(valid_raw(r) for r in rows),
        invalid_N=sum(not valid_raw(r) for r in rows),generation_seconds=elapsed,
        complete_generation_total=elapsed['sum'] if elapsed['recorded_N']==len(rows) and rows else None,
        input_tokens=field('input_tokens'),output_tokens=field('output_tokens'),
        batch_size_items=dict(Counter(str(r.get('batch_size','not_recorded')) for r in rows)),
        phase_walls=walls,rule='seconds already divided by actual batch size; never sum batch_seconds per row',
        billing='Process/worker intervals exclude preparation, upload, return and inter-stage wait; no CNY estimate or full-window substitution.')


def analyze(scope,paths=None,bootstrap=False):
    keys=indexed(K/'keys.jsonl');screen=set(c.read(K/'job.json')['phases'][0]['ids'])
    target=screen if scope=='screen160' else {i for i,r in keys.items() if scope=='full1817' or r['old_panel'] in ('natural','pressure')}
    if len(target)!=dict(screen160=160,old500=500,full1817=1817)[scope]:raise ValueError('Frozen134 scope changed')
    lengths,jobs,batches=frozen_jobs(scope,keys)
    if not target<=lengths.keys():raise ValueError('Requested scope lacks complete frozen142 inputs')
    paths=paths or [P/s/'evidence/relevance_order' for s in SCOPES[:SCOPES.index(scope)+1]]
    raw=collect142(paths)
    if set(raw)-target:raise ValueError('142 receipt outside requested scope')
    baseline,provenance=baseline136();unverified=[]
    for i,row in raw.items():
        expected=lengths[i]
        if (row.get('arm')!='relevance_order' or row.get('adapter_sha256')!=SOURCE120_SHA
            or row.get('source_checkpoint')!='120_final369'
            or row.get('prompt_token_sha256')!=expected['prompt_token_sha256']
            or row.get('source_prompt_token_sha256')!=expected['source_prompt_token_sha256']
            or row.get('input_tokens')!=expected['input_tokens'] or row.get('batch_size')!=batches[i]
            or (valid_raw(row) and row.get('finish_reason')!='stop')):
            raise ValueError('142 first receipt source/prompt/runtime mismatch: '+i)
        if i not in baseline:unverified.append(i)
        elif (baseline[i].get('prompt_token_sha256')!=expected['source_prompt_token_sha256']
              or baseline[i].get('input_tokens')!=expected['source_input_tokens']):
            raise ValueError('142 original prompt does not equal136 input: '+i)
    candidate={i:r['parsed']['verdict'] for i,r in raw.items() if valid_raw(r)}
    old={i:baseline[i]['parsed']['verdict'] for i in target&baseline.keys() if valid_raw(baseline[i])}
    valid=sorted(candidate.keys()&old.keys()-set(unverified))
    if not valid:raise ValueError('No verified jointly valid actual142/136 first outputs; no scores written')
    primary=paired_subset(valid,old,candidate,'claim_repeat136',keys,bootstrap);cov=coverage(target,raw)
    history,optional=historical_predictions(keys);history.update(optional)
    sources=dict(relevance_order=candidate,claim_repeat136=old,**history)
    groups=dict(natural=[i for i in valid if keys[i]['old_panel']=='natural'],
        pressure=[i for i in valid if keys[i]['old_panel']=='pressure'],
        new1317=[i for i in valid if keys[i]['subset']=='new'],
        history103_180=[i for i in valid if keys[i]['history103_panel'] in ('natural','pressure')])
    baseline_folders=[R/'.local_models/136_claim_repeat_transfer/evidence'/s/'claim_repeat' for s in SCOPES]
    result=dict(task=142,arm='relevance_order',scope=scope,adapter_sha256=SOURCE120_SHA,
        source_adapter_sha256=SOURCE120_SHA,expected_N=len(target),valid_N=len(candidate),joint_valid_N=len(valid),
        primary=primary,standalone_candidate=metrics([keys[i] for i in sorted(candidate)],candidate),
        coverage=dict(candidate=cov,claim_repeat136=coverage(target,baseline),prompt_unverified_ids=unverified),
        panels={name:paired_subset(ids,old,candidate,'claim_repeat136',keys) for name,ids in groups.items() if ids},
        by_author={a:paired_subset([i for i in valid if keys[i]['author']==a],old,candidate,'claim_repeat136',keys) for a in sorted({keys[i]['author'] for i in valid})},
        by_patient={s:paired_subset([i for i in valid if keys[i]['sid']==s],old,candidate,'claim_repeat136',keys) for s in sorted({keys[i]['sid'] for i in valid})},
        historical_common=common_table(valid,sources,keys),
        historical_comparisons={name:common_table(valid,dict(relevance_order=candidate,claim_repeat136=old,**{name:values}),keys) for name,values in history.items()},
        screening=screening(primary,cov,scope,unverified),source_artifacts=jobs,baseline136_provenance=provenance,
        bootstrap=dict(performed=bootstrap,iterations=1000 if bootstrap else 0,method='existing final_compare120.paired / patient cluster bootstrap'),
        inference_cost=dict(relevance_order=inference_cost(raw,target,paths),claim_repeat136=inference_cost(baseline,target,baseline_folders)),
        input_cost=dict(mean_extra_tokens=statistics.mean(lengths[i]['input_tokens']-lengths[i]['source_input_tokens'] for i in raw),
            total_extra_tokens=sum(lengths[i]['input_tokens']-lengths[i]['source_input_tokens'] for i in raw)),
        new_training=False,new_supervision=False,new_API=0,no_postprocessing=True,no_label_rewrite=True,analysis_only=True)
    unchanged=[i for i in valid if lengths[i]['prompt_token_sha256']==lengths[i]['source_prompt_token_sha256']]
    result['same_input_internal_control']=dict(N=len(unchanged),ids=unchanged,
        changed_label_ids=[i for i in unchanged if candidate[i]!=old[i]],
        note='Included in the frozen evaluation cohort and original batch pairing; not independent evidence of ordering benefit.')
    authors={a:checked_collect([K/'bundle/results'/a,K/'evidence'/a]) for a in ('author_base9b','author_lora9b')}
    author_pred={a:{i:r['parsed']['verdict'] for i,r in data.items() if valid_raw(r)} for a,data in authors.items()}
    result['author_baseline_common']=common_table(valid,dict(relevance_order=candidate,claim_repeat136=old,paper_r1=history['paper_r1'],**author_pred),keys)
    result['author_baseline_coverage']={a:coverage(target,data) for a,data in authors.items()}
    base104_raw=indexed(R/'outputs/105_brief_supervision/predictions_sanitized.jsonl','base_judge')
    original107=indexed(R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    base104={i:r['parsed']['verdict'] for i,r in base104_raw.items() if i in original107 and valid_raw(r) and r.get('prompt_token_sha256')==original107[i].get('prompt_token_sha256')}
    result['same_prompt_unfinetuned_overlap']=common_table(valid,dict(relevance_order=candidate,claim_repeat136=old,base104_9b=base104,
        full_pool120=history['full_pool120'],label_only107=history['label_only107'],paper_r1=history['paper_r1']),keys)
    result['same_prompt_unfinetuned_overlap'].update(raw_coverage=coverage(target,base104_raw),
        prompt_scope='104 baseline SHA matched to107;136 adds claim_repeat,142 additionally reorders complete reference fragments')
    correct=result['standalone_candidate']['correct']
    result['PA_full_target_bounds']=[correct/len(target),(correct+len(target)-len(candidate))/len(target)]
    predictions=[dict(keys[i],relevance_order=candidate[i],claim_repeat136=old.get(i),primary_joint_valid=i in valid) for i in sorted(candidate)]
    receipts=[dict(id=i,GT=keys[i]['GT'],received=i in raw,valid=i in candidate,primary_joint_valid=i in valid,
        verdict=candidate.get(i),finish_reason=raw[i].get('finish_reason') if i in raw else None) for i in sorted(target)]
    return result,predictions,receipts


def main():
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=SCOPES,default='screen160')
    p.add_argument('--results',type=Path,nargs='+');p.add_argument('--out',type=Path,default=O)
    p.add_argument('--bootstrap',action='store_true');a=p.parse_args()
    result,predictions,receipts=analyze(a.scope,a.results,a.bootstrap);prefix='relevance_order_'+a.scope
    c.put(a.out/(prefix+'.json'),result);c.putl(a.out/(prefix+'_predictions_sanitized.jsonl'),predictions)
    c.putl(a.out/(prefix+'_receipt_status_sanitized.jsonl'),receipts)
    v=result['primary'];print(c.canonical(dict(scope=a.scope,N=v['N'],delta_MCC=v['delta_MCC'],delta_correct=v['delta_correct'],delta_false_S=v['delta_false_S'],screening=result['screening'])))


if __name__=='__main__':main()
