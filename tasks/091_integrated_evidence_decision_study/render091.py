"""Readable diagnostic tables and one standalone decision-path figure."""
from common091 import *
def main():
    a=read(OUT/'B_diagnosis.json');parts=['# B：统一口径完整诊断表','','所有结果为冻结分数的事后诊断，不选择新方法。Original为同ID不同历史系统参照。','']
    for panel,d in a['panels'].items():
        parts += [f"## {panel}：全体{d['full_n']}，四臂core共同有效{d['common_core_n']}",'', '|配置（共同有效）|MCC|PA|正确数|错误支持/non-S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
        mm=[('Original',d['original'])]+[(arm+'/'+m,d['metrics'][arm][m]) for arm in ARMS for m in METHODS]
        for name,v in mm:
            recall='/'.join('—' if v['per_class'][k]['recall'] is None else f"{100*v['per_class'][k]['recall']:.2f}%" for k in LABELS)
            parts.append(f"|{name}|{v['MCC']:.4f}|{v['PA']:.2%}|{v['correct']}/{v['n']}|{v['false_S']}/{v['non_S']}|{v['Macro_F1']:.4f}|{recall}|")
        parts+=['','### P−F按GT的正确数增量','','|GT|raw净值|最终净值|','|---|---:|---:|']
        for k in LABELS:
            v=d['metrics'];raw=v['P90']['raw']['confusion_matrix'][LABELS.index(k)][LABELS.index(k)]-v['F4']['raw']['confusion_matrix'][LABELS.index(k)][LABELS.index(k)];fin=v['P90']['PriorG']['confusion_matrix'][LABELS.index(k)][LABELS.index(k)]-v['F4']['PriorG']['confusion_matrix'][LABELS.index(k)][LABELS.index(k)]
            parts.append(f'|{k}|{raw:+d}|{fin:+d}|')
        parts+=['','### raw到最终的联合正确性路径','','|类型|人数（命题）|GT组成|','|---|---:|---|']
        for k,v in d['kind_counts'].items():parts.append(f"|{k}|{v['n']}|{v['GT']}|")
        parts+=['','### 每类标签转移（含未改标签，完整分区）','','|臂|前→后|GT|前标签|后标签|数量|','|---|---|---|---|---|---:|']
        for x in d['class_transitions']:parts.append(f"|{x['arm']}|{x['before']}→{x['after']}|{x['GT']}|{x['old']}|{x['new']}|{x['n']}|")
        parts+=['','### 患者分布','','|患者|共同有效数|raw救回/伤害/净|最终救回/伤害/净|','|---|---:|---|---|']
        for x in d['patients']:parts.append(f"|{x['sid']}|{x['n']}|{x['raw']['rescue']}/{x['raw']['harm']}/{x['raw']['net']:+d}|{x['final']['rescue']}/{x['final']['harm']}/{x['final']['net']:+d}|")
        parts+=['','### 类对log-ratio排序（P−F；固定偏置不会改变同一臂的类对AUC）','','|类别对|F4 AUC|P90 AUC|差值|患者95%CI|','|---|---:|---:|---:|---|']
        for key,v in d['auc'].items():
            if v['defined']:parts.append(f"|{key}|{v['arms']['F4']['AUC']:.4f}|{v['arms']['P90']['AUC']:.4f}|{v['P_minus_F']:+.4f}|{v['CI95']}|")
            else:parts.append(f'|{key}|—|—|—|本面板无该真实类别|')
    text(OUT/'B_tables.md','\n'.join(parts)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
    specs=[('Natural: 167 common-core claims',[7,-4,-1,2,-2,2],['Raw net','F catches up\n(S)','P gain lost\n(NS)','Raw harms\nerased (S)','Final-only\nharms','Final net']),('Stress: 65 common-core claims',[1,-2,3,-2,0],['Raw net','P gains lost\n(NS)','Final-only\nrescues','Final-only\nharms','Final net'])]
    for ax,(title,vals,labs) in zip(axs,specs):
        level=0
        for i,v in enumerate(vals):
            endpoint=i in (0,len(vals)-1);start=0 if endpoint else level
            ax.bar(i,v,bottom=start,color='#406f96' if endpoint else '#4c9668' if v>=0 else '#be6656')
            level=v if endpoint else level+v
            ax.text(i,max(start,start+v)+.15,f'{v:+d}',ha='center',fontsize=10)
        ax.axhline(0,color='black',linewidth=.6);ax.set_xticks(range(len(vals)),labs,fontsize=8);ax.set_ylabel('P90 minus F4: number correct');ax.set_title(title);ax.set_ylim(-2,8)
    fig.suptitle('Raw advantage and final decision advantage are different quantities')
    fig.savefig(OUT/'decision_paths.png',dpi=180);fig.savefig(OUT/'decision_paths.svg');plt.close(fig)
    rep=read(OUT/'B_repeat090.json');out={}
    for panel in ('natural','pressure'):
        out[panel]={}
        for arm in ('B','F4'):
            z=[r for r in rep['rows'] if r['panel']==panel and r['arm']==arm and r['old_valid'] and r['new_valid']]
            out[panel][arm]=dict(n=len(z),layers={m:dict(old_correct=sum(x['old'][m]==x['GT'] for x in z),new_correct=sum(x['new'][m]==x['GT'] for x in z),flips=sum(x['old'][m]!=x['new'][m] for x in z)) for m in ('raw','PriorG')})
    put(OUT/'B_repeat_by_panel.json',out)
if __name__=='__main__':main()
