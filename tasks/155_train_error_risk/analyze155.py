"""Fit frozen risk model on original training patients, evaluate cached1817."""
from pathlib import Path
from collections import Counter,defaultdict
import sys,json,time,math
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import joblib
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/146_caption_transfer'))
from common146 import assets,read,rows,save,score,five_table,markdown_table,cost
from features155 import features,FEATURE_NAMES

def main():
    started=time.perf_counter();P=R/'.local_models/155_train_error_risk'
    keys,pred,base=assets();p=pred['claim_repeat136']
    trainkeys={r['id']:r for r in rows(P/'keys.jsonl')}
    traininput={r['id']:r for r in rows(P/'inputs_source.jsonl')}
    raw={r['id']:r for r in (read(f) for f in (P/'evidence/results/native_train').glob('*.json'))}
    assert set(raw)==set(trainkeys)==set(traininput) and len(raw)==512
    assert not ({str(r['sid']) for r in trainkeys.values()} & {str(r['sid']) for r in keys.values()})
    assert all(r['parsed']['valid'] and r['finish_reason']=='stop' and math.isfinite(r['native_margin']) for r in raw.values())
    ids=sorted(i for i,r in raw.items() if r['parsed']['verdict']=='Supported')
    X=np.array([features(traininput[i]['claim'],traininput[i]['reference'],raw[i]['native_margin']) for i in ids])
    y=np.array([int(trainkeys[i]['GT']!='Supported') for i in ids]);assert len(set(y))==2
    models={}
    for name,cols in [('train_error_risk',list(range(9))),('train_margin_only',[0])]:
        model=make_pipeline(StandardScaler(),LogisticRegression(C=1.,class_weight='balanced',max_iter=1000,random_state=155))
        model.fit(X[:,cols],y);joblib.dump(model,P/(name+'.joblib'));models[name]=(model,cols)
    pool={i for i,v in p.items() if v=='Supported'};margin={}
    for scope in ('pilot','screen160','old500_fixpath','full1817'):
        for f in (R/'.local_models/144_native_confidence'/scope/'evidence/results/claim_repeat136').glob('*.json'):
            r=read(f);i=r['id']
            if i in pool:
                if i in margin:assert margin[i]==r['logit_S_minus_Not']
                margin[i]=r['logit_S_minus_Not']
    assert set(margin)==pool
    inputs={r['id']:r for scope in ('screen160','old500','full1817') for r in rows(R/f'.local_models/136_claim_repeat_transfer/claim_repeat_{scope}/bundle/data/inputs.jsonl')}
    assert pool<=set(inputs)
    ordered=sorted(pool);Xe=np.array([features(inputs[i]['claim'],inputs[i]['reference'],margin[i]) for i in ordered])
    values={'global_margin':{i:-margin[i] for i in pool}}
    group=defaultdict(list)
    for i in pool:group[str(keys[i]['sid'])].append(i)
    values['patient_rank']={i:-(sum(margin[j]<margin[i] for j in group[str(keys[i]['sid'])])+.5*sum(margin[j]==margin[i] for j in group[str(keys[i]['sid'])]))/len(group[str(keys[i]['sid'])]) for i in pool}
    coefficients={}
    for name,(model,cols) in models.items():
        prob=model.predict_proba(Xe[:,cols])[:,1];values[name]=dict(zip(ordered,map(float,prob)))
        coefficients[name]=dict(features=[FEATURE_NAMES[c] for c in cols],standardized_coefficients=model[-1].coef_[0].tolist(),intercept=model[-1].intercept_.tolist())
    results={};flags={};workloads=sorted({0,178,290,*[int(len(pool)*q/100) for q in (5,10,20,30)]})
    for name,v in values.items():
        order=sorted(pool,key=lambda i:(-v[i],i));results[name]={};flags[name]={}
        for k in workloads:
            review=set(order[:k]);automatic=set(keys)-review;m=score(automatic,p,keys)
            results[name][str(k)]=dict(k=k,auto_N=len(automatic),coverage=len(automatic)/len(keys),intercepted_FS=88-m['false_S'],residual_FS=m['false_S'],original_non_S=362,review_correct_S=sum(keys[i]['GT']=='Supported' for i in review),auto_metrics=m)
            flags[name][str(k)]=sorted(review)
    complete=read(P/'evidence/results/complete.json');wall=read(P/'evidence/controller_done.json')['epoch']-read(P/'evidence/results/deadlines.json')['started']
    budget=dict(generation=cost(raw,raw),controller_wall_seconds=wall,controller_interval_CNY=wall*1.58/3600,new_API=0)
    train=dict(N=512,native_S_N=len(ids),native_S_error_N=int(y.sum()),patients=32,original_GT_classes=dict(Counter(r['GT'] for r in trainkeys.values())),sample_selected_by_GT=True,fit_only_training_native_S=True,training_errors_in_sample_for_existing_SFT=True)
    five=five_table(keys,keys,pred,base)
    out=dict(task=155,train=train,coefficients=coefficients,results=results,budget=budget,five_baselines=five,CPU_seconds=time.perf_counter()-started,label_changes=0,evaluation_GT_used_for_fit=False,calibration_guarantee=False)
    O=R/'outputs/155_train_error_risk';save(O/'analysis.json',out);save(P/'review_flags.json',flags)
    with (O/'scores_sanitized.jsonl').open('w',encoding='utf-8') as f:
        for i in ordered:f.write(json.dumps(dict(id=i,**{n:v[i] for n,v in values.items()}))+'\n')
    lines=['# 155 train_error_risk：只用原训练患者的实际错误拟合风险','',f"512条来自120原训练32名患者，按GT分层固定取样；136首答中{len(ids)}条预测S，其中{int(y.sum())}条原GT为非S。仅这些训练侧错误用于拟合。评价20名患者与训练32名患者不重叠；评价GT只算指标。",'',
        '固定9个特征为原生margin、命题长度、数字/否定/时间/因果/变化/连接计数、内容词在reference的覆盖；标准化后LogisticRegression C=1、balanced，无评价集调参。margin-only为同训练样本的机制对照。训练患者已经被120监督，错误是微调模型的训练内错误；分层抽样比例与部署分布不同，输出不作校准概率。','',
        '|方法|送审|自动覆盖|截获FS/88|残留FS/362|送审正确S|自动S FDR|自动MCC|自动PA|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,pts in results.items():
        for k in (178,290):
            v=pts[str(k)];m=v['auto_metrics'];lines.append(f"|{name}|{k}|{v['coverage']:.2%}|{v['intercepted_FS']}|{v['residual_FS']}|{v['review_correct_S']}|{m['S_FDR']:.2%}|{m['mcc']:.4f}|{m['percent_agreement']:.2%}|")
    lines+=['','全量136标签、MCC和PA不变；送审未当作纠错，自动子集成绩不是全量提升。无独立校准或Conformal保证。完整曲线及三类表现见analysis.json。','',
        '## 固定五基线','',markdown_table(five),'','五基线复用缓存，原作者两臂输出预算768、120/136为384，paper_r1为历史模型；共同有效ID与1817全量分开。缺失历史成本不补0。','',
        f"训练侧512条取分新增GPU推理，CPU拟合不更新LoRA；输入{budget['generation']['input_tokens']['total']}、输出{budget['generation']['output_tokens']['total']} tokens，生成{budget['generation']['seconds']['total']:.2f}秒，controller {wall:.2f}秒、区间¥{budget['controller_interval_CNY']:.4f}。排队、准备和回传还计入整个窗口；新增API为0。部署特征直接复用已有margin和原文，无额外LLM调用。",'',
        '结论：当前9特征风险拟合在178/290条送审下残留false-S为49/29，原margin为44/29，没有改善；停止该固定配方的扩大与调参。margin-only与原margin相同，不能把单调再映射包装成收益。该负结果不否定有依据的其他训练方向。','',
        '系数、所有失败与原训练GT/原文私有保存；公开文件仅含必要数值、ID和代码。未以评价病例训练。']
    (O/'report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps(dict(train=train,results={n:{k:v[k]['residual_FS'] for k in ('178','290')} for n,v in results.items()},budget=budget),ensure_ascii=False))

if __name__=='__main__':main()
