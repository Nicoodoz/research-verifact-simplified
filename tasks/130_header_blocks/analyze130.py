"""Compare the fixed presentation candidate with both retained native models."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'.local_models/130_header_blocks'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as c
sys.path.insert(0,str(ROOT/'tasks/120_full_pool_sft'))
from analyze120 import collect
from final_compare120 import lookup,metrics,paired,LABELS


def screen_signal(rows,old,new,complete):
    v=paired(rows,old,new,'120_full_pool_sft')
    changes=v['changes']['by_class']
    guards=dict(complete_first_receipts=complete,coverage=len(rows)>=157,
        S=changes['Supported']['rescued']-changes['Supported']['harmed']>=-4,
        NS=changes['Not Supported']['rescued']-changes['Not Supported']['harmed']>=-3,
        NA=changes['Not Addressed']['rescued']-changes['Not Addressed']['harmed']>=-3)
    for panel in ('natural','pressure'):
        group=[r for r in rows if r['old_panel']==panel]
        guards[panel]=bool(group) and paired(group,old,new,'120_full_pool_sft')['delta_correct']>=-2
    quality=v['delta_correct']>=2 and v['delta_MCC']>=.01 and v['delta_false_S']<=1
    risk=v['delta_false_S']<=-2 and v['delta_correct']>=-2 and v['delta_MCC']>=-.01
    return dict(guards=guards,quality_signal=quality,risk_signal=risk,
        continue_=all(guards.values()) and (quality or risk),composite=v)


def main():
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=['screen160','old500'],default='screen160')
    a=p.parse_args()
    keys=lookup(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')
    base107=lookup(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    base120=lookup(ROOT/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')
    selected=c.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids']
    target=set(selected) if a.scope=='screen160' else {i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')}
    folders=[P/'evidence/header_blocks_screen160']
    if a.scope=='old500':folders.append(P/'evidence/header_blocks_old500')
    raw=collect(folders);pred={r['id']:r for r in raw}
    if len(pred)!=len(raw) or not set(pred)<=target:raise ValueError('Duplicate or out-of-scope first receipt')
    maps={r['id']:r for path in P.glob('*_source_map.jsonl') for r in c.rows(path)}
    for i,r in pred.items():
        if r['source_adapter_sha256']!=base120[i]['source_adapter_sha256']:
            raise ValueError('Changed native checkpoint')
        if r['source_prompt_sha256_104']!=maps[i]['changed_prompt_sha256']:
            raise ValueError('Unexpected grouped-reference input')
        if maps[i]['original_prompt_sha256']!=base107[i]['prompt_token_sha256']:
            raise ValueError('Original full-reference comparator input mismatch')
    valid=[keys[i] for i in sorted(target) if pred.get(i,{}).get('valid') and base107[i]['valid'] and base120[i]['valid']]
    result=dict(task=130,candidate='header_blocks',scope=a.scope,expected_N=len(target),
        received_N=len(raw),valid_N=len(valid),invalid_N=sum(not r['valid'] for r in raw),
        missing_N=len(target-set(pred)),training=False,API=0,confirmation40_used=False,panels={})
    old103=lookup(ROOT/'outputs/103_lora_selection/final_paired_predictions.jsonl')
    groups={panel:[r for r in valid if r['old_panel']==panel] for panel in ('natural','pressure')}
    for panel in ('natural','pressure'):
        groups['same103_'+panel]=[r for r in valid if r['old_panel']==panel
            and r['id'] in old103 and old103[r['id']]['arms']['nine_native']['valid']]
    for panel,group in groups.items():
        if not group:continue
        models={'paper_r1':{r['id']:r['paper_r1'] for r in group},
            '107_label_only':{r['id']:base107[r['id']]['verdict'] for r in group},
            '120_full_pool_sft':{r['id']:base120[r['id']]['verdict'] for r in group},
            'header_blocks':{r['id']:pred[r['id']]['verdict'] for r in group}}
        if panel.startswith('same103_'):
            models['103_original_prompt_unfinetuned9B']={r['id']:old103[r['id']]['predictions']['nine_native'] for r in group}
        result['panels'][panel]=dict(N=len(group),scores={name:metrics(group,p) for name,p in models.items()},
            versus107=paired(group,base107,pred,'107_label_only'),
            versus120=paired(group,base120,pred,'120_full_pool_sft'),
            by_author={author:paired([r for r in group if r['author']==author],base120,pred,'120_full_pool_sft')
                for author in sorted({r['author'] for r in group})})
    result['baseline_limits']=dict(paper_r1='Author historical model/configuration, not same-Judge causal control.',
        original_prompt_unfinetuned9B='Actual common subset only; different original prompt and thinking budget.',
        label_only107='Maintained ordinary fine-tuning baseline; original104 prompt and full reference.',
        full_pool_sft120='Matched checkpoint; only reference presentation changes for the candidate.')
    if a.scope=='screen160':result['screen']=screen_signal(valid,base120,pred,set(pred)==target)
    out=ROOT/'outputs/130_header_blocks'
    c.put(out/(a.scope+'.json'),result)
    c.putl(out/(a.scope+'_predictions_sanitized.jsonl'),[
        dict(id=i,sid=keys[i]['sid'],GT=keys[i]['GT'],author=keys[i]['author'],old_panel=keys[i]['old_panel'],
            verdict=pred.get(i,{}).get('verdict'),valid=pred.get(i,{}).get('valid',False),missing=i not in pred,
            baseline107=base107[i]['verdict'],baseline120=base120[i]['verdict']) for i in sorted(target)])
    lines=['# 130 header_blocks：'+a.scope+'实际结果','',
        '仅改变完整reference呈现。原正文和顺序保留；107、120与作者历史结果复用。原作者式未微调9B只列其已有共同子集。','',
        '|范围／模型|共同有效N|MCC|PA|正确数|false-S/真实非S|S/NS/NA召回|',
        '|---|---:|---:|---:|---:|---:|---|']
    for panel,data in result['panels'].items():
        for name,m in data['scores'].items():
            recalls='/'.join('—' if m['per_class'][g]['recall'] is None else f"{m['per_class'][g]['recall']:.1%}" for g in LABELS)
            lines.append(f"|{panel}/{name}|{data['N']}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|{m['correct']}|{m['false_S']}/{m['non_S']}|{recalls}|")
    lines+=['','|范围／相对120|ΔMCC|Δ正确|Δfalse-S|S救回/误伤|NS救回/误伤|NA救回/误伤|','|---|---:|---:|---:|---:|---:|---:|']
    for panel,data in result['panels'].items():
        v=data['versus120'];change=v['changes']['by_class']
        by_class='|'.join(f"{change[g]['rescued']}/{change[g]['harmed']}" for g in LABELS)
        lines.append(f"|{panel}|{v['delta_MCC']:+.4f}|{v['delta_correct']:+d}|{v['delta_false_S']:+d}|{by_class}|")
    lines+=['','缺失/无效单列于JSON，不补旧答案；来源、患者方向与混淆矩阵一并保存。不是独立未接触测试。','']
    (out/(a.scope+'.md')).write_bytes('\n'.join(lines).encode())
    print(c.canonical(dict(scope=a.scope,received=len(raw),valid=len(valid),screen=result.get('screen'),
        panels={p:{k:d['versus120'][k] for k in ('delta_MCC','delta_correct','delta_false_S')} for p,d in result['panels'].items()})))


if __name__=='__main__':main()
