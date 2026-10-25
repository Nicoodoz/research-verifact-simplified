"""Paper-ready vector/PNG figures, from frozen statistical tables only."""
from pathlib import Path
import argparse,csv,hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator,PercentFormatter

ROOT=Path(__file__).resolve().parents[2];DEFAULT=ROOT/'outputs/023_lambda_boundary_response_analysis'
COLORS={'PA':'#0072B2','MCC':'#6A3D9A','S_recall':'#0072B2','NS_recall':'#D55E00','NA_recall':'#009E73','false_S_rate':'#CC3366'}
GROUPS=['019','020_R0','020_R1'];TITLES=['019 discovery (n = 650)','020 R0 (n = 879)','020 R1 (n = 879)']

def readrows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def setup(ax):
    ax.set_xlim(0,4);ax.xaxis.set_major_locator(MultipleLocator(1));ax.grid(axis='y',color='#DADDE0',linewidth=.5);ax.set_axisbelow(True)
    ax.axvline(2,color='#333333',ls=(0,(3,2)),lw=1,zorder=2)
    ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
def curve(exact,group,author,key):
    rr=[r for r in exact if r['group']==group and r['author']==author]
    x=np.array([float(r['lambda_value']) for r in rr]);y=np.array([float(r[key]) if r[key] else np.nan for r in rr])
    if key.endswith('_recall'):
        gt=key.split('_')[0]+'_GT';y=np.array([v if int(r[gt]) else np.nan for r,v in zip(rr,y)])
    return x,y
def export(fig,out,name):
    fig.savefig(out/(name+'.pdf'),metadata={'CreationDate':None,'ModDate':None,'Title':name,'Subject':'Frozen score response analysis; no parameter selection'})
    fig.savefig(out/(name+'.svg'),metadata={'Date':None,'Title':name})
    fig.savefig(out/(name+'.png'),dpi=400)
    plt.close(fig)

def run(data,out):
    if out.exists():raise ValueError('Figures directory already exists')
    out.mkdir(parents=True)
    exact=readrows(data/'exact_states.csv');dense=readrows(data/'dense_grid.csv')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.linewidth':.7,'lines.linewidth':1.6,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'verifact-023-v1','savefig.facecolor':'white'})
    fig,axs=plt.subplots(2,3,figsize=(7.5,4.8),sharex=True,sharey='row')
    for j,(group,title) in enumerate(zip(GROUPS,TITLES)):
        for i,key in enumerate(('PA','MCC')):
            ax=axs[i,j];setup(ax);x,y=curve(exact,group,'all',key);ax.step(x,y,where='post',color=COLORS[key])
            point=next(r for r in dense if r['group']==group and r['author']=='all' and float(r['lambda_value'])==2)
            ax.plot(2,float(point[key]),'o',ms=4,color=COLORS[key],markeredgecolor='white',markeredgewidth=.6,zorder=4)
            if group=='019':
                marks=[r for r in dense if r['group']==group and r['author']=='all' and float(r['lambda_value']) in (0,.5,1,1.5,2,3,4)]
                ax.scatter([float(r['lambda_value']) for r in marks],[float(r[key]) for r in marks],s=16,facecolors='white',edgecolors=COLORS[key],lw=.8,zorder=3)
            if i==0:ax.set_title(title)
            if i==1:ax.set_xlabel(r'Supported bias $\lambda$')
            if j==0:ax.set_ylabel('PA (%)' if key=='PA' else 'MCC')
            if key=='PA':ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    for i,key in enumerate(('PA','MCC')):
        vals=[float(r[key]) for r in exact if r['group'] in GROUPS and r['author']=='all'];pad=.015 if key=='PA' else .01
        axs[i,0].set_ylim(min(vals)-pad,max(vals)+pad)
    fig.suptitle('Figure 1. Performance response to Supported bias',fontsize=11,y=.98)
    fig.text(.5,.018,r'Exact steps; dashed line: fixed $\lambda=2$. Open circles: original 019 anchor points.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.047,1,.94),h_pad=1.3,w_pad=1.1);export(fig,out,'figure1_performance')

    fig,axs=plt.subplots(1,3,figsize=(7.5,3.35),sharex=True,sharey=True)
    legend=[]
    for j,(group,title) in enumerate(zip(GROUPS,TITLES)):
        ax=axs[j];setup(ax);ax.set_title(title);ax.set_xlabel(r'Supported bias $\lambda$');ax.set_ylim(0,1.02);ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
        for key,label in [('S_recall','S recall'),('NS_recall','NS recall'),('NA_recall','NA recall'),('false_S_rate','False-S rate')]:
            x,y=curve(exact,group,'all',key);line,=ax.step(x,y,where='post',color=COLORS[key],ls='--' if key=='false_S_rate' else '-',label=label)
            if j==0:legend.append(line)
        if j==0:ax.set_ylabel('Recall / error rate (%)')
    fig.suptitle('Figure 2. Supported benefit and non-S cost',fontsize=11,y=.99)
    fig.legend(handles=legend,loc='upper center',bbox_to_anchor=(.5,.91),ncol=4,frameon=False,columnspacing=1.6)
    fig.text(.5,.018,r'False-S rate denominator: ground-truth NS + NA. Dashed vertical line: fixed $\lambda=2$.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,.82),w_pad=1.1);export(fig,out,'figure2_tradeoff')

    fig,axs=plt.subplots(2,3,figsize=(7.5,4.8),sharex=True,sharey='row')
    for i,author in enumerate(('human','llm')):
        for j,(group,title) in enumerate(zip(GROUPS,TITLES)):
            ax=axs[i,j];setup(ax);x,y=curve(exact,group,author,'MCC');ax.step(x,y,where='post',color='#0072B2' if author=='human' else '#D55E00')
            ax.axhline(0,color='#777777',lw=.7,ls=':')
            if i==0:ax.set_title(title)
            if j==0:ax.set_ylabel(('Human-written' if author=='human' else 'LLM-written')+'\nMCC')
            if i==1:ax.set_xlabel(r'Supported bias $\lambda$')
        vals=[float(r['MCC']) for r in exact if r['group'] in GROUPS and r['author']==author];axs[i,0].set_ylim(min(0,min(vals))-.03,max(vals)+.03)
    fig.suptitle('Figure S1. Author subgroup response',fontsize=11,y=.98)
    fig.text(.5,.015,r'LLM-written 020: 263 / 269 claims are S. Dotted horizontal line: Always-S MCC = 0.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,.94),h_pad=1.3,w_pad=1.1);export(fig,out,'figureS1_author_MCC')
    metadata=dict(matplotlib=matplotlib.__version__,numpy=np.__version__,data_hashes={p.name:hashfile(p) for p in (data/'exact_states.csv',data/'dense_grid.csv')},files={p.name:hashfile(p) for p in out.iterdir() if p.is_file()},styles='exact post steps; no smoothing; per-metric common y axes; PDFs embed TrueType; SVG text retained',fixed_lambda=2,new_API_calls=0)
    (out/'manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(figures=3,formats=['PDF','SVG','PNG'],matplotlib=matplotlib.__version__,data=str(data)),ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=DEFAULT/'analysis_001');p.add_argument('--output',type=Path,default=DEFAULT/'figures_001');a=p.parse_args();run(a.data,a.output)
