"""Official point metrics plus patient-cluster bootstrap from sufficient counts."""
import sys
from collections import Counter
import numpy as np
import common095 as c
sys.path.insert(0,str(c.ROOT/'tasks/092_task_adapted_verifier'))
from analyze092 import table
from verifact_research.evaluation import paired_compare
LABELS=['Supported','Not Supported','Not Addressed']

def score(rows,models):return table(rows,models) if rows else None

def cm_metrics(cm):
    cm=np.asarray(cm,dtype=float);n=cm.sum(axis=(-2,-1));r=cm.sum(-1);s=cm.sum(-2);d=np.diagonal(cm,axis1=-2,axis2=-1);correct=d.sum(-1)
    div=lambda a,b:np.divide(a,b,out=np.zeros_like(a,dtype=float),where=b!=0)
    den=np.sqrt(np.maximum(0,(n*n-(s*s).sum(-1))*(n*n-(r*r).sum(-1))))
    return np.stack([div(correct,n),div(correct*n-(r*s).sum(-1),den),div(2*d,r+s).mean(-1)],axis=-1)

def paired(rows,base,candidate,repeats=1000):
    if not rows:return None
    sids=sorted({r['sid'] for r in rows});si={s:i for i,s in enumerate(sids)};a=np.zeros((len(sids),3,3),dtype=int);b=a.copy();patients={s:dict(rescue=0,harm=0) for s in sids};resc=Counter();harm=Counter();added=prevented=0
    for r in rows:
        g,x,y=(LABELS.index(z) for z in [r['GT'],r['predictions'][base],r['predictions'][candidate]])
        a[si[r['sid']],g,x]+=1;b[si[r['sid']],g,y]+=1
        if x!=g and y==g:resc[r['GT']]+=1;patients[r['sid']]['rescue']+=1
        if x==g and y!=g:harm[r['GT']]+=1;patients[r['sid']]['harm']+=1
        added+=g!=0 and x!=0 and y==0;prevented+=g!=0 and x==0 and y!=0
    rng=np.random.RandomState(95095);ix=rng.randint(0,len(sids),size=(repeats,len(sids)));diff=cm_metrics(b[ix].sum(1))-cm_metrics(a[ix].sum(1));nets={s:d['rescue']-d['harm'] for s,d in patients.items()};point=cm_metrics(b.sum(0))-cm_metrics(a.sum(0))
    official=paired_compare([dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rows],[dict(proposition_id=r['id'],verdict=r['predictions'][base]) for r in rows],[dict(proposition_id=r['id'],verdict=r['predictions'][candidate]) for r in rows],iterations=repeats)
    for i,key in [(0,'percent_agreement'),(1,'mcc')]:assert abs(float(point[i])-official['metrics'][key]['delta'])<1e-10
    supplemental={k:np.quantile(diff[:,i],[.025,.975]).tolist() for i,k in enumerate(['PA','MCC','Macro_F1'])}
    ci=dict(PA=official['metrics']['percent_agreement']['ci95'],MCC=official['metrics']['mcc']['ci95'],Macro_F1=supplemental['Macro_F1'])
    return dict(base=base,candidate=candidate,N=len(rows),patients=len(sids),rescue=sum(resc.values()),harm=sum(harm.values()),net=sum(resc.values())-sum(harm.values()),rescue_by_GT={x:resc[x] for x in LABELS},harm_by_GT={x:harm[x] for x in LABELS},false_S_added=int(added),false_S_prevented=int(prevented),patient_net=nets,patient_details=patients,patient_win_loss_tie=[sum(v>0 for v in nets.values()),sum(v<0 for v in nets.values()),sum(v==0 for v in nets.values())],rescue_patients=sum(v['rescue']>0 for v in patients.values()),delta={k:float(point[i]) for i,k in enumerate(['PA','MCC','Macro_F1'])},CI95=ci,official_paired_compare=official,supplemental_cluster_CI95=supplemental,bootstrap_repeats=repeats,bootstrap_scope='Primary PA/MCC intervals use repository paired_compare; supplementary Macro-F1 uses aggregated patient counts. Fixed predictions only; no adaptive development or service randomness covered.')

def strata(rows,field,models):return {str(v):score([r for r in rows if r[field]==v],models) for v in sorted({r[field] for r in rows},key=str)}

def transition(rows,base,new):
    cc=Counter((r['GT'],r['predictions'][base],r['predictions'][new]) for r in rows)
    return [dict(GT=g,base=x,candidate=y,N=n) for (g,x,y),n in sorted(cc.items())]
