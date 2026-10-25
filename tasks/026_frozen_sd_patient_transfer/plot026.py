"""Standalone scientific SVG/PNG, reads frozen machine tables only."""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'outputs/026_frozen_sd_patient_transfer'

def run(destination):
    out=Path(destination).resolve();assert not out.exists() and (out.is_relative_to(BASE) or out.is_relative_to(ROOT/'outputs/replays'));out.mkdir(parents=True)
    with (BASE/'analysis_001/global_frontier.csv').open(encoding='utf-8') as f:rows=[r for r in csv.DictReader(f) if r['scope']=='primary_common' and r['author']=='all']
    byx={}
    for r in rows:
        x,y=int(r['risk']),int(r['R']);byx[x]=max(y,byx.get(x,-1))
    points=[];best=-1
    for x,y in sorted(byx.items()):
        if y>best:points.append((x,y));best=y
    hull=[]
    for x,y in points:
        while len(hull)>1:
            a,b=hull[-2:]
            if (b[1]-a[1])*(x-b[0])<=(y-b[1])*(b[0]-a[0])+1e-12:hull.pop()
            else:break
        hull.append((x,y))
    metrics=json.loads((BASE/'analysis_001/metrics.json').read_text(encoding='utf-8'))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.4),constrained_layout=True)
    for ax in axes:
        ax.step(*zip(*points),where='post',color='#65758b',label='Deterministic global-lambda frontier')
        ax.plot(*zip(*hull),'--',color='#333333',label='Randomized global-lambda envelope')
        for name,color,marker,label in [('U2','#ce7e00','s','Fixed U2'),('SD','#166fa8','o','Frozen SD'),('peer_U2','#4b8d3a','^','Peer-U2')]:
            m=metrics['all/'+name];ax.scatter(m['risk'],m['R'],s=65,c=color,marker=marker,zorder=5,label=label);ax.annotate(f"{label} ({m['risk']}, {m['R']})",(m['risk'],m['R']),xytext=(5,5),textcoords='offset points',fontsize=9)
        ax.set_xlabel('Additional false-S versus U0 (H + W)');ax.set_ylabel('Rescued true Supported (R)');ax.grid(alpha=.18)
    axes[0].set_title('A. Full nonnegative global-lambda reference');axes[0].set_xlim(-2,112);axes[0].set_ylim(0,64)
    axes[1].set_title('B. Candidate-gate operating region');axes[1].set_xlim(0,25);axes[1].set_ylim(0,50)
    axes[0].legend(loc='lower right',fontsize=8,frameon=False)
    fig.savefig(out/'risk_rescue.png',dpi=300);fig.savefig(out/'risk_rescue.svg');plt.close(fig)
    (out/'README.md').write_text('# 026 risk–rescue figure\n\nAll 650 claims. Curves use every nonnegative global-lambda switching state through all-S. Dashed line is an outcome-informed randomized expected envelope, not a selected deployment method. Fixed SD / peer / U2 are unchanged. Right panel only zooms the axes. Source: analysis_001/global_frontier.csv and metrics.json.\n',encoding='utf-8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
