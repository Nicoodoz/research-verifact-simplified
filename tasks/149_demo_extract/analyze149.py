"""Fixed160 demo extraction outcomes against cached136, full demos and five baselines."""
from pathlib import Path
import json,sys,time
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,save,collect,valid,score,pair,five_table,markdown_table,cost,LABELS

def main():
    P=R/'.local_models/149_demo_extract/evidence';job=read(P/'data/job.json');ids=set(job['ids'])
    raw=collect([P/'results/demo_extract']);assert len(ids)==160 and set(raw)==ids and all(valid(r) for r in raw.values())
    keys,pred,rawbase=assets();new={i:r['parsed']['verdict'] for i,r in raw.items()}
    full=collect([R/'.local_models/141_two_demos/screen160/evidence/two_demos']);assert ids<=full.keys()
    fullpred={i:r['parsed']['verdict'] for i,r in full.items() if valid(r)}
    table=five_table(ids,keys,pred,rawbase,{'demo_extract':(new,raw)})
    results={}
    for name,lookup in [('claim_repeat136',pred['claim_repeat136']),('two_demos141',fullpred)]:
        a,b=score(ids,lookup,keys),score(ids,new,keys)
        results[name]=dict(baseline=a,candidate=b,delta_MCC=b['mcc']-a['mcc'],delta_correct=b['correct']-a['correct'],delta_FS=b['false_S']-a['false_S'],
            per_class_net={g:sum(keys[i]['GT']==g and new[i]==g for i in ids)-sum(keys[i]['GT']==g and lookup[i]==g for i in ids) for g in LABELS},paired=pair(ids,lookup,new,keys))
    costs={'demo_extract':cost(ids,raw),'two_demos141':cost(ids,full),'claim_repeat136':cost(ids,rawbase['claim_repeat136'])}
    done=read(P/'controller_done.json');phase=done['epoch']-read(P/'pid.json')['started'];costs['demo_extract']['controller_wall_seconds']=phase
    c=results['claim_repeat136'];f=results['two_demos141'];prep=read(P/'preparation.json')
    O=R/'outputs/149_demo_extract';save(O/'analysis.json',dict(N=160,invalid_N=0,missing_N=0,five_baselines=table,comparisons=results,costs=costs,preparation=prep,
        new_API=0,new_training=False,new_generation_N=160,controller_interval_CNY=phase*1.58/3600,full_target_reference_preserved=True))
    with (O/'predictions_sanitized.jsonl').open('w',encoding='utf-8') as file:
        for i in sorted(ids):file.write(json.dumps(dict(id=i,sid=str(keys[i]['sid']),GT=keys[i]['GT'],verdict=new[i],claim_repeat136=pred['claim_repeat136'][i],two_demos141=fullpred[i],valid=True,input_tokens=raw[i]['input_tokens'],output_tokens=raw[i]['output_tokens'],seconds=raw[i]['seconds']),ensure_ascii=False)+'\n')
    lines=['# 149 demo_extract：相同两例的证据摘录','',
        '相同S→NS训练示例、原标签、claim和顺序；每例保留已有审读依据指向的4个完整原始片段，目标claim和完整reference保持。仅示例证据摘录，不是新算法或新医生标注。','']
    for name,v in results.items():lines.append(f"相对{name}：MCC {v['baseline']['mcc']:.4f}→{v['candidate']['mcc']:.4f}（{v['delta_MCC']:+.4f}），正确{v['baseline']['correct']}→{v['candidate']['correct']}（{v['delta_correct']:+d}），false-S {v['baseline']['false_S']}→{v['candidate']['false_S']}（{v['delta_FS']:+d}）；三类净正确{v['per_class_net']}。\n")
    lines+=['## 五基线与候选：共同有效ID','',markdown_table(table),'',
        f"目标160全部有效；五基线共同有效N={table['N']}，与上方完整160直接比较分母不同。paper_r1为作者历史模型；作者两9B为作者提示/768输出；120与136为104体系/384输出。107不列常规主表。",'',
        '## 实测成本','', '|配置|判定次数|输入tokens|输出tokens|生成秒|每条秒|','|---|---:|---:|---:|---:|---:|']
    for name,v in costs.items():lines.append(f"|{name}|{v['attempted_records']}|{v['input_tokens']['total']}|{v['output_tokens']['total']}|{v['seconds']['total']:.2f}|{v['seconds']['mean']:.3f}|")
    lines+=['',f"示例新增tokens由原141的14515降到1578（−89.13%），是相同两例的实际编码结果；完整目标未截断。候选BF16/greedy384、16384上下文、154条batch2与6条batch1；原141为32768/batch1，因此时间差是实际方案成本差，不是严格同运行条件基准。controller {phase:.2f}秒（含加载/编译/生成），租金区间估算¥{phase*1.58/3600:.4f}；准备、等待、上传回传仍在21:12起全窗口账本累计，不能再次相加。本task新增API0，历史成本缺项未补0。",'',
        '患者bootstrap、三类precision/recall/F1、Macro-F1和混淆矩阵见analysis.json。只覆盖原160，不外推500或1817。完整长示例旧结果与全部新首答保留。','']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps({name:{k:v[k] for k in ('delta_MCC','delta_correct','delta_FS','per_class_net')} for name,v in results.items()},ensure_ascii=False))

if __name__=='__main__':main()
