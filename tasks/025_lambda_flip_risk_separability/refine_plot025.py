"""Render discrete frontier as a staircase, preserving first visual draft."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent
def run():
    s=(TASK/'plot025.py').read_text(encoding='utf-8')
    s=s.replace("OUT/'figures_001'","OUT/'figures_002'")
    s=s.replace("ax.plot(*zip(*gp),color='#333333',lw=1.4,label='Exact global lambda states')","front={x:max(y for xx,y in gp if xx==x) for x,y in gp};front=sorted(front.items())\n            ax.step(*zip(*front),where='post',color='#333333',lw=1.4,label='Deterministic global frontier')")
    s=s.replace("axs[0].plot(*zip(*pts),color=colors[method],alpha=.65,lw=1,label=method+' OOF ranking')","axs[0].step(*zip(*pts),where='post',color=colors[method],alpha=.65,lw=1,label=method+' OOF ranking')")
    s=s.replace("zorder=5)","zorder=5,label='Second-Judge U2 baseline' if method=='peer_U2' else None)")
    s=s.replace("axs[0].legend(fontsize=8,loc='lower right')","axs[0].scatter([],[],color='#666666',label='Nested-CV operating point');axs[0].legend(fontsize=7.3,loc='lower right')")
    with (TASK/'plot025_final.py').open('x',encoding='utf-8',newline='\n') as f:f.write(s)
if __name__=='__main__':run()
