"""Final descriptive tables, fusion checks and costs; no fitting or calls."""
from collections import Counter
import numpy as np
import common092 as c
from analyze092 import table,paired
def metric_table(tt):
    lines=['|配置|MCC|PA|正确/N|错误支持/non-S|AC1|Macro-F1|S假发现率|','|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,v in tt.items():lines.append(f"|{name}|{v['MCC']:.4f}|{v['PA']:.2%}|{v['correct']}/{v['N']}|{v['false_S']}/{v['true_non_S']}|{v['AC1']:.4f}|{v['Macro_F1']:.4f}|{v['false_discovery_S']:.2%}|")
    return '\n'.join(lines)
def main():
    rows=c.lines(c.OUT/'oof_predictions.jsonl');fusion=c.lines(c.OUT/'fusion_predictions.jsonl');met=c.read(c.OUT/'metrics.json');sub=c.read(c.OUT/'subgroups.json');pairs=c.read(c.OUT/'paired.json')
    models=['Original','B','F4','frozen','finetuned','bias_only','text_fusion']
    fm=table(fusion,models);extra=dict(metrics=fm,paired_vs_F4=paired(fusion,'F4','text_fusion'),core_valid=table([r for r in fusion if r['fusion_baseline_valid']],models),by_author={a:table([r for r in fusion if r['author']==a],models) for a in ['human','llm']},by_fold={str(f):table([r for r in fusion if r['fold']==f],models) for f in range(5)})
    counts=Counter((r['GT'],r['predictions']['B'],r['predictions']['bias_only'],r['predictions']['text_fusion']) for r in fusion)
    extra['transitions']=[dict(GT=k[0],B=k[1],bias_only=k[2],text_fusion=k[3],N=v) for k,v in sorted(counts.items())]
    extra['both_B_and_F4_wrong_text_correct']=sum(r['predictions']['B']!=r['GT'] and r['predictions']['F4']!=r['GT'] and r['predictions']['finetuned']==r['GT'] for r in fusion)
    c.put(c.OUT/'fusion_supplement.json',extra)
    paragraphs=['# 类别、患者和融合补表','所有confusion matrix行是真实S/NS/NA，列为预测S/NS/NA。概率指标是分类softmax的诊断，不表示经过临床校准。','']
    for scope,tt in list(met.items())+[('conditional_fusion_common',fm)]:
        paragraphs+=['## '+scope,'',metric_table(tt),'','|配置|类别|Precision|Recall|F1|','|---|---|---:|---:|---:|']
        for name,z in tt.items():
            for j,lab in enumerate(['S','NS','NA']):paragraphs.append(f"|{name}|{lab}|{z['precision'][j]:.2%}|{z['recall'][j]:.2%}|{z['F1'][j]:.4f}|")
        paragraphs+=['','混淆矩阵：','']
        for name,z in tt.items():paragraphs.append(name+': '+str(z['confusion_matrix']))
        paragraphs+=['']
    for author,tt in sub['author'].items():paragraphs+=['## author='+author,'',metric_table(tt),'']
    for f,tt in sub['fold'].items():paragraphs+=['## outer fold='+f,'',metric_table(tt),'']
    for name in ['090_natural','090_pressure']:
        paragraphs+=['## '+name+'（原同期B/F4，各面板独立）','',metric_table(sub[name]),'']
    paragraphs+=['## 全量概率诊断','','|配置|NLL|Brier（三类平方误差和）|ECE（15等宽箱）|','|---|---:|---:|---:|']
    for name in ['frozen','finetuned']:
        v=met['full_OOF'][name];paragraphs.append(f"|{name}|{v['NLL']:.4f}|{v['Brier']:.4f}|{v['ECE_15']:.4f}|")
    (c.OUT/'detailed_tables.md').write_text('\n'.join(paragraphs)+'\n',encoding='utf-8')
    pp=pairs['finetuned_vs_frozen']['patient_net'];vals=np.array(list(pp.values()));patient=dict(patient_net_quantiles=np.quantile(vals,[0,.25,.5,.75,1]).tolist(),largest_five_positive=sorted(pp.items(),key=lambda x:-x[1])[:5],largest_five_negative=sorted(pp.items(),key=lambda x:x[1])[:5],all_leave_one_patient_net_positive=bool((vals.sum()-vals>0).all()),note='Descriptive fixed-prediction distribution, not retrained leave-one-patient validation.')
    c.put(c.OUT/'patient_summary.json',patient)
    costs=c.read(c.OUT/'costs.json');train=costs['training'];bench=c.read(c.OUT/'deployment_benchmark.json')
    c.put(c.OUT/'final_costs.json',dict(API_calls=0,API_cost_cny=0,API_cap_cny=30,cloud_rental_cny=None,cloud_hourly_price_unknown=True,
        cloud_encoding_seconds=costs['encoding']['seconds_this_run'],cloud_frozen_seconds=sum(v['seconds'] for v in train if v['family']=='frozen'),cloud_finetuned_seconds=sum(v['seconds'] for v in train if v['family']=='finetuned'),
        cloud_sum_measured_stage_seconds=costs['encoding']['seconds_this_run']+sum(v['seconds'] for v in train),
        local_C48_seconds=costs['c48']['seconds_this_resume'],local_prior_encoding_seconds=3028.9574644565582,local_interrupted_finetuning_checkpoint_seconds=1939.1826543807983,
        local_fusion_train_feature_seconds=sum(v['seconds'] for v in c.read(c.OUT/'fusion_feature_cost.json')),
        local_deployment={k:dict(N=v['N'],seconds=v['forward_seconds'],mean_seconds=v['forward_seconds']/v['N'],process_wall_seconds=v['process_wall_seconds'],label_disagreements=v['label_disagreements']) for k,v in bench.items()},
        model_size=c.read(c.OUT/'model_size.json'),per_fold_saved_weights_bytes=sorted({v['weights_bytes'] for v in train}),
        cost_limitations='Stage sums are not billed instance runtime; cold start, data transfer, idle time, local electricity and opportunity costs are not priced. Deployment timing excludes C48 retrieval and uses 12 hash-selected fold0 claims only.'))
    print(metric_table(fm));print('patient',patient)
if __name__=='__main__':main()
