"""CPU comparison of actual fixed369 predictions; preserve the220 results."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/120_full_pool_sft'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0,str(ROOT/'tasks/116_research_cycle'))
from analyze_scores116 import metrics,section
sys.path.insert(0,str(ROOT/'tasks/107_support_aux'))
from evaluate107 import risk_deltas
sys.path.insert(0,str(ROOT/'src'))
from verifact_research.evaluation import paired_compare

LABELS=('Supported','Not Supported','Not Addressed')


def lookup(path):
    rows=common.rows(path); result={r['id']:r for r in rows}
    if len(rows)!=len(result):raise ValueError('Duplicate prediction ID: '+str(path))
    return result


def paired(rows,old,new,reference,bootstrap=False):
    value=section(rows,old,new)
    value['reference']=reference
    value['scores'][reference]=value['scores'].pop('label_only107')
    if bootstrap:
        truth=[dict(proposition_id=r['id'],subject_id=str(r['sid']),human_gt=r['GT']) for r in rows]
        a=[dict(proposition_id=r['id'],verdict=old[r['id']]['verdict']) for r in rows]
        b=[dict(proposition_id=r['id'],verdict=new[r['id']]['verdict']) for r in rows]
        value['patient_bootstrap']=paired_compare(truth,a,b,iterations=1000)
        annotated=[dict(r,pred={'reference':old[r['id']]['verdict'],'final369':new[r['id']]['verdict']}) for r in rows]
        value['risk_and_recall_bootstrap']=risk_deltas(annotated,'reference','final369')
    return value


def evaluate(predictions,done_path,tag,bootstrap):
    done=common.read(done_path)
    if (done.get('steps'),done.get('consumed'))!=(369,2945):
        raise ValueError('Only actual completed369/2945 state is eligible')
    keys=lookup(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    base=lookup(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    midpoint=lookup(OUT/'midpoint220_1817_predictions_sanitized.jsonl')
    final=lookup(predictions)
    if not final or not set(final)<=set(keys):raise ValueError('Unknown or empty final IDs')
    for i,r in final.items():
        if r['GT']!=keys[i]['GT'] or str(r['sid'])!=str(keys[i]['sid']):
            raise ValueError('Original GT/patient changed')
        if r.get('receipt_status')!='missing':
            if r.get('source_adapter_sha256')!=done['adapter_sha256']:
                raise ValueError('Not the fixed369 adapter')
            if r.get('source_prompt_sha256_104')!=base[i]['prompt_token_sha256']:
                raise ValueError('Not the original107/120 prompt')
    valid={i:r for i,r in final.items() if r.get('valid') is True}
    groups={p:[keys[i] for i in final if keys[i].get('old_panel')==p] for p in ('natural','pressure')}
    if len(final)==1817 and set(final)==set(keys):
        groups.update(selection1817=list(keys.values()),new1317=[r for r in keys.values() if r.get('subset')=='new'])
    original103=lookup(ROOT/'outputs/103_lora_selection/final_paired_predictions.jsonl')
    for p in ('natural','pressure'):
        groups['same103_'+p]=[keys[i] for i in final if i in original103 and original103[i]['panel']==p
            and original103[i]['arms']['nine_native']['valid']]
    result=dict(task=120,step=369,consumed=2945,source_adapter_sha256=done['adapter_sha256'],
        coverage=dict(expected=len(final),valid=len(valid),invalid=sum(r.get('receipt_status')=='invalid' for r in final.values()),
            missing=sum(r.get('receipt_status')=='missing' for r in final.values())),
        panels={},new_training=False,new_inference=False,old220_preserved=True,
        cohort_role='historically exposed development/selection patients',confirmation40_used=False)
    for name,requested in groups.items():
        rows=[r for r in requested if r['id'] in valid]
        if not rows:continue
        models={'paper_r1':{r['id']:r['paper_r1'] for r in rows},
            '107_label_only':{r['id']:base[r['id']]['verdict'] for r in rows},
            '120_step220':{r['id']:midpoint[r['id']]['verdict'] for r in rows},
            '120_step369':{r['id']:valid[r['id']]['verdict'] for r in rows}}
        if name.startswith('same103_'):
            models['103_original_prompt_unfinetuned9B']={r['id']:original103[r['id']]['predictions']['nine_native'] for r in rows}
        panel=dict(expected_N=len(requested),joint_valid_N=len(rows),
            scores={label:metrics(rows,pred) for label,pred in models.items()},
            versus107=paired(rows,base,valid,'107_label_only',bootstrap and name=='selection1817'),
            versus220=paired(rows,midpoint,valid,'120_step220',bootstrap and name=='selection1817'))
        panel['by_author']={a:paired([r for r in rows if r['author']==a],base,valid,'107_label_only')
            for a in sorted({r['author'] for r in rows})}
        result['panels'][name]=panel
    result['baseline_limits']={
        'paper_r1':'Historical author predictions, different Judge/configuration; not a same-model control.',
        '103_original_prompt_unfinetuned9B':'Only existing180 coverage; different prompt/thinking budget. Never imputed into the full cohort.',
        '107_label_only':'Maintained fine-tuned9B baseline, same104 prompt and complete reference.',
        '120_step220':'Preserved earlier checkpoint of the same training run; not a separate seed.'}
    return result


def render(result,tag):
    lines=['# 120 fixed369：'+tag+'同ID比较','',
        '本表只读取已返回的最终369步预测；复用107、220步、paper_r1和已有103原生结果，不新增推理或训练。',
        '原20名患者均为历史暴露的开发/选型队列。103未微调基线只在其真实覆盖的共同子集列出，提示词和计算预算差异保留。','',
        '|范围／模型|有效／范围|MCC|PA|正确数|false-S/真实非S|S/NS/NA召回|',
        '|---|---:|---:|---:|---:|---:|---|']
    for name,panel in result['panels'].items():
        for label,m in panel['scores'].items():
            recalls='/'.join('—' if m['per_class'][g]['recall'] is None else f"{100*m['per_class'][g]['recall']:.2f}%" for g in LABELS)
            lines.append(f"|{name}/{label}|{panel['joint_valid_N']}/{panel['expected_N']}|{m['mcc']:.4f}|{100*m['percent_agreement']:.2f}%|{m['correct']}|{m['false_S']}/{m['non_S']}|{recalls}|")
    lines+=['','|范围／参照|ΔMCC|Δ正确|Δfalse-S|S救回/误伤|NS救回/误伤|NA救回/误伤|false-S新增/避免|',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,panel in result['panels'].items():
        for compare in ('versus107','versus220'):
            p=panel[compare];c=p['changes']
            classes='|'.join(f"{c['by_class'][g]['rescued']}/{c['by_class'][g]['harmed']}" for g in LABELS)
            lines.append(f"|{name}/{p['reference']}|{p['delta_MCC']:+.4f}|{p['delta_correct']:+d}|{p['delta_false_S']:+d}|{classes}|{c['false_S_new']}/{c['false_S_avoided']}|")
    lines+=['','无效与缺失不补旧答案；患者、来源及混淆矩阵见同名JSON。标签指标不能证明理由正确或医学推理机制。',
        '表格是实际结果，不预设最终369优于220；是否继续由质量、错误放行及类别损失综合判断。','']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser();p.add_argument('--predictions',type=Path,required=True)
    p.add_argument('--training-done',type=Path,required=True);p.add_argument('--tag',required=True)
    p.add_argument('--bootstrap',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Simple artifact tag required')
    result=evaluate(a.predictions,a.training_done,a.tag,a.bootstrap)
    common.put(OUT/(a.tag+'_comparison.json'),result)
    (OUT/(a.tag+'_comparison.md')).write_bytes(render(result,a.tag).encode('utf-8'))
    print(json.dumps({name:{v:panel[v]['delta_MCC'] for v in ('versus107','versus220')}
        for name,panel in result['panels'].items()}))


if __name__=='__main__':main()
