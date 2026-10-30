"""Read first midpoint receipts and apply the pre-written continuation rule."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'.local_models/132_midpoint_update'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(ROOT/'tasks/120_full_pool_sft'))
from analyze120 import collect
from final_compare120 import paired,metrics,LABELS


def main():
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=('screen160','old500','internal687'),default='screen160');a=p.parse_args()
    keys={r['id']:r for r in c.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
    target=c.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')['screen_ids'] if a.scope=='screen160' else sorted(i for i,r in keys.items() if r['old_panel'] in ('natural','pressure'))
    paths=[P/'evidence/midpoint_screen160']
    if a.scope=='old500':paths.append(P/'evidence/midpoint_old500')
    internal=[]
    if a.scope=='internal687':
        internal=c.rows(ROOT/'outputs/120_full_pool_sft/internal687_predictions_sanitized.jsonl')
        keys={r['id']:r for r in internal};target=sorted(keys);paths=[P/'evidence/midpoint_internal687']
    values=collect(paths);new={r['id']:r for r in values}
    if len(new)!=len(values) or set(new)!=set(target):raise ValueError('Require all distinct first receipts')
    sha=c.read(P/'adapter_final/composition.json')['adapter_sha256']
    if any(r['source_adapter_sha256']!=sha for r in values):raise ValueError('Wrong midpoint adapter')
    b107={r['id']:r for r in c.rows(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    b120={r['id']:r for r in c.rows(ROOT/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')}
    prompt_hashes={i:r['source_prompt_sha256_104'] for i,r in b120.items()}
    if a.scope=='internal687':
        b107={r['id']:dict(verdict=r['baseline107']) for r in internal}
        b120={r['id']:dict(verdict=r['candidate120']) for r in internal}
        prompt_hashes={r['id']:r['expected_prompt_sha256'] for r in c.rows(ROOT/'.local_models/120_full_pool_sft/internal687/bundle/data/internal687/internal120_inputs.jsonl')}
    for i,r in new.items():
        if r['source_prompt_sha256_104']!=prompt_hashes[i]:raise ValueError('Prompt changed')
    joint=[keys[i] for i in target if new[i]['valid']]
    groups={'all':joint}
    native103={};base105={}
    if a.scope=='old500':
        groups.update({panel:[r for r in joint if r['old_panel']==panel] for panel in ('natural','pressure')})
        native103={r['id']:r for r in c.rows(ROOT/'outputs/103_lora_selection/final_paired_predictions.jsonl')}
        base105={r['id']:r for r in c.rows(ROOT/'outputs/105_brief_supervision/predictions_sanitized.jsonl') if r['arm']=='base_judge'}
        for panel in ('natural','pressure'):
            groups['same103_'+panel]=[r for r in joint if r['old_panel']==panel and r['id'] in native103 and native103[r['id']]['arms']['nine_native']['valid']]
            groups['same105base_'+panel]=[r for r in joint if r['old_panel']==panel and r['id'] in base105 and base105[r['id']]['parsed']['valid']]
    result=dict(scope=a.scope,expected_N=len(target),received_N=len(values),joint_valid_N=len(joint),invalid_N=len(values)-len(joint),
        fixed_alpha=.5,source107_sha256=c.read(P/'adapter_final/composition.json')['source107_sha256'],
        source120_sha256=c.read(P/'adapter_final/composition.json')['source120_sha256'],new_training=False,
        new_API=0,panels={})
    for name,rows in groups.items():
        scores={
            'paper_r1':metrics(rows,{r['id']:r['paper_r1'] for r in rows}),
            'label_only107':metrics(rows,{r['id']:b107[r['id']]['verdict'] for r in rows}),
            'full_pool120':metrics(rows,{r['id']:b120[r['id']]['verdict'] for r in rows}),
            'midpoint132':metrics(rows,{r['id']:new[r['id']]['verdict'] for r in rows})}
        if name.startswith('same103_'):
            scores['base9b_author_prompt_cached103']=metrics(rows,{r['id']:native103[r['id']]['predictions']['nine_native'] for r in rows})
        if name.startswith('same105base_'):
            if any(base105[r['id']]['prompt_token_sha256']!=b107[r['id']]['prompt_token_sha256'] for r in rows):raise ValueError('Cached unfine-tuned prompt differs')
            scores['base9b_same104_prompt_cached105']=metrics(rows,{r['id']:base105[r['id']]['parsed']['verdict'] for r in rows})
        result['panels'][name]=dict(scores=scores,vs107=paired(rows,b107,new,'label_only107'),vs120=paired(rows,b120,new,'full_pool120'))
    result['by_author']={author:dict(vs107=paired([r for r in joint if r['author']==author],b107,new,'label_only107'),
        vs120=paired([r for r in joint if r['author']==author],b120,new,'full_pool120')) for author in sorted({r['author'] for r in joint})}
    if a.scope=='screen160':
        s=result['panels']['all']['scores'];old=s['label_only107'];full=s['full_pool120'];cand=s['midpoint132']
        sc=lambda v:v['per_class']['Supported']['recall']*sum(r['GT']=='Supported' for r in joint)
        gain107=(cand['mcc']>=old['mcc']+.01 or cand['correct']>=old['correct']+2 or cand['false_S']<=old['false_S']-1)
        risk=(cand['false_S']<=full['false_S']-2 and cand['mcc']>=old['mcc'] and cand['correct']>=old['correct']-1 and sc(cand)>=sc(old)-1 and gain107)
        quality=(cand['mcc']>=full['mcc']+.015 and cand['false_S']<=full['false_S'])
        result.update(continue_=bool(len(joint)>=152 and (risk or quality)),risk_branch=bool(risk),quality_branch=bool(quality))
    out=ROOT/'outputs/132_midpoint_update';out.mkdir(parents=True,exist_ok=True)
    c.put(out/(a.scope+'.json'),result)
    c.putl(out/(a.scope+'_predictions_sanitized.jsonl'),[dict(keys[i],midpoint132=new[i]['verdict'],midpoint_valid=new[i]['valid'],baseline107=b107[i]['verdict'],baseline120=b120[i]['verdict']) for i in target])
    lines=['# 132：107与120有效更新的固定中点','',
        '只做一次alpha=0.5，无新增训练；原107、120与作者历史预测均复用。自然与压力分开，mixed筛查集合不冒充自然分布。','',
        '|范围／模型|有效N|MCC|PA|正确数|false-S/真实非S|S/NS/NA召回|',
        '|---|---:|---:|---:|---:|---:|---|']
    for panel,d in result['panels'].items():
        n=len(groups[panel])
        for label,m in d['scores'].items():
            recalls='/'.join(f"{m['per_class'][g]['recall']*100:.2f}%" if any(r['GT']==g for r in groups[panel]) else '—' for g in LABELS)
            lines.append(f"|{panel}/{label}|{n}|{m['mcc']:.4f}|{m['percent_agreement']*100:.2f}%|{m['correct']}|{m['false_S']}/{m['non_S']}|{recalls}|")
    lines+=['',f"覆盖：{len(joint)}/{len(target)}，无效{result['invalid_N']}，未补旧答案。",
        '配对类别救回／误伤、患者方向与来源见JSON。参数插值不等于低学习率重训，也没有证明医学推理机制。',
        '107使用104的标签prompt；作者式未微调9B只在103已有覆盖上列出，其thinking与输出预算不同。105缓存的未微调9B与当前104标签prompt一致，但缺失／无效仍保留，未新运行105。paper_r1始终是不同模型的作者历史参照。','']
    if a.scope=='screen160':lines.insert(-1,'冻结继续条件：'+('达到，允许补到500。' if result['continue_'] else '未达到，停止当前中点。'))
    (out/(a.scope+'.md')).write_text('\n'.join(lines),encoding='utf-8')
    print(c.canonical(dict(scope=a.scope,continue_=result.get('continue_'),scores={k:{x:v[x] for x in ('mcc','correct','false_S','non_S')} for k,v in result['panels']['all']['scores'].items()})))


if __name__=='__main__':main()
