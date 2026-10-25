"""Compact paper figures, vector SVG and300dpi PNG; no new scientific computation."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common036 as c
NAMES={'O':'VeriFact','B':'Direct Judge','U0':'U0','U2':'U2','U2_T':'U2 + T','Gate_A':'U2 + A Gate','Std_T':'Temperature','Std_G':'Single bias','Std_M':'Class biases','Std_V':'Vector scaling','Joint_NLL':'Joint NLL'}
def main(name='figures_002'):
    import re
    assert re.fullmatch(r'figures_[0-9]{3}',name)
    out=c.OUT/name;out.mkdir(exist_ok=False);metrics=c.read(c.OUT/'analysis_001/R0/metrics.json')
    plt.rcParams.update({'font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    def save(fig,name):
        fig.savefig(out/(name+'.svg'),bbox_inches='tight');fig.savefig(out/(name+'.png'),dpi=300,bbox_inches='tight');plt.close(fig)
    methods=['O','B','U0','U2','Gate_A','Std_G','Std_M','Std_V','Joint_NLL'];x=np.arange(len(methods));colors=['#89959d','#89959d','#5a819a','#007f7d','#c47b23','#988eb0','#988eb0','#988eb0','#988eb0']
    fig,axs=plt.subplots(1,3,figsize=(14,4),layout='constrained')
    for ax,key,label,scale in zip(axs,['PA','MCC','false_S'],['Agreement (%)','MCC','False Supported (count)'],[100,1,1]):
        vals=[metrics['all/'+m][key]*scale for m in methods];ax.bar(x,vals,color=colors);ax.set_xticks(x,[NAMES[m] for m in methods],rotation=60,ha='right');ax.set_ylabel(label);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
        for xx,v in zip(x,vals):ax.annotate(f'{v:.1f}' if key=='PA' else f'{v:.3f}' if key=='MCC' else str(int(v)),(xx,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
    save(fig,'figure1_performance_risk')
    methods=['O','B','U0','U2','Gate_A','Std_M','Std_V'];fig,axs=plt.subplots(1,3,figsize=(12,3.7),layout='constrained')
    for ax,scope in zip(axs,['all','human','llm']):
        xx=np.arange(3)
        for j,m in enumerate(methods):ax.bar(xx+(j-3)*.115,[100*(metrics[scope+'/'+m][k] or 0) for k in ['S_recall','NS_recall','NA_recall']],width=.115,label=NAMES[m])
        ax.set_xticks(xx,['S','NS','NA']);ax.set_ylim(0,105);ax.set_title(scope.upper());ax.set_ylabel('Recall (%)');ax.grid(axis='y',alpha=.2)
    axs[-1].legend(fontsize=8,loc='upper left',bbox_to_anchor=(1.02,1));save(fig,'figure2_class_recall')
    d=c.read(c.OUT/'analysis_001/R0/directions.json');fig,ax=plt.subplots(figsize=(13,4),layout='constrained')
    u=next(v for v in d if v['comparison']=='U2-vs-U0');g=next(v for v in d if v['comparison']=='Gate_A-vs-U2');ids=sorted(u['patient_deltas']);x=np.arange(len(ids))
    ax.bar(x-.2,[u['patient_deltas'][sid] for sid in ids],width=.4,label='U2 minus U0',color='#007f7d');ax.bar(x+.2,[g['patient_deltas'][sid] for sid in ids],width=.4,label='Gate minus U2',color='#c47b23');ax.axhline(0,color='black',lw=.7);ax.set_xticks(x,ids,rotation=90,fontsize=8);ax.set_ylabel('Change in correct claims');ax.set_xlabel('Reserved patient');ax.legend();save(fig,'figure3_patient_deltas')
    rows=c.csvread(c.OUT/'analysis_001/R0/reliability.csv');fig,axs=plt.subplots(1,3,figsize=(11,3.5),layout='constrained')
    for ax,label in zip(axs,c.LABELS):
        for m in ['U2','U2_T','Std_V']:
            rr=[r for r in rows if r['method']==m and r['label']==label and int(r['n'])>0];ax.plot([float(r['mean_probability']) for r in rr],[float(r['frequency']) for r in rr],marker='o',ms=3,label=NAMES[m])
        ax.plot([0,1],[0,1],color='gray',ls='--',lw=.7);ax.set(xlim=(0,1),ylim=(0,1),title=label,xlabel='Mean predicted probability',ylabel='Observed frequency')
    axs[0].legend(fontsize=8);save(fig,'figure4_reliability')
    risk=[r for r in c.csvread(c.OUT/'analysis_001/R0/risk_rescue.csv') if r['scope']=='all'];fig,ax=plt.subplots(figsize=(6,4),layout='constrained')
    for m in ['U0','U2','Gate_A']:
        r=next(r for r in risk if r['method']==m);x=float(r['new_false_S']);y=float(r['R']);ax.scatter(x,y,s=70);ax.annotate(NAMES[m],(x,y),xytext=(5,5),textcoords='offset points')
    ax.set(xlabel='New false Supported among U2 candidates (H + W)',ylabel='True Supported rescued (R)');ax.grid(alpha=.2);save(fig,'figure5_risk_rescue')
    c.put(out/'manifest.json',{p.name:c.sha(p) for p in out.iterdir() if p.is_file()});print('036 figures generated')
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output-name',default='figures_002');main(parser.parse_args().output_name)
