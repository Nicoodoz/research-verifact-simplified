"""Pinned tokenizer/Jinja only. No model weights, GPU or network operations."""
from __future__ import annotations
import argparse
from collections import Counter
import statistics
import sys
from pathlib import Path
import common106 as c

sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'))
from tokenizer_cpu105 import CPUPinnedTokenizer
from data105 import encode, shared, offsets

def stats(values):
    v=sorted(values)
    return dict(N=len(v),sum=sum(v),mean=statistics.mean(v),min=min(v),median=statistics.median(v),p95=v[int(.95*(len(v)-1))],max=max(v))

def select_diagnostics(rows, per_class=4):
    """Training IDs only; round-robin across patient, hash fixed before GPU."""
    selected=[]
    for label in c.LABELS:
        by_patient={}
        for row in rows:
            if row['GT']==label:by_patient.setdefault(str(row['sid']),[]).append(row)
        patients=sorted(by_patient,key=lambda p:c.digest('106/diagnostic/patient/'+label+'/'+p))
        for p in patients:by_patient[p].sort(key=lambda r:c.digest('106/diagnostic/id/'+r['id']))
        chosen=[]
        while len(chosen)<per_class:
            moved=False
            for p in patients:
                if by_patient[p] and len(chosen)<per_class:chosen.append(by_patient[p].pop(0));moved=True
            if not moved:break
        if len(chosen)!=per_class:raise ValueError('Insufficient training diagnostic coverage')
        selected.extend(chosen)
    return selected

def label_audit(tok):
    answers={}
    for label in c.LABELS:
        answer=c.canonical({'verdict':label})
        ids,spans=offsets(tok,answer)
        # Synthetic labels only, no clinical text enters this report.
        value_start=answer.index(':')+2;value_end=len(answer)-2
        group=[i for i,(s,e) in enumerate(spans) if s<value_end and value_start<e]
        answers[label]=dict(answer=answer,ids=ids,decoded_tokens=[tok.decode([i],skip_special_tokens=False) for i in ids],
                            offsets=[list(s) for s in spans],verdict_indices=group,verdict_ids=[ids[i] for i in group],
                            eos_id=tok.convert_tokens_to_ids('<|im_end|>'))
    ns=answers['Not Supported']['verdict_ids'];na=answers['Not Addressed']['verdict_ids']
    common=[]
    for a,b in zip(ns,na):
        if a!=b:break
        common.append(a)
    return dict(labels=answers,NS_NA_shared_value_prefix_ids=common,
                sequence_probability_requires='all conditional answer tokens plus EOS, normalized over three complete legal paths',
                no_substring_Supported_penalty=True,control_loss='105_verdict_mean_CE_plus_other_answer_mean_CE',
                candidate_loss='verdict_sum_CE_div_fixed_global360over196_plus_other_answer_mean_CE')

