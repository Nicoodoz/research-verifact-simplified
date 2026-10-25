"""Static scientific figures from canonical027 machine tables, no models."""
import csv,json,argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'outputs/027_dual_judge_transfer_diagnosis'
def table(name):
    with (BASE/'analysis_002'/name).open(encoding='utf-8') as f:return list(csv.DictReader(f))
def hull(rows):
    b={}
    for r in rows:
        f,R=float(r['risk']),float(r['R']);b[f]=max(R,b.get(f,-1))
    pts=[];best=-1
    for f,R in sorted(b.items()):
        if R>best:pts.append((f,R));best=R
    hh=[]
    for p in pts:
        while len(hh)>1:
            a,b=hh[-2:]
            if (b[1]-a[1])*(p[0]-b[0])<=(p[1]-b[1])*(b[0]-a[0])+1e-12:hh.pop()
            else:break
        hh.append(p)
    return pts,hh
def run(destination):
    out=Path(destination).resolve();assert not out.exists() and (out.is_relative_to(BASE) or out.is_relative_to(ROOT/'outputs/replays'));out.mkdir(parents=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    cc=table('curves.csv');gg=table('global_curves.csv');colors={'D_margin':'#777777','Q_s':'#40954e','Q_margin':'#93b346','SD':'#167bb0'};labels={'D_margin':'DeepSeek margin','Q_s':'Qwen S score','Q_margin':'Qwen margin','SD':'SD probability'}
    fig,axes=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    for col,(group,total) in enumerate([('025',76),('026',34)]):
        pts,hh=hull([r for r in gg if r['group']==group]);ax=axes[0,col]
        ax.step(*zip(*pts),where='post',color='black',alpha=.35,label='Full global: deterministic');ax.plot(*zip(*hh),'--',color='black',label='Full global: mixture envelope')
        for method in colors:
            rr=[r for r in cc if r['group']==group and r['method']==method];risk=[float(r['risk']) for r in rr];res=[float(r['R']) for r in rr]
            ax.step(risk,res,where='post',color=colors[method],label=labels[method])
            targets=sorted(set(res));needed=[min(f for R,f in zip(res,risk) if R>=t) for t in targets]
            axes[1,col].step(np.array(targets)/total*100,needed,where='pre',color=colors[method],label=labels[method])
        # Same full global envelope projected at the requested rescue, not truncated input.
        h=np.array(hh);rx=np.linspace(.8*total,total,101);fy=np.interp(rx,h[:,1],h[:,0]);axes[1,col].plot(rx/total*100,fy,'--',color='black',label='Full global: mixture')
        ax.set(title=f'{group}: full reference and candidate rankings',xlabel='Additional false-S',ylabel='Rescued true S');ax.grid(alpha=.2)
        axes[1,col].set(title=f'{group}: high-rescue view (diagnostic)',xlabel='Retained original U2 rescue (%)',ylabel='Additional false-S',xlim=(80,100.5));axes[1,col].grid(alpha=.2)
    axes[0,0].legend(fontsize=7,loc='lower right',frameon=False)
    for ext in ('png','svg'):fig.savefig(out/('figure1_rankings.'+ext),dpi=250)
    plt.close(fig)
    data=json.loads((BASE/'analysis_002/candidates.json').read_text(encoding='utf-8'));fig,axes=plt.subplots(2,3,figsize=(10.5,6),sharey=True,constrained_layout=True)
    for i,group in enumerate(('025','026')):
        for j,feature in enumerate(('D_s','Q_s','SD')):
            rs=[r for r in data if r['group']==group];vv=[[r[feature] for r in rs if (r['kind']=='R')==positive] for positive in (True,False)]
            box=axes[i,j].boxplot(vv,positions=[1,2],widths=.45,patch_artist=True,showmeans=True)
            for patch,color in zip(box['boxes'],['#69ad85','#ce857b']):patch.set_facecolor(color);patch.set_alpha(.6)
            axes[i,j].set(xticks=[1,2],xticklabels=['R','H / W'],ylim=(-.03,1.03),title=group+' '+{'D_s':'DeepSeek S score','Q_s':'Qwen S score','SD':'SD probability'}[feature]);axes[i,j].grid(axis='y',alpha=.2)
            if j==0:axes[i,j].set_ylabel('Score / probability')
            if feature=='SD':axes[i,j].axhline(.686248968514202,color='#555555',ls=':',label='026 frozen threshold')
    axes[1,2].legend(fontsize=8,loc='lower right',frameon=False)
    fig.suptitle('025 SD uses patient OOF predictions; 026 uses the frozen final gate',fontsize=11)
    for ext in ('png','svg'):fig.savefig(out/('figure2_distributions.'+ext),dpi=250)
    plt.close(fig)
    (out/'README.md').write_text('# 027 figures\n\nFigure1 retains the complete global frontier through all-S; lower panels only zoom the high-rescue region. Curves are descriptive threshold sweeps, not new operating points. Figure2 shows class-conditional score distributions; 025 pooled OOF probabilities come from different held-out-patient models. Dashed horizontal line is the unchanged026 threshold, not the per-fold025 operating rule.\n',encoding='utf-8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
