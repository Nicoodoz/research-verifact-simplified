"""Pure-SVG figures for task 035; avoids the broken plotting stack in the research env."""
import csv, html
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/035_lambda_boundary_calibration'
FIG=OUT/'figures_001';FIG.mkdir(exist_ok=True)

def rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def text(x,y,s,size=12,anchor='start',weight='normal'):
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{html.escape(str(s))}</text>'
def svgfile(name,body,w=760,h=480):
    s=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>{body}</svg>'
    (FIG/name).write_text(s,encoding='utf-8')

m=[r for r in rows(OUT/'run_002/main40/metrics.csv') if r['scope']=='all']
by={r['method']:r for r in m}

# Figure 1
W,H=760,480;L,R,T,B=80,30,55,70
xmin,xmax=60,250;ymin,ymax=75,85
sx=lambda v:L+(float(v)-xmin)/(xmax-xmin)*(W-L-R)
sy=lambda v:T+(ymax-float(v))/(ymax-ymin)*(H-T-B)
parts=[text(W/2,28,'Main40 decision operating points',16,'middle','bold'),
       f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="black"/>',
       f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="black"/>']
for v in (80,120,160,200,240):
    x=sx(v);parts += [f'<line x1="{x}" y1="{H-B}" x2="{x}" y2="{H-B+5}" stroke="black"/>',text(x,H-B+22,v,10,'middle')]
for v in (76,78,80,82,84):
    y=sy(v);parts += [f'<line x1="{L-5}" y1="{y}" x2="{L}" y2="{y}" stroke="black"/>',text(L-10,y+4,v,10,'end'),f'<line x1="{L}" y1="{y}" x2="{W-R}" y2="{y}" stroke="#dddddd"/>']
for method in ('U0','U2','Joint_NLL','MCC_T'):
    r=by[method];x=sx(r['false_S']);y=sy(100*float(r['PA']))
    parts += [f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="black" stroke-width="2"/>',text(x+8,y-8,method,11)]
parts += [text((L+W-R)/2,H-18,'False-S count (lower is safer)',12,'middle'),text(18,(T+H-B)/2,'PA (%)',12,'middle')]
svgfile('figure1_decision_tradeoff.svg',''.join(parts),W,H)

# Figure 2
methods=('U0','U2','U2_T','Joint_NLL','MCC_T'); vals=[float(by[x]['NLL']) for x in methods]
W,H=760,480;L,R,T,B=70,25,55,90;maxv=1.5
barw=(W-L-R)/len(methods)*0.55;step=(W-L-R)/len(methods)
parts=[text(W/2,28,'Main40 negative log-likelihood',16,'middle','bold'),
       f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="black"/>',
       f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="black"/>']
for i,(method,v) in enumerate(zip(methods,vals)):
    x=L+step*(i+.5);bh=v/maxv*(H-T-B);y=H-B-bh
    parts += [f'<rect x="{x-barw/2}" y="{y}" width="{barw}" height="{bh}" fill="none" stroke="black" stroke-width="2"/>',
              text(x,H-B+22,method,10,'middle'),text(x,y-6,f'{v:.3f}',10,'middle')]
for v in (0,.3,.6,.9,1.2,1.5):
    y=H-B-v/maxv*(H-T-B);parts += [text(L-8,y+4,f'{v:.1f}',10,'end'),f'<line x1="{L}" y1="{y}" x2="{W-R}" y2="{y}" stroke="#e5e5e5"/>']
parts += [text(18,(T+H-B)/2,'NLL (lower is better)',12,'middle')]
svgfile('figure2_nll.svg',''.join(parts),W,H)

# Figure 3
p=rows(OUT/'parameter_summary.csv');W,H=980,500;L,R,T,B=70,25,55,110
xpos=[L+i*(W-L-R)/(len(p)-1) for i in range(len(p))]
sy3=lambda v:T+(4.2-float(v))/4.2*(H-T-B)
parts=[text(W/2,28,'Lambda selected across patient folds and score sources',16,'middle','bold'),
       f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="black"/>',
       f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="black"/>']
series=[('Task_lambda','Task constrained','circle'),('Robust_lambda','Patient robust','square'),('MCC_lambda','MCC-only exploratory','triangle'),('Joint_NLL_lambda','Joint NLL','cross')]
for key,label,shape in series:
    pts=[(x,sy3(r[key])) for x,r in zip(xpos,p)]
    parts.append('<polyline fill="none" stroke="black" stroke-width="1.5" points="'+' '.join(f'{x},{y}' for x,y in pts)+'"/>')
    for x,y in pts:
        if shape=='circle':parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="white" stroke="black"/>')
        elif shape=='square':parts.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" fill="white" stroke="black"/>')
        elif shape=='triangle':parts.append(f'<polygon points="{x},{y-5} {x-5},{y+4} {x+5},{y+4}" fill="white" stroke="black"/>')
        else:parts.append(f'<path d="M{x-4},{y-4} L{x+4},{y+4} M{x-4},{y+4} L{x+4},{y-4}" stroke="black"/>')
for i,(x,r) in enumerate(zip(xpos,p)):
    lab=f"{r['source'].replace('bridge_','')} F{r['fold']}";parts.append(text(x,H-B+18+(i%2)*12,lab,8,'middle'))
for v in (0,1,2,3,4):
    y=sy3(v);parts += [text(L-8,y+4,v,10,'end'),f'<line x1="{L}" y1="{y}" x2="{W-R}" y2="{y}" stroke="#e5e5e5"/>']
for j,(_,label,shape) in enumerate(series):parts.append(text(L+10+(j%2)*230,45+(j//2)*16,label,10))
parts += [text(20,(T+H-B)/2,'effective lambda',12,'middle')]
svgfile('figure3_lambda_stability.svg',''.join(parts),W,H)
print('035 SVG figures written')
