"""Consolidate the fixed149 first160 and new340; preserve earlier160 artifacts."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,save,collect,valid,score,pair,five_table,markdown_table,cost,LABELS

def main():
    P0=R/'.local_models/149_demo_extract/evidence';P1=R/'.local_models/149_demo_extract_old500/evidence'
    jobs=[read(p/'data/job.json') for p in (P0,P1)];assert len(set(jobs[0]['ids'])&set(jobs[1]['ids']))==0
    ids=set(jobs[0]['ids'])|set(jobs[1]['ids']);assert len(ids)==500
    raw=collect([p/'results/demo_extract' for p in (P0,P1)]);assert set(raw)==ids and all(valid(r) for r in raw.values())
    assert all(read(p/'controller_done.json')['exit_code']==0 for p in (P0,P1))
    keys,pred,rawbase=assets();assert ids=={i for i,k in keys.items() if k['old_panel'] in ('natural','pressure')}
    new={i:r['parsed']['verdict'] for i,r in raw.items()};full=collect([R/'.local_models/141_two_demos'/s/'evidence/two_demos' for s in ('screen160','old500')]);fullpred={i:r['parsed']['verdict'] for i,r in full.items() if valid(r)}
    table=five_table(ids,keys,pred,rawbase,{'demo_extract':(new,raw)});results={}
    for name,lookup in [('claim_repeat136',pred['claim_repeat136']),('two_demos141',fullpred)]:
        a,b=score(ids,lookup,keys),score(ids,new,keys)
        groups={}
        for panel in ('natural','pressure'):
            group={i for i in ids if keys[i]['old_panel']==panel};x,y=score(group,lookup,keys),score(group,new,keys)
            groups[panel]=dict(N=len(group),baseline=x,candidate=y,delta_correct=y['correct']-x['correct'],delta_FS=y['false_S']-x['false_S'],delta_MCC=y['mcc']-x['mcc'])
        results[name]=dict(baseline=a,candidate=b,delta_MCC=b['mcc']-a['mcc'],delta_correct=b['correct']-a['correct'],delta_FS=b['false_S']-a['false_S'],
            per_class_net={g:sum(keys[i]['GT']==g and new[i]==g for i in ids)-sum(keys[i]['GT']==g and lookup[i]==g for i in ids) for g in LABELS},paired=pair(ids,lookup,new,keys),groups=groups)
    costs={'demo_extract':cost(ids,raw),'two_demos141':cost(ids,full),'claim_repeat136':cost(ids,rawbase['claim_repeat136'])}
    walls=[read(p/'controller_done.json')['epoch']-read(p/'pid.json')['started'] for p in (P0,P1)]
    output=dict(N=500,valid_N=500,invalid_N=0,missing_N=0,reused160=160,new340=340,five_baselines=table,comparisons=results,costs=costs,controller_seconds=walls,controller_interval_CNY=sum(walls)*1.58/3600,new_API=0)
    O=R/'outputs/149_demo_extract';save(O/'old500_analysis.json',output);save(O/'analysis.json',output)
    with (O/'old500_predictions_sanitized.jsonl').open('w',encoding='utf-8') as file:
        for i in sorted(ids):file.write(json.dumps(dict(id=i,sid=str(keys[i]['sid']),GT=keys[i]['GT'],verdict=new[i],claim_repeat136=pred['claim_repeat136'][i],two_demos141=fullpred[i],valid=True,input_tokens=raw[i]['input_tokens'],output_tokens=raw[i]['output_tokens'],seconds=raw[i]['seconds']),ensure_ascii=False)+'\n')
    lines=['# 149 demo_extract：原500完整结果','',
        '复用原160，只新增340；500/500均为首答且有效。原S→NS两个训练示例的身份、claim、标签、顺序不变，只保留已有审读指向的完整片段；目标reference始终全文保留，无训练或GT改写。','']
    for name,v in results.items():
        lines.append(f"相对{name}：MCC {v['baseline']['mcc']:.4f}→{v['candidate']['mcc']:.4f}（{v['delta_MCC']:+.4f}），PA {v['baseline']['percent_agreement']:.2%}→{v['candidate']['percent_agreement']:.2%}，正确{v['baseline']['correct']}→{v['candidate']['correct']}（{v['delta_correct']:+d}），FS {v['baseline']['false_S']}→{v['candidate']['false_S']}（{v['delta_FS']:+d}/179）；三类净正确{v['per_class_net']}。\n")
        for panel,g in v['groups'].items():lines.append(f"{panel}（N={g['N']}）：正确{g['delta_correct']:+d}、FS{g['delta_FS']:+d}、MCC{g['delta_MCC']:+.4f}。")
    lines+=['','## 五基线与候选：共同有效ID','',markdown_table(table),'',
        f"完整500直接比较与五基线共同N={table['N']}分开；作者invalid不填0。paper_r1为历史R1；作者9B用作者式prompt/768输出，120/136为104体系/384输出。107不列常规主表。",'',
        '## 同ID实测推理成本','', '|配置|判定次数|输入tokens|输出tokens|生成秒|每条秒|','|---|---:|---:|---:|---:|---:|']
    for name,v in costs.items():lines.append(f"|{name}|{v['attempted_records']}|{v['input_tokens']['total']}|{v['output_tokens']['total']}|{v['seconds']['total']:.2f}|{v['seconds']['mean']:.3f}|")
    lines+=['',f"示例新增1578 tokens/条，对141原14515减少89.13%。本候选BF16/greedy384、16384上下文、batch2/1；两阶段controller墙钟{walls[0]:.2f}+{walls[1]:.2f}秒，区间折算¥{sum(walls)*1.58/3600:.4f}。准备、排队、回传与发布继续包含在全窗口租金；不能叠加生成与controller费用。原141为32768/batch1，时间差为实际方案成本差，不是严格吞吐基准。新增API0，旧基线费用缺项不补0。",'',
        '[原160报告保留](screen160_report.md) · [原160完整统计](screen160_analysis.json) · [最新窗口成本](../146_caption_transfer/window_budget_latest.md)','',
        '患者配对bootstrap、三类precision/recall/F1、Macro-F1、混淆矩阵及自然/压力表现保留在old500_analysis.json。没有完整1817结果，不外推。']
    text='\n'.join(lines).rstrip()+'\n';(O/'old500_report.md').write_text(text,encoding='utf-8');(O/'report.md').write_text(text,encoding='utf-8')
    print(json.dumps({n:{k:v[k] for k in ('delta_MCC','delta_correct','delta_FS','per_class_net')} for n,v in results.items()},ensure_ascii=False))

if __name__=='__main__':main()