def prepare(data_dir, output, model_dir, eval_inputs):
    data_dir=Path(data_dir);output=Path(output);model_dir=Path(model_dir)
    sources=[data_dir/(arm+'.jsonl') for arm in ('label_mean','label_sum')]+[Path(eval_inputs)]
    source_hashes={str(path.resolve()):c.sha(path) for path in sources}
    meta=c.read(c.ROOT/'outputs/103_lora_selection/model_metadata.json')['qwen3.5-9b']
    if meta['revision']!=c.REVISION:raise ValueError('Wrong tokenizer revision')
    names=('config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja')
    for name in names:
        if c.sha(model_dir/name)!=meta['files'][name]['sha256']:raise ValueError('Tokenizer SHA mismatch: '+name)
    tok=CPUPinnedTokenizer(model_dir);lengths=[];diag={};diag_members=[]
    for arm in ('label_mean','label_sum'):
        rows=c.rows(data_dir/(arm+'.jsonl'))
        if len(rows)!=196 or Counter(r['GT'] for r in rows)!=Counter({'Supported':83,'Not Supported':62,'Not Addressed':51}):raise ValueError('Frozen 196 class quotas differ')
        if len({r['id'] for r in rows})!=196:raise ValueError('Duplicate training ID')
        for row in rows:
            if set(shared.parse_answer(row))!={'verdict'}:raise ValueError('Only physician label answers allowed')
            e=encode(tok,row)
            lengths.append(dict(arm=arm,id=row['id'],sid=row['sid'],GT=row['GT'],input_tokens=e['prompt_tokens'],answer_tokens=e['answer_tokens'],
                                total_tokens=len(e['input_ids']),verdict_tokens=e['groups'].count(1),other_tokens=e['groups'].count(2),
                                verdict_answer_token_indices=e['verdict_answer_token_indices'],prompt_token_sha256=e['prompt_token_sha256'],answer_sha256=e['answer_sha256']))
        actual_value_total=sum(r['verdict_tokens'] for r in lengths if r['arm']==arm)
        if actual_value_total!=360:raise ValueError('Global196-label token mean changed; never normalize by current batch/class')
        chosen=select_diagnostics(rows)
        for row in chosen:
            diag[row['id']]={k:row[k] for k in ('id','sid','claim','reference','reference_id','reference_sha256')}
            diag[row['id']]['panel']='train_diagnostic'
            diag_members.append(dict(arm=arm,id=row['id'],sid=row['sid'],GT=row['GT']))
    evaluation=[];erows=c.rows(eval_inputs)
    for row in erows:
        ids=shared.prompt_ids(tok,row)
        evaluation.append(dict(id=row['id'],sid=row['sid'],panel=row['panel'],input_tokens=len(ids),prompt_token_sha256=c.digest(c.canonical(ids))))
    if len(erows)!=500:raise ValueError('Must retain original development500')
    for diagrow in diag.values():
        ids=shared.prompt_ids(tok,diagrow)
        evaluation.append(dict(id=diagrow['id'],sid=diagrow['sid'],panel='train_diagnostic',input_tokens=len(ids),prompt_token_sha256=c.digest(c.canonical(ids))))
    if any(c.sha(path)!=source_hashes[str(path.resolve())] for path in sources):raise RuntimeError('Source changed during tokenization; do not publish stale token maps')
    output.mkdir(parents=True,exist_ok=True)
    c.putl(output/'train_token_lengths.jsonl',lengths)
    c.putl(output/'eval_token_lengths.jsonl',[r for r in evaluation if r['panel']!='train_diagnostic'])
    c.putl(output/'diagnostic_token_lengths.jsonl',[r for r in evaluation if r['panel']=='train_diagnostic'])
    c.putl(data_dir/'diagnostic_inputs.jsonl',[diag[k] for k in sorted(diag)])
    c.putl(output/'diagnostic_manifest.jsonl',diag_members)
    for name,predicate in [('eval',lambda r:r['panel']!='train_diagnostic'),('diagnostic',lambda r:r['panel']=='train_diagnostic')]:
        order=sorted(filter(predicate,evaluation),key=lambda r:(r['input_tokens'],r['id']))
        batches=[dict(batch=i//8,ids=[r['id'] for r in order[i:i+8]],max_input_tokens=max(r['input_tokens'] for r in order[i:i+8])) for i in range(0,len(order),8)]
        c.put(output/(name+'_batches.json'),dict(batch_size=8,ordering='input_token_length_then_ID',batches=batches))
    minimum_context=max(max(r['total_tokens'] for r in lengths),max(r['input_tokens'] for r in evaluation)+384)
    original_context=c.read(c.ROOT/'outputs/105_brief_supervision/token_summary.json')['required_context_tokens']
    if minimum_context>original_context:raise ValueError('Diagnosis does not fit original105 context; do not silently change the one-loss contrast')
    result=dict(model='Qwen/Qwen3.5-9B',revision=c.REVISION,tokenizer_only=True,weights_loaded=False,truncation=False,
                tokenizer_files={name:c.sha(model_dir/name) for name in names},
                input_file_SHA256=source_hashes,
                training={arm:{key:stats([r[key] for r in lengths if r['arm']==arm]) for key in ('input_tokens','answer_tokens','total_tokens')} for arm in ('label_mean','label_sum')},
                required_context_tokens=original_context,minimum_required_context_tokens=minimum_context,
                diagnostic_union_N=len(diag),diagnostic_each_arm_N=12,development_N=500)
    result['fixed_value_token_mean_normalizer']=360/196
    result['actual_value_tokens_per_arm']=360
    c.put(output/'tokenizer_summary.json',result);c.put(output/'tokenizer_labels.json',label_audit(tok))
    print(c.canonical(result))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',type=Path,default=c.PRIVATE)
    p.add_argument('--output',type=Path,default=c.OUT);p.add_argument('--model-dir',type=Path,default=c.ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    p.add_argument('--eval-inputs',type=Path,default=c.ROOT/'.local_models/105_brief_supervision/eval_inputs.jsonl')
    a=p.parse_args();prepare(a.data_dir,a.output,a.model_dir,a.eval_inputs)

if __name__=='__main__':main()
