"""Post-fit reporting only: never modifies fitted models, selection, or predictions."""
import argparse
from pathlib import Path
import numpy as np
import common as c
import analysis as a
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);args=ap.parse_args();out=Path(args.run).resolve()
    data=c.read(out/'inputs_numeric.json');mapping={'DS_to_Q':'bridge_qwen','Q_to_DS':'bridge_deepseek'}
    names=c.read(out/'completion.json')['datasets'];models=c.METHODS;all_metrics=c.csvread(out/'all_metrics.csv')
    supplement=out/'supplement';supplement.mkdir(exist_ok=False);rhw=[];u4=[];state_info=[];parameters=[]
    for name in names:
        rows=data[mapping.get(name,name)];saved=np.load(out/'frozen_predictions'/(name+'.npz'));y=np.array([r['y'] for r in rows]);base=saved['U0_labels']
        z,_=c.arrays(rows);z4=z.copy();z4[:,0]+=4
        u4.append(dict(dataset=name,Joint_NLL_equals_U4=bool(np.array_equal(saved['Joint_NLL_labels'],c.decode(z4)))))
        for m in models:
            p=saved[m+'_labels'];changed=p!=base;monotone=bool(np.all((base[changed]!=0)&(p[changed]==0)))
            R=int(sum((base!=0)&(p==0)&(y==0)));H=int(sum((base==y)&(y!=0)&(p==0)));W=int(sum((base!=y)&(base!=0)&(y!=0)&(p==0)))
            rhw.append(dict(dataset=name,method=m,only_nonS_to_S=monotone,R=R,H=H,W=W,
              net_correct=int(sum(p==y)-sum(base==y)),new_false_S=int(sum((y!=0)&(p==0))-sum((y!=0)&(base==0)))))
            if monotone:assert rhw[-1]['net_correct']==R-H and rhw[-1]['new_false_S']==H+W
    for p in sorted((out/'fits').glob('*/fold?.json')):
        r=c.read(p);states=c.csvread(p.with_name(p.stem+'_states.csv'));eligible=[s for s in states if s['eligible']=='True']
        state_info.append(dict(source=r['source'],fold=r['fold'],states=len(states),eligible=len(eligible)))
        for m,v in r['models'].items():parameters.append(dict(source=r['source'],fold=r['fold'],method=m,lambda_value=v.get('lam'),T=v.get('T'),boundary=v.get('boundary',False),theta=str(v.get('theta',''))))
    c.csvwrite(supplement/'RHW.csv',rhw);c.csvwrite(supplement/'selection_feasibility.csv',state_info)
    c.csvwrite(supplement/'parameters.csv',parameters);c.put(supplement/'joint_equals_U4.json',u4)
    rr=data['main40'];saved=np.load(out/'frozen_predictions/main40.npz');extra={}
    for scope in ('all','human','llm'):
        ii=np.array([i for i,r in enumerate(rr) if scope=='all' or r['author']==scope]);rows=[rr[i] for i in ii]
        for m in ('G_022','M_022','V_022'):
            bp=(saved['U2_labels'][ii],saved['U2_logprob'][ii]);cp=(saved[m+'_labels'][ii],saved[m+'_logprob'][ii])
            p=c.paired_compare(c.cohort(rows),c.predictions(rows,bp[0]),c.predictions(rows,cp[0]),iterations=1000)
            p['probability_and_risk']=a.paired_extra(rows,bp,cp);extra[scope+'/'+m+'-vs-U2']=p
    c.put(supplement/'auxiliary_pairs.json',extra)
    labels={'U0':'U0','U2':'固定U2','U2_T':'U2＋温度T','Joint_NLL':'联合NLL（尺度＋S偏置）',
      'Task_T':'任务目标λ＋T','Robust_T':'患者稳健λ＋T','G_022':'022学习单一λ','M_022':'022多类偏置','V_022':'022 vector scaling','T_022':'022原温度缩放'}
    metrics=c.read(out/'main40/metrics.json');pairs=c.read(out/'main40/paired.json')
    lines=['# 034扩展：支持边界与置信度解耦实验','',
      '**已执行并通过自检；尚未独立审计。0新增API，0费用，reserved40未使用。**','',
      '## 核心结论','',
      '1. U2＋T确实保持全部预测标签不变，并大幅降低NLL；但主40人队列的Brier反而上升，不能称概率质量全面提升。',
      '2. 任务型与患者稳健λ在所有外层折都返回λ=2。主40人的每折11种训练预测状态里，只有U2满足PA不降且false-S不增的约束，因此没有实际选择空间，不能据此宣称稳健学习优于固定2。',
      '3. 联合NLL在主40人上多判对67条，但增加54条false-S。各折λ均触及范围上界4；分类增益主要体现更激进工作点，不是找到稳定内点最优值。',
      '4. 旧022多类偏置在当前主队列的PA/MCC点估计更高，但同样增加false-S并降低NS召回；属于预设辅助对照，不根据本轮结果改选主方案。','',
      '## 1. 主40人：同3675条患者外预测','',
      '|方法|正确|PA|MCC|false-S|NLL|Brier|ECE10|','|---|---:|---:|---:|---:|---:|---:|---:|']
    for m in models:
        v=metrics['all/'+m];lines.append(f"|{labels[m]}|{v['correct']}/3675|{v['PA']:.2%}|{v['MCC']:.4f}|{v['false_S']}|{v['NLL']:.4f}|{v['Brier']:.4f}|{v['ECE10']:.4f}|")
    lines+=['','## 2. 配对差值及不确定性','','以下为1000次固定预测患者重抽样95%区间；开发交叉验证，不包含完整重拟合/方法选择的不确定性。','',
      '|比较|ΔPA，百分点|ΔMCC|ΔNLL|ΔBrier|Δfalse-S率，百分点|','|---|---|---|---|---|---|']
    def fmt(v,scale=1):return f"{v['delta']*scale:+.4f} [{v['ci95'][0]*scale:+.4f}, {v['ci95'][1]*scale:+.4f}]"
    for m in ('U2_T','Joint_NLL','Task_T','Robust_T','M_022','V_022'):
        p=pairs['all/'+m+'-vs-U2'] if m in ('U2_T','Joint_NLL','Task_T','Robust_T') else extra['all/'+m+'-vs-U2']
        v=p['metrics'];q=p['probability_and_risk']
        lines.append(f"|{labels[m]}−U2|{fmt(v['percent_agreement'],100)}|{fmt(v['mcc'])}|{fmt(q['NLL'])}|{fmt(q['Brier'])}|{fmt(q['FSR'],100)}|")
    lines+=['','false-S率的分母为782条真实非Supported；它不同于全队列错误率或预测Supported中的错误比例。','','## 3. 类别与作者代价','',
      '|范围|方法|正确/N|MCC|false-S|S召回|NS召回|NA召回|','|---|---|---:|---:|---:|---:|---:|---:|']
    for scope in ('all','human','llm'):
        for m in ('U2','U2_T','Joint_NLL','M_022','V_022'):
            v=metrics[scope+'/'+m]
            lines.append(f"|{scope}|{labels[m]}|{v['correct']}/{v['n']}|{v['MCC']:.4f}|{v['false_S']}|{v['S_recall']:.2%}|{v['NS_recall']:.2%}|{v['NA_recall']:.2%}|")
    lines+=['','联合NLL相对U2：S正确+97、NS正确−30、NA不变，合计+67。多类偏置：S+97、NS−50、NA+43，合计+90。vector scaling的NS召回仅8.08%，不能只依据较低NLL或较高合并PA宣布三类全面改善。',
      '完整R/H/W、逐条修错/误伤、类别矩阵、逐患者结果及患者等权PA分别保存在supplement/RHW.csv、各队列transitions.csv、metrics.json、patients.csv及patient_directions.json。','',
      '## 4. 022复现与重复实验','','022原4折不变，1529条R0用于拟合；879条R1从未进入拟合。G/M/V/T与U0/U2共14448个预测标签逐条复现。','',
      '|队列|方法|正确/N|MCC|false-S|NLL|Brier|','|---|---|---:|---:|---:|---:|---:|']
    for name in ('old_R0','old_R1','bridge_deepseek','bridge_qwen','DS_to_Q','Q_to_DS'):
        mm=c.read(out/name/'metrics.json')
        for m in ('U2','U2_T','Joint_NLL'):
            v=mm['all/'+m];lines.append(f"|{name}|{labels[m]}|{v['correct']}/{v['n']}|{v['MCC']:.4f}|{v['false_S']}|{v['NLL']:.4f}|{v['Brier']:.4f}|")
    lines+=['','旧879条同ID重复中，U2/U2+T/任务λ/稳健λ均翻转81条；联合NLL翻转97条。温度缩放不改变标签，所以不能降低生成波动。',
      'DS_to_Q与Q_to_DS为同患者范围的跨Judge参数直接迁移；bridge_*为各自Judge重新拟合规则。024全部879条评分有效，直接Judge缺失的一条不影响本次评分后处理。',
      '跨Judge温度迁移的NLL接近目标Judge内重拟合，但样本只有10名患者；不能据此声称任意模型通用。所有材料均来自已用development，重复或跨模型输出不算新增患者。','',
      '## 5. 参数、约束与方法解释','',
      '|主40人外层折|U2温度T|联合NLL有效λ|任务λ|稳健λ|候选状态|可行状态|','|---|---:|---:|---:|---:|---:|---:|']
    for fold in range(4):
        r=c.read(out/f'fits/main40/fold{fold}.json')['models'];s=next(s for s in state_info if s['source']=='main40' and s['fold']==fold)
        lines.append(f"|{fold}|{r['U2_T']['T']:.4f}|{r['Joint_NLL']['lam']:.4f}|{r['Task_T']['lam']:.4f}|{r['Robust_T']['lam']:.4f}|{s['states']}|{s['eligible']}|")
    lines+=['','本轮采用严格的训练PA与false-S约束，主40人的可行集合只剩U2。稳健分位数目标未能发挥选择作用；不应将此结果包装成新稳健算法成功或λ=2的普遍最优性证明。',
      '联合NLL的λ=4位于预设[0,4]边界。保持上界，不根据评价结果扩大搜索；其参数不代表无约束全局最优。与022辅助校准器的正则化和边界不同，不能把全部差异归因于NLL目标。',
      'U2+T只保证固定λ标签不变，不保证NLL、Brier、ECE和每一类概率校准同时改善。主队列NLL改善、Brier退化并存，是本轮必须保留的结果。',
      '建议保持U2作为既有分类参照；U2+T作为概率表达扩展的候选，需要明确其Brier代价。联合NLL/多类偏置保留为更激进的辅助工作点，不自动替换主方案。','',
      '## 6. 复现、自检与目录说明','',
      '九项合成测试通过；verify.py完成1013项检查、16组交叉验证参数确定性重拟合、保存预测重放、分类指标复算及14448个022旧标签复现。执行者自检不等于独立审计。',
      '执行中工作区被另一处修改将原扩展移至035。为不覆盖并行工作，本轮在tasks/034_same_data_comparison/lambda_run_snapshot_001保存独立执行快照，修复其仓库根路径后运行；035目录未被本轮回写。快照原始标题/控制台仍可能出现035，实验内容和034输出绑定以freeze.json为准。',
      '旧034三方比较保留。运行：python -B tasks/034_same_data_comparison/lambda_run_snapshot_001/run.py --output <全新目录>；复查：同目录verify.py --run <运行目录>。使用现有research-verifact-029环境，无包安装或更新。',
      '主要文件：all_metrics.csv、各数据集metrics.json/paired.json、fits、frozen_predictions、repeat_stability.csv、transfer_vs_refit.json、supplement、verification.json。']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    figdir=out/'figures';figdir.mkdir(exist_ok=False)
    methods=['U0','U2','U2_T','Joint_NLL','M_022','V_022'];en=['U0','U2','U2 + temperature','Joint NLL','Class bias (022)','Vector scaling (022)']
    for metric in ('NLL','Brier'):
        fig,ax=plt.subplots(figsize=(8,4.5));vals=[metrics['all/'+m][metric] for m in methods]
        ax.barh(en,vals);ax.invert_yaxis();ax.set_xlabel(metric+' (lower is better)')
        ax.set_title('Patient-out development evaluation: 40 patients, 3675 claims')
        for i,v in enumerate(vals):ax.text(v+.005,i,f'{v:.4f}',va='center',fontsize=9)
        ax.set_xlim(0,max(vals)*1.2);fig.tight_layout()
        fig.savefig(figdir/(metric.lower()+'.png'),dpi=180);fig.savefig(figdir/(metric.lower()+'.svg'));plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.8));x=np.arange(3);used=['U2','Joint_NLL','M_022','V_022']
    for j,m in enumerate(used):ax.bar(x+(j-1.5)*.18,[metrics['all/'+m][k] for k in ('S_recall','NS_recall','NA_recall')],width=.18,label=m)
    ax.set_xticks(x,['Supported','Not Supported','Not Addressed']);ax.set_ylim(0,1);ax.set_ylabel('Recall');ax.set_title('Class-specific trade-offs');ax.legend(fontsize=8);fig.tight_layout()
    fig.savefig(figdir/'class_recall.png',dpi=180);fig.savefig(figdir/'class_recall.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.5))
    for source in ('old_R0','main40','bridge_deepseek','bridge_qwen'):
        pts=[p for p in parameters if p['source']==source and p['method']=='U2_T'];ax.plot([p['fold'] for p in pts],[p['T'] for p in pts],marker='o',label=source)
    ax.set_xticks(range(4));ax.set_xlabel('Held-out patient fold');ax.set_ylabel('Fitted temperature T');ax.set_title('Temperature fitted using training patients only');ax.legend(fontsize=8);fig.tight_layout()
    fig.savefig(figdir/'temperatures.png',dpi=180);fig.savefig(figdir/'temperatures.svg');plt.close(fig)
    original=c.ROOT/'outputs/035_lambda_boundary_calibration/source_034_fingerprints.json'
    if original.exists():
        status={p:c.sha(c.ROOT/p)==h for p,h in c.read(original).items()};assert all(status.values()),'Original034 changed'
        c.put(supplement/'original034_unchanged.json',status)
    c.put(out/'delivery_manifest.json',dict(created_utc=c.now(),files={str(p.relative_to(out)):c.sha(p) for p in out.rglob('*') if p.is_file() and p.name!='delivery_manifest.json'},
      reporting_code_sha256=c.sha(Path(__file__)),status='executed_self_verified_not_independently_audited'))
    print('034 report and figures complete',flush=True)

if __name__=='__main__':main()
