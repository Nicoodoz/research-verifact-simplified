"""Standalone scientific figures from frozen public numeric outputs only."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common095 as c
plt.rcParams.update({'font.size':10,'svg.fonttype':'path','figure.dpi':120})
COLORS=['#64748b','#60a5fa','#0f766e','#eab308','#c2410c']

def save(fig,name):
    fig.savefig(c.OUT/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(c.OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)

def main():
    coverage=c.read(c.OUT/'baseline_coverage.json');metrics=c.read(c.OUT/'baseline_metrics.json')['common_core'];models=['Original','B_raw','B_PriorG','092_Frozen','092_Finetuned']
    fig,axes=plt.subplots(2,3,figsize=(11,7));vmax=max(max(sum(metrics[k]['confusion_matrix'],[])) for k in models)
    for ax,k in zip(axes.flat,models):
        cm=np.asarray(metrics[k]['confusion_matrix']);ax.imshow(cm,cmap='Blues',vmin=0,vmax=vmax)
        for i in range(3):
            for j in range(3):ax.text(j,i,str(cm[i,j]),ha='center',va='center',color='white' if cm[i,j]>vmax*.55 else 'black')
        ax.set_xticks(range(3),['S','NS','NA']);ax.set_yticks(range(3),['S','NS','NA']);ax.set_xlabel('Predicted');ax.set_ylabel('Physician label');ax.set_title(k)
    ax=axes[1,2];values=[coverage['core_valid_B'],coverage['raw_valid_B']-coverage['core_valid_B'],coverage['successful_B']-coverage['raw_valid_B'],coverage['missing']];names=['Core valid','Raw only','Other invalid','Missing']
    ax.barh(names,values,color=['#0f766e','#60a5fa','#ef4444','#cbd5e1']);ax.set_xlim(0,9065);ax.set_title('B coverage of 9,065 IDs')
    for i,v in enumerate(values):ax.text(v+100,i,str(v),va='center')
    fig.suptitle(f"Same-ID comparison: common core N={coverage['core_valid_B']} (development evaluation)");fig.tight_layout();save(fig,'baseline_confusion_coverage')
    fig,axes=plt.subplots(1,4,figsize=(13,3.4));labels=['Author','B raw','B + G','092 frozen','092 tuned']
    for ax,metric in zip(axes,['PA','MCC','Macro_F1','false_S_rate']):
        vals=[metrics[k][metric] for k in models];ax.bar(np.arange(5),vals,color=COLORS);ax.set_xticks(range(5),labels,rotation=35,ha='right');ax.set_title(metric);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.tight_layout();save(fig,'baseline_quality_risk')
    path=c.OUT/'screen_analysis.json'
    if path.exists():
        analysis=c.read(path)['panels'];fig,axes=plt.subplots(2,2,figsize=(11,7))
        for row,panel in enumerate(['natural','mechanism']):
            d=analysis[panel];ax=axes[row,0];x=np.arange(3);width=.25
            for j,(name,col) in enumerate(zip(['E-B','C-B','C-E'],['#64748b','#0f766e','#c2410c'])):
                values=[d['comparisons']['PriorG'][name]['delta'][m]*100 for m in ['PA','MCC','Macro_F1']];ax.bar(x+(j-1)*width,values,width,label=name,color=col)
            ax.axhline(0,color='black',lw=.8);ax.set_xticks(x,['PA (pp)','MCC (x100)','Macro-F1 (x100)']);ax.set_title(f'{panel}: fixed PriorG, N={d["core_N"]}');ax.legend()
            ax=axes[row,1];names=['Program/source valid','Deployed contrast','All 3 core valid'];vals=[d['constructor_program_valid'],d['operated_N'],d['core_N']];ax.barh(names,vals,color=['#60a5fa','#0f766e','#64748b']);ax.set_xlim(0,d['N']*1.15);ax.set_title(f'{panel}: coverage / {d["N"]}')
            for i,v in enumerate(vals):ax.text(v+1,i,str(v),va='center')
        fig.tight_layout();save(fig,'screen_effect_coverage')
    cost=c.read(c.OUT/'cost_ledger.json');fig,axes=plt.subplots(1,2,figsize=(11,4));phases=list(cost['phase_costs']);vals=[cost['phase_costs'][p] for p in phases];axes[0].bar(phases,vals,color=COLORS[:len(phases)]);axes[0].set_ylabel('CNY, directory tariff + unknown reserve');axes[0].set_title(f"New task expenditure: {cost['total_directory_price_or_unknown_cny']:.2f} / 150 CNY");axes[0].tick_params(axis='x',rotation=25)
    if 'screen' in cost['logical_deployment']:
        x=np.arange(3);arms=['B','E','C'];natural=cost['logical_deployment']['screen']['natural'];values=[natural[a]['observed_usage_tariff_cny']/natural[a]['N'] for a in arms];axes[1].bar(x,values,color=['#64748b','#60a5fa','#0f766e']);axes[1].set_xticks(x,arms);axes[1].set_ylabel('CNY / claim');axes[1].set_title('Natural panel: single-arm deployment\nIncludes auxiliary calls and exact-B fallback')
    else:
        gate=c.read(c.OUT/'operation_gate.json');x=np.arange(2);axes[1].bar(x-.18,[gate['automated_eligible_panels'][p] for p in ['natural','mechanism']],.36,label='Automatic eligibility',color='#60a5fa');axes[1].bar(x+.18,[0,0],.36,label='Final Judge deployed',color='#0f766e');axes[1].set_xticks(x,['Natural / 200','Enriched / 100']);axes[1].set_ylabel('Claims');axes[1].set_title('Count gate passed; semantic checks failed');axes[1].legend()
    fig.tight_layout();save(fig,'cost_coverage')
    print('Figures written from public frozen outputs')
if __name__=='__main__':main()
