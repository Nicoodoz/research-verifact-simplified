"""Evaluate cumulative frozen demonstration stages without rerunning receipts."""
from pathlib import Path
import json,sys,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,save,collect,valid,score,pair,five_table,markdown_table,cost,LABELS

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=['screen160','old500','full1817'],default='screen160');a=ap.parse_args()
    scopes=['screen160']+(['old500'] if a.scope!='screen160' else [])+(['full1817'] if a.scope=='full1817' else [])
    paths=[R/'.local_models'/('152_demo_na'+('' if s=='screen160' else '_'+s))/'evidence' for s in scopes]
    ids=set();walls=[]
    for p in paths:
        job=read(p/'data/job.json');assert not ids & set(job['ids']);ids.update(job['ids'])
        assert read(p/'controller_done.json')['exit_code']==0
        walls.append(read(p/'controller_done.json')['epoch']-read(p/'pid.json')['started'])
    assert len(ids)=={'screen160':160,'old500':500,'full1817':1817}[a.scope]
    raw=collect([p/'results/demo_na' for p in paths]);assert set(raw)==ids and all(valid(r) for r in raw.values())
    keys,pred,rawbase=assets();new={i:r['parsed']['verdict'] for i,r in raw.items()}
    comparisons={};lookups={'claim_repeat136':pred['claim_repeat136']}
    if a.scope!='full1817':
        r149=collect([R/'.local_models'/name/'evidence/results/demo_extract' for name in ('149_demo_extract','149_demo_extract_old500')]);lookups['demo_extract149']={i:r['parsed']['verdict'] for i,r in r149.items() if valid(r)}
        r141=collect([R/'.local_models/141_two_demos'/s/'evidence/two_demos' for s in ('screen160','old500')]);lookups['two_demos141']={i:r['parsed']['verdict'] for i,r in r141.items() if valid(r)}
    for name,lookup in lookups.items():
        assert ids<=set(lookup);b,c=score(ids,lookup,keys),score(ids,new,keys);groups={}
        for panel,subset in [('natural',{i for i in ids if keys[i]['old_panel']=='natural'}),('pressure',{i for i in ids if keys[i]['old_panel']=='pressure'}),('new1317',{i for i in ids if keys[i]['subset']=='new'})]:
            if not subset:continue
            x,y=score(subset,lookup,keys),score(subset,new,keys)
            groups[panel]=dict(N=len(subset),baseline=x,candidate=y,delta_correct=y['correct']-x['correct'],delta_FS=y['false_S']-x['false_S'],delta_MCC=y['mcc']-x['mcc'])
        comparisons[name]=dict(baseline=b,candidate=c,delta_correct=c['correct']-b['correct'],delta_FS=c['false_S']-b['false_S'],delta_MCC=c['mcc']-b['mcc'],per_class_net={g:sum(keys[i]['GT']==g and new[i]==g for i in ids)-sum(keys[i]['GT']==g and lookup[i]==g for i in ids) for g in LABELS},paired=pair(ids,lookup,new,keys),groups=groups)
    five=five_table(ids,keys,pred,rawbase,{'demo_na':(new,raw)})
    costs=dict(demo_na=cost(ids,raw),claim_repeat136=cost(ids,rawbase['claim_repeat136']))
    if a.scope!='full1817':costs.update(demo_extract149=cost(ids,r149),two_demos141=cost(ids,r141))
    out=dict(task=152,scope=a.scope,N=len(ids),valid_N=len(raw),invalid_N=0,missing_N=0,reused_prior_stages=True,comparisons=comparisons,five_baselines=five,costs=costs,controller_seconds=walls,controller_interval_CNY=sum(walls)*1.58/3600,new_API=0)
    O=R/'outputs/152_demo_na';save(O/(a.scope+'_analysis.json'),out);save(O/'analysis.json',out)
    with (O/(a.scope+'_predictions_sanitized.jsonl')).open('w',encoding='utf-8') as f:
        for i in sorted(ids):f.write(json.dumps(dict(id=i,sid=str(keys[i]['sid']),GT=keys[i]['GT'],verdict=new[i],claim_repeat136=pred['claim_repeat136'][i],valid=True,input_tokens=raw[i]['input_tokens'],output_tokens=raw[i]['output_tokens'],seconds=raw[i]['seconds']))+'\n')
    lines=[f'# 152 demo_na：{a.scope}，N={len(ids)}','',
        '固定149的精简S＋NS两例，只追加1个真实训练患者的NA例；示例新增2187 tokens/条，目标病例reference全文保留。三例均来自原120训练32名患者，不用评价GT、内部验证8人或确认40人选例；label-only greedy384。旧阶段首答直接复用，无内容重试。','']
    for name,v in comparisons.items():
        b,c=v['baseline'],v['candidate'];lines.append(f"相对{name}：MCC {b['mcc']:.4f}→{c['mcc']:.4f}（{v['delta_MCC']:+.4f}），PA {b['percent_agreement']:.2%}→{c['percent_agreement']:.2%}，正确{b['correct']}→{c['correct']}（{v['delta_correct']:+d}），false-S {b['false_S']}→{c['false_S']}（{v['delta_FS']:+d}）；三类净正确{v['per_class_net']}。")
        for panel,g in v['groups'].items():lines.append(f"{panel} N={g['N']}：正确{g['delta_correct']:+d}、false-S{g['delta_FS']:+d}、MCC{g['delta_MCC']:+.4f}。")
    lines+=['','## 五基线与候选：共同有效ID','',markdown_table(five),'',
        f"五基线共同有效N={five['N']}，与上面完整候选范围的直接比较分开。缓存复用；作者两臂为作者接口/768输出，120/136为104体系/384输出，paper_r1为作者历史R1。监督、证据与生成设置有差异，107不作常规主表。",'',
        '## 同ID推理成本','', '|配置|判定次数|输入tokens|输出tokens|生成秒|每条秒|','|---|---:|---:|---:|---:|---:|']
    for name,v in costs.items():lines.append(f"|{name}|{v['attempted_records']}|{v['input_tokens']['total']}|{v['output_tokens']['total']}|{v['seconds']['total']:.2f}|{v['seconds']['mean']:.3f}|")
    lines+=['',f"候选RTX4080 SUPER、BF16、16384上下文、batch2/1；controller阶段秒数{walls}，区间¥{sum(walls)*1.58/3600:.4f}，API新增0。准备、排队、回传和发布还计入整个GPU窗口。生成时间与controller不重复累加，旧基线费用缺项不补0；141为32768/batch1，成本比较为实际系统差异。",'',
        '1000次患者cluster配对bootstrap、三类precision/recall/F1、Macro-F1、混淆矩阵及自然/压力/新增面板见analysis.json。20名评价患者已有历史开发暴露；不宣称新holdout，不自动升级默认系统。']
    text='\n'.join(lines).rstrip()+'\n';(O/(a.scope+'_report.md')).write_text(text,encoding='utf-8');(O/'report.md').write_text(text,encoding='utf-8')
    print(json.dumps({n:{k:v[k] for k in ('delta_MCC','delta_correct','delta_FS','per_class_net')} for n,v in comparisons.items()},ensure_ascii=False))

if __name__=='__main__':main()
