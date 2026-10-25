"""Small paper figures from saved results only."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common033 as s

def main(destination='figures_001'):
    out=s.OUT/destination;s.require(not out.exists(),'Figure directory exists');out.mkdir();plt.rcParams.update({'font.size':10,'svg.fonttype':'none'});metrics=s.read(s.OUT/'evaluation_001/metrics.json');curves=s.csvread(s.OUT/'evaluation_001/curves.csv');fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained');palette={'A':'#2471a3','D':'#b03a2e'}
    for ax,scope,title in zip(axes,['expansion','confirmation'],['Selection panel: 12 patients / 998 claims','Check panel: 12 patients / 1148 claims']):
        rr=[r for r in curves if r['scope']==scope and r['reference']=='global_lambda'];F=np.array([float(r['risk']) for r in rr]);R=np.array([float(r['R']) for r in rr]);h=s.old.frontier.hull(s.old.frontier.pareto(F,R));x,y=zip(*h);ax.plot(x,y,'--',color='.45',label='Full global-lambda mixture')
        for m in ('A','D'):
            for kind,marker,filled in [('historical28','o',False),('all40','s',False),('directed_best','*',True)]:
                v=metrics[scope+'/all/'+m+'_'+kind];ax.scatter(v['risk'],v['R'],marker=marker,s=120 if marker=='*' else 55,edgecolors=palette[m],facecolors=palette[m] if filled else 'white',label=m+' '+{'historical28':'historical28 LOPO','all40':'all40 LOPO','directed_best':'selected subset'}[kind])
        u=metrics[scope+'/all/U2'];ax.scatter(u['risk'],u['R'],c='black',marker='x',s=50,label='Fixed U2');ax.set_xlim(-1,u['risk']+4);ax.set_ylim(max(0,u['R']*.45),u['R']+5);ax.set_title(title,fontsize=11);ax.set_xlabel('Added false-S (H + W)');ax.set_ylabel('Rescued Supported (R)');ax.grid(alpha=.2)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=4,fontsize=8);fig.savefig(out/'risk_rescue.png',dpi=220);fig.savefig(out/'risk_rescue.svg');plt.close(fig)
    sources=s.csvread(s.OUT/'association_001/common_panel_source_comparison.csv');fig,axes=plt.subplots(1,2,figsize=(9,3.8),layout='constrained')
    for method,color in [('A','#2471a3'),('B','#b7950b'),('D','#b03a2e')]:
        rr=[r for r in sources if r['method']==method];x=[int(r['train_026']) for r in rr];axes[0].plot(x,[100*float(r['rescue_retention_mean']) for r in rr],'-o',color=color,label=method);axes[1].plot(x,[float(r['risk_mean']) for r in rr],'-o',color=color,label=method)
    axes[0].axhline(80,color='.5',ls='--',lw=1);axes[0].set_ylabel('Mean rescue retention (%)');axes[1].set_ylabel('Mean added false-S');
    for ax in axes:ax.set_xticks(range(5));ax.set_xlabel('Training patients from batch 026 (k = 5)');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('All existing fixed 5-patient sets on the common selection panel',fontsize=11);fig.savefig(out/'source_tradeoff.png',dpi=220);fig.savefig(out/'source_tradeoff.svg');plt.close(fig)
    d=s.read(s.OUT/'supplement_001/patient_directions.json');chosen=[next(r for r in d if r['scope']=='confirmation' and r['comparison']==m+'_directed_best-minus-'+m+'_all40') for m in ('A','D')];subjects=sorted(chosen[0]['deltas']);y=np.arange(len(subjects));fig,ax=plt.subplots(figsize=(7,4.8),layout='constrained')
    for offset,method,row in [(-.18,'A',chosen[0]),(.18,'D',chosen[1])]:ax.barh(y+offset,[row['deltas'][p] for p in subjects],height=.34,label=method+' subset minus all40 LOPO',color=palette[method])
    ax.set_yticks(y,subjects);ax.axvline(0,color='.3',lw=.8);ax.set_xlabel('Delta correct claims');ax.set_ylabel('Development check patient');ax.legend(fontsize=8);ax.grid(axis='x',alpha=.2);fig.savefig(out/'patient_delta.png',dpi=220);fig.savefig(out/'patient_delta.svg');plt.close(fig);s.put(out/'manifest.json',dict(created_utc=s.now(),files={p.name:s.sha(p) for p in out.iterdir() if p.is_file()},code=s.sha(s.TASK/'plot033.py')))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',default='figures_001');main(p.parse_args().output)
