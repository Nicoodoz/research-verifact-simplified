"""Standalone publication-style SVG/PNG, using already-computed machine curves."""
import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/025_lambda_flip_risk_separability';A=OUT/'analysis_003'
def readcsv(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def hull(points):
    d={}
    for x,y in points:d[x]=max(y,d.get(x,-1))
    out=[];best=-1
    for x,y in sorted(d.items()):
        if y<=best:continue
        best=y
        while len(out)>1:
            a,b=out[-2:]
            if (b[1]-a[1])*(x-b[0])<=(y-b[1])*(b[0]-a[0])+1e-12:out.pop()
            else:break
        out.append((x,y))
    return out
def run():
    folder=OUT/'figures_001';folder.mkdir(exist_ok=False)
    globalrows=readcsv(A/'global_lambda_curves.csv');curves=readcsv(A/'gate_curves.csv');summary=json.loads((A/'summary.json').read_text(encoding='utf-8'))
    colors={'S':'#3377aa','SE':'#dd8833','SD':'#228866','SED':'#9955aa','peer_U2':'#bb4444'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    for group,title in [('024_D','DeepSeek V4 Flash 0731'),('024_Q','Qwen3.8-27B')]:
        gg=[r for r in globalrows if r['group']==group and r['author']=='all'];gp=[(float(r['risk']),float(r['R'])) for r in gg];hp=hull(gp)
        fig,axs=plt.subplots(1,2,figsize=(11,4.3),gridspec_kw={'width_ratios':[1.6,1]})
        for ax in axs:
            ax.plot(*zip(*gp),color='#333333',lw=1.4,label='Exact global lambda states')
            ax.plot(*zip(*hp),color='#333333',ls='--',lw=1.2,label='Global randomized envelope')
            ax.set_xlabel('Additional false-S (H + W)');ax.set_ylabel('Rescued true-S (R)');ax.grid(alpha=.2)
        for method in ('S','SE','SD','SED'):
            cc=[r for r in curves if r['group']==group and r['method']==method];pts=[(float(r['risk']),float(r['R'])) for r in cc]
            axs[0].plot(*zip(*pts),color=colors[method],alpha=.65,lw=1,label=method+' OOF ranking')
        for method in colors:
            p=summary[group][method]
            for ax in axs:ax.scatter(p['risk'],p['R'],color=colors[method],s=45,marker='D' if method=='peer_U2' else 'o',zorder=5)
        u2=next(r for r in gg if float(r['lambda_value'])==2);x=float(u2['risk']);y=float(u2['R'])
        axs[0].scatter([x],[y],marker='*',s=120,c='black',zorder=6,label='Fixed lambda = 2')
        axs[0].set_xlim(-.4,x*1.06);axs[0].set_ylim(0,y*1.12);axs[1].set_xlim(left=0);axs[1].set_ylim(bottom=0)
        axs[0].set_title('Candidate-range detail');axs[1].set_title('Entire nonnegative-lambda trade-off')
        axs[0].legend(fontsize=8,loc='lower right');fig.suptitle(title+': risk versus rescue')
        fig.tight_layout();fig.savefig(folder/(group+'_risk_rescue.svg'));fig.savefig(folder/(group+'_risk_rescue.png'),dpi=220);plt.close(fig)
if __name__=='__main__':run()
