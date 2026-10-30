"""Summarize existing optimization logs without inventing per-class losses."""
from collections import Counter
from pathlib import Path
import json
import statistics
import sys

R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'))
import common105 as c


def main():
    raw=c.rows(R/'.local_models/120_full_pool_sft/resume369/evidence/full_pool_sft/steps.jsonl')
    unique={}
    for row in raw:
        if row['step'] in unique and unique[row['step']]!=row:
            raise ValueError('Conflicting records for the same actual step')
        unique[row['step']]=row
    steps=[unique[i] for i in range(1,370)]
    source=c.rows(R/'.local_models/120_full_pool_sft/bundle/data/full_pool_sft120/train.jsonl')
    by_id={r['id']:r for r in source};ids=[i for s in steps for i in s['ids']]
    if len(ids)!=2945 or len(set(ids))!=2945 or set(ids)!=set(by_id):
        raise ValueError('Actual training consumption differs from the frozen one-pass list')
    groups={}
    for name,part in [('steps1_92',steps[:92]),('steps93_184',steps[92:184]),
                      ('steps185_276',steps[184:276]),('steps277_369',steps[276:])]:
        members=[by_id[i] for s in part for i in s['ids']]
        groups[name]=dict(steps=len(part),examples=len(members),GT=dict(Counter(r['GT'] for r in members)),
            patients=len({r['sid'] for r in members}),mean_logged_batch_loss=statistics.mean(s['loss'] for s in part),
            median_logged_batch_loss=statistics.median(s['loss'] for s in part),
            mean_gradient_norm=statistics.mean(s['gradient_norm'] for s in part),
            mean_tokens_per_example=sum(s['tokens'] for s in part)/len(members),
            seconds_per_example=sum(s['seconds'] for s in part)/len(members))
    total_seconds=sum(s['seconds'] for s in steps)
    result=dict(steps=369,examples=2945,patients=len({r['sid'] for r in source}),
        GT=dict(Counter(r['GT'] for r in source)),no_omitted_or_repeated_training_ID=True,
        last_tail_divisor=steps[-1]['loss_divisor'],logged_training_step_seconds=total_seconds,
        logged_training_hours=total_seconds/3600,phases=groups,
        per_class_loss_available=False,
        interpretation='The old log stores one average loss per batch. Minority-specific loss and class probabilities cannot be recovered from it. Actual415 training-set predictions are queued to distinguish fitting from generalization.',
        new_training=False,new_GPU_calls=0)
    out=R/'outputs/120_full_pool_sft';c.put(out/'training_dynamics.json',result)
    lines=['# 120：现有训练日志能确认什么','',
        '原369步实际消费2945个唯一ID，三类均完整出现；最后一条尾批除数为1。这里分析的是已保存日志，不新增训练。','',
        '|步骤段|实际例数|S/NS/NA|平均batch loss|每例平均tokens|每例训练秒数|',
        '|---|---:|---|---:|---:|---:|']
    for name,g in groups.items():
        counts='/'.join(str(g['GT'].get(k,0)) for k in ('Supported','Not Supported','Not Addressed'))
        lines.append(f"|{name}|{g['examples']}|{counts}|{g['mean_logged_batch_loss']:.4f}|{g['mean_tokens_per_example']:.0f}|{g['seconds_per_example']:.2f}|")
    lines+=['',f'已记录的训练step用时合计{total_seconds/3600:.2f}小时，不含窗口等待、加载、检查、部分保存或评价，不能当作账单时长。',
        '日志只有混合batch的平均loss，不能从中反推NS或NA的真实独立loss。loss下降也不证明分类有效；已另排415条实际训练样本预测，复用107回执来补足这个判断。','']
    (out/'training_dynamics.md').write_bytes('\n'.join(lines).encode())
    print(c.canonical(result))


if __name__=='__main__':main()
