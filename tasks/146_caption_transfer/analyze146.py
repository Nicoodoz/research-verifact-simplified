"""Analyze only the completed fixed400 screen, with five cached baselines."""
from pathlib import Path
import json,sys,time
from datetime import datetime,timezone,timedelta
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common146 import assets,read,rows,save,collect,valid,score,pair,five_table,markdown_table,cost,LABELS

def main():
    P=R/'.local_models/146_caption_transfer/evidence';job=read(P/'data/job.json');ids=set(job['ids'])
    raw=collect([P/'results/order_caption']);done=read(P/'controller_done.json')
    assert len(ids)==400 and set(raw)==ids and done['exit_code']==0 and all(valid(r) for r in raw.values())
    keys,baselines,oldraw=assets();candidate={i:r['parsed']['verdict'] for i,r in raw.items()}
    old142=collect([R/'.local_models/142_relevance_order'/s/'evidence/relevance_order' for s in ('screen160','old500','full1817')])
    pred142={i:r['parsed']['verdict'] for i,r in old142.items() if valid(r)}
    extra={'order_caption':(candidate,raw)};table=five_table(ids,keys,baselines,oldraw,extra)
    comparisons={name:dict(baseline=score(ids,lookup,keys),candidate=score(ids,candidate,keys),paired=pair(ids,lookup,candidate,keys))
                 for name,lookup in [('claim_repeat136',baselines['claim_repeat136']),('relevance_order142',pred142)]}
    for name,value in comparisons.items():
        lookup=baselines['claim_repeat136'] if name=='claim_repeat136' else pred142
        value['delta_correct']=value['candidate']['correct']-value['baseline']['correct']
        value['delta_FS']=value['candidate']['false_S']-value['baseline']['false_S']
        value['delta_MCC']=value['candidate']['mcc']-value['baseline']['mcc']
        value['per_class_net']={g:sum(keys[i]['GT']==g and candidate[i]==g for i in ids)-sum(keys[i]['GT']==g and lookup[i]==g for i in ids) for g in LABELS}
        value['patient_changes']={sid:dict(delta_correct=sum((candidate[i]==keys[i]['GT'])-(lookup[i]==keys[i]['GT']) for i in ids if str(keys[i]['sid'])==sid),
            delta_FS=sum(int(candidate[i]=='Supported' and keys[i]['GT']!='Supported')-int(lookup[i]=='Supported' and keys[i]['GT']!='Supported') for i in ids if str(keys[i]['sid'])==sid)) for sid in sorted({str(keys[i]['sid']) for i in ids})}
    c=comparisons['claim_repeat136'];p=comparisons['relevance_order142']
    phase=done['epoch']-read(P/'pid.json')['started'];session=read(R/'.local_models/night_20261031/session.json');now=time.time()
    budget=dict(as_of=datetime.now(timezone(timedelta(hours=8))).isoformat(),GPU_start=session['start'],GPU_end=session['end'],
        GPU_estimated_CNY=(now-session['start_epoch'])*1.58/3600,API_estimated_CNY=0,API_cap_CNY=80,
        candidate_controller_wall_seconds=phase,candidate_controller_interval_CNY=phase*1.58/3600,
        controller_excludes_preparation_upload_return_and_parallel_CPU=True,no_shutdown=True)
    output=dict(task=146,N=400,valid_N=400,invalid_N=0,missing_N=0,selected_without_GT=True,
                five_baselines=table,comparisons=comparisons,costs={'order_caption':cost(ids,raw),'relevance_order142':cost(ids,old142),'claim_repeat136':cost(ids,oldraw['claim_repeat136'])},budget=budget)
    O=R/'outputs/146_caption_transfer';save(O/'analysis.json',output);save(O/'window_budget.json',budget)
    with (O/'predictions_sanitized.jsonl').open('w',encoding='utf-8') as f:
        for i in sorted(ids):f.write(json.dumps(dict(id=i,sid=str(keys[i]['sid']),GT=keys[i]['GT'],verdict=candidate[i],valid=True,
            claim_repeat136=baselines['claim_repeat136'][i],relevance_order142=pred142[i],input_tokens=raw[i]['input_tokens'],output_tokens=raw[i]['output_tokens'],seconds=raw[i]['seconds']),ensure_ascii=False)+'\n')
    def brief(name,v):
        a,b=v['baseline'],v['candidate']
        return f"相对{name}：MCC {a['mcc']:.4f}→{b['mcc']:.4f}（{v['delta_MCC']:+.4f}），PA {a['percent_agreement']:.2%}→{b['percent_agreement']:.2%}，正确{a['correct']}→{b['correct']}（{v['delta_correct']:+d}），false-S {a['false_S']}→{b['false_S']}（{v['delta_FS']:+d}，non-S={a['non_S']}）。三类净正确{v['per_class_net']}。"
    lines=['# 146 caption_transfer：145在原500之外的固定400验证','',
        '只修正142全局排序说明，所有目标claim和完整证据片段保持；120权重、不训练、greedy384、BF16、16384上下文。按ID哈希固定选样，不按GT或既有对错选样；使用原20名历史暴露患者，不称新holdout。','',brief('claim_repeat136',c),'',brief('relevance_order142',p),'',
        '## 五条固定基线与候选：共同有效ID','',markdown_table(table),'',
        f"固定400条全部有效。作者两臂invalid导致五基线共同N={table['N']}；上方直接对照使用完整400，禁止跨表直接相减。paper_r1为作者历史R1，并非同模型强对照；作者两9B使用作者式提示和768输出，120/136/候选使用104体系384输出。120与136/候选共用训练后的120权重，136重复claim，候选另有142重排和145caption修正。107不列常规主表。",'',
        '## 实测成本','',
        '|配置|判定次数|输入tokens|输出tokens|生成秒|每条秒|', '|---|---:|---:|---:|---:|---:|']
    for name,value in output['costs'].items():
        lines.append(f"|{name}|{value['attempted_records']}|{value['input_tokens']['total']}|{value['output_tokens']['total']}|{value['seconds']['total']:.2f}|{value['seconds']['mean']:.3f}|")
    lines+=['',f"候选controller区间{phase:.2f}秒，按¥1.58/h折算¥{phase*1.58/3600:.4f}，包含加载/编译/生成，未包含准备上传回传；不是方案全程费用。窗口从21:12至{budget['as_of']}连续租金估算¥{budget['GPU_estimated_CNY']:.4f}，包含等待和并行CPU工作，不能与生成/controller费用重复相加。历史各行费用未单独记录；本task新增API0，未为成本重跑基线。",'',
        '患者配对区间、三类precision/recall/F1、混淆矩阵、Macro-F1及患者得失见analysis.json。该筛查不足以宣称完整1817优势；原500的145结果原样保留。','']
    (O/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({name:{k:v[k] for k in ('delta_correct','delta_FS','delta_MCC','per_class_net')} for name,v in comparisons.items()},ensure_ascii=False))

if __name__=='__main__':main()
