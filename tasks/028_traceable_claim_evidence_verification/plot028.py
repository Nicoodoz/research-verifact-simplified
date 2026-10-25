"""Fixed operating points against complete frozen reference envelopes."""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'outputs/028_traceable_claim_evidence_verification'
def envelope(rows):
    by={}
    for r in rows:
        f,R=float(r['risk']),float(r['R']);by[f]=max(R,by.get(f,-1))
    pts=[];best=-1
    for p in sorted(by.items()):
        if p[1]>best:pts.append(p);best=p[1]
    hull=[]
    for x,y in pts:
        while len(hull)>1:
            a,b=hull[-2:]
            if (b[1]-a[1])*(x-b[0])<=(y-b[1])*(b[0]-a[0])+1e-12:hull.pop()
            else:break
        hull.append((x,y))
    return hull
def run(destination):
    out=Path(destination).resolve();assert not out.exists() and (out.is_relative_to(BASE) or out.is_relative_to(ROOT/'outputs/replays'));out.mkdir(parents=True)
    with (BASE/'analysis_001/curves.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
    metrics=json.loads((BASE/'analysis_001/metrics.json').read_text(encoding='utf-8'));plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(12,4.5),constrained_layout=True)
    for ax,g in zip(axes,('025','026','pooled')):
        for ref,color,label in [('global_lambda','#222222','Full global-lambda mixture'),('SD','#327cb0','SD curve + original point'),('repeat','#77936e','Repeat / U0 / U2 mixture')]:
            hh=envelope([r for r in rows if r['group']==g and r['reference']==ref]);ax.plot(*zip(*hh),ls='--',color=color,label=label)
        for method,color,marker in [('SD','#327cb0','s'),('repeat','#77936e','^'),('trace','#c44338','o')]:
            m=metrics[g+'/all/'+method];ax.scatter(m['risk'],m['R'],color=color,marker=marker,s=65,zorder=5);ax.annotate(f"{method} ({m['risk']},{m['R']})",(m['risk'],m['R']),xytext=(4,5),textcoords='offset points',fontsize=8)
        u2=metrics[g+'/all/U2'];ax.set(xlim=(-.7,u2['risk']+3),ylim=(0,u2['R']*1.1),xlabel='Additional false-S (H+W)',ylabel='Rescued true S (R)',title=g+' candidate operating region');ax.grid(alpha=.2)
    axes[0].legend(loc='lower right',fontsize=7,frameon=False)
    fig.savefig(out/'risk_rescue.png',dpi=270);fig.savefig(out/'risk_rescue.svg');plt.close(fig)
    (out/'README.md').write_text('# 028 risk–rescue\n\nAll envelopes are computed from full frozen reference states. Axes zoom the candidate operating region; the global input is not limited to lambda2 or candidates. Points are unchanged operating rules, not selected thresholds. Mixture curves are descriptive GT-informed expected references.\n',encoding='utf-8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
