"""One descriptive risk-rescue figure, complete reference plus local view."""
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common031 as c
def run(destination):
    out=c.OUT/destination;c.require(not out.exists(),'New figure directory');out.mkdir();analysis=c.OUT/'analysis_001';metrics=c.read(analysis/'metrics.json');curves=c.csvread(analysis/'curves.csv');globalrows=[r for r in curves if r['reference']=='global_lambda'];F=np.array([float(r['risk']) for r in globalrows]);R=np.array([float(r['R']) for r in globalrows]);pts=c.base.frontier.pareto(F,R);hull=c.base.frontier.hull(pts)
    plt.rcParams.update({'font.size':10,'svg.fonttype':'none'});fig,axes=plt.subplots(1,2,figsize=(10,4.3),layout='constrained');colors={'A':'#2471a3','B':'#d68910','C':'#229954','D':'#a93226'}
    for ax in axes:
        x,y=zip(*pts);ax.step(x,y,where='post',color='.55',lw=1,label='Global lambda (deterministic)');x,y=zip(*hull);ax.plot(x,y,'--',color='.35',lw=1,label='Global lambda (mixture)')
        for m in 'ABCD':
            before=metrics['all/before_'+m];after=metrics['all/after_'+m];ax.plot([before['risk'],after['risk']],[before['R'],after['R']],color=colors[m],lw=1,alpha=.7)
            ax.scatter(before['risk'],before['R'],s=60,facecolors='white',edgecolors=colors[m],label=m+' before');ax.scatter(after['risk'],after['R'],s=60,color=colors[m],marker='s',label=m+' after')
            # Color/marker legend identifies methods without overlapping text at tied points.
        u2=metrics['all/U2'];ax.scatter(u2['risk'],u2['R'],marker='x',s=60,color='black',label='Fixed U2');ax.set_xlabel('Added false-S (H + W)');ax.set_ylabel('Rescued true Supported (R)');ax.grid(alpha=.2)
    axes[0].set_title('Complete global-lambda reference');axes[1].set_title('Frozen operating points (local view)');names=['U2',*[e+'_'+m for e in ('before','after') for m in 'ABCD']];maxx=max(metrics['all/'+n]['risk'] for n in names);maxy=max(metrics['all/'+n]['R'] for n in names);axes[1].set_xlim(-1,maxx+max(3,.1*maxx));axes[1].set_ylim(-1,maxy+max(3,.15*maxy));handles,labels=axes[1].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=4,fontsize=8)
    fig.savefig(out/'risk_rescue.png',dpi=220);fig.savefig(out/'risk_rescue.svg');plt.close(fig);c.put(out/'manifest.json',dict(inputs={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [analysis/'metrics.json',analysis/'curves.csv',c.TASK/'plot031.py']},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='figures_001');run(p.parse_args().output)
