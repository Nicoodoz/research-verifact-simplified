"""Unified classification and paired probability evaluation."""
from collections import Counter
import numpy as np
import common as c

def probability_metrics(y,p,lp):
    q=np.exp(lp);loss=-lp[np.arange(len(y)),y]
    brier=((q-np.eye(3)[y])**2).sum(1);confidence=q.max(1);bins=np.minimum((confidence*10).astype(int),9)
    ece=sum(np.mean(bins==b)*abs(np.mean(p[bins==b]==y[bins==b])-np.mean(confidence[bins==b])) for b in range(10) if np.any(bins==b))
    return dict(NLL=float(loss.mean()),Brier=float(brier.mean()),ECE10=float(ece)),loss,brier

def point(rows,p,lp):
    y=np.array([r['y'] for r in rows]);m=c.evaluate(c.cohort(rows),c.predictions(rows,p),profile='none')
    cm=np.array(m['confusion_matrix']);prob,_,_=probability_metrics(y,p,lp)
    return dict(n=len(rows),correct=int(np.trace(cm)),PA=m['percent_agreement'],MCC=m['mcc'],AC1=m['gwet_ac1'],
      false_S=int(cm[1:,0].sum()),non_S=int(cm[1:].sum()),FSR=float(cm[1:,0].sum()/cm[1:].sum()) if cm[1:].sum() else None,
      **prob,S_recall=m['per_class']['Supported']['recall'],NS_recall=m['per_class']['Not Supported']['recall'],
      NA_recall=m['per_class']['Not Addressed']['recall'],confusion_matrix=cm.tolist(),per_class=m['per_class'])

def paired_extra(rows,base,cand):
    y=np.array([r['y'] for r in rows]);subjects=sorted(set(r['sid'] for r in rows));gi=np.array([subjects.index(r['sid']) for r in rows]);g=len(subjects)
    weights=np.stack([np.bincount(np.random.RandomState(i).choice(g,g),minlength=g) for i in range(1000)])
    size=np.bincount(gi,minlength=g);non=np.bincount(gi,weights=(y!=0),minlength=g);result={}
    _,bl,bb=probability_metrics(y,*base);_,cl,cb=probability_metrics(y,*cand)
    bf=(y!=0)&(base[0]==0);cf=(y!=0)&(cand[0]==0)
    for name,d,den in [('NLL',cl-bl,size),('Brier',cb-bb,size),('FSR',cf.astype(float)-bf,non)]:
        numer=weights@np.bincount(gi,weights=d,minlength=g);denom=weights@den;v=numer[denom>0]/denom[denom>0]
        result[name]=dict(delta=float(d.sum()/den.sum()) if den.sum() else None,ci95=np.quantile(v,[.025,.975]).tolist() if len(v) else None,valid_draws=len(v))
    return result

def analyze(name,rows,outputs,out):
    folder=out/name;folder.mkdir(exist_ok=False);table=[];metrics={};pairs={};patient=[];reliability=[];breakdown=[]
    y=np.array([r['y'] for r in rows]);z,_=c.arrays(rows)
    pair_defs=[('U2_T','U2'),('Joint_NLL','U2'),('Task_T','U2'),('Robust_T','U2'),('Robust_T','Task_T'),('Robust_T','Joint_NLL')]
    for scope in ('all','human','llm'):
        ii=np.array([i for i,r in enumerate(rows) if scope=='all' or r['author']==scope]);rr=[rows[i] for i in ii]
        for method,(p,lp) in outputs.items():
            m=point(rr,p[ii],lp[ii]);metrics[scope+'/'+method]=m
            table.append(dict(dataset=name,scope=scope,method=method,**{k:v for k,v in m.items() if k not in ('confusion_matrix','per_class')}))
        for new,old in pair_defs:
            b=(outputs[old][0][ii],outputs[old][1][ii]);a=(outputs[new][0][ii],outputs[new][1][ii])
            pair=c.paired_compare(c.cohort(rr),c.predictions(rr,b[0]),c.predictions(rr,a[0]),iterations=1000)
            pair['probability_and_risk']=paired_extra(rr,b,a);pairs[scope+'/'+new+'-vs-'+old]=pair
    for sid in sorted(set(r['sid'] for r in rows)):
        ii=np.array([i for i,r in enumerate(rows) if r['sid']==sid]);rr=[rows[i] for i in ii]
        base=point(rr,outputs['U2'][0][ii],outputs['U2'][1][ii])
        for method,(p,lp) in outputs.items():
            m=point(rr,p[ii],lp[ii]);patient.append(dict(dataset=name,sid=sid,method=method,n=len(ii),
              correct=m['correct'],PA=m['PA'],MCC=m['MCC'],NLL=m['NLL'],false_S=m['false_S'],
              delta_correct=m['correct']-base['correct'],delta_false_S=m['false_S']-base['false_S']))
    raw_scores=np.array([r['scores'] for r in rows]);margin=z[:,1:].max(1)-z[:,0]
    masks={'U2_correct':outputs['U2'][0]==y,'U2_wrong':outputs['U2'][0]!=y,
      'true_class_score_zero':raw_scores[np.arange(len(y)),y]==0,'near_U2_boundary':abs(margin-2)<=.25,
      'away_U2_boundary':abs(margin-2)>.25}
    for method,(p,lp) in outputs.items():
        q=np.exp(lp)
        for group,mask in masks.items():
            breakdown.append(dict(dataset=name,method=method,group=group,n=int(mask.sum()),NLL=float(-lp[mask,y[mask]].mean()) if mask.any() else None))
        for cls,label in enumerate(c.LABELS):
            bins=np.minimum((q[:,cls]*10).astype(int),9)
            for b in range(10):
                mask=bins==b
                reliability.append(dict(dataset=name,method=method,label=label,bin=b,n=int(mask.sum()),
                  mean_probability=float(q[mask,cls].mean()) if mask.any() else None,frequency=float((y[mask]==cls).mean()) if mask.any() else None))
    transitions=[];u0=outputs['U0'][0];u2=outputs['U2'][0]
    for method,(p,lp) in outputs.items():
        for i,r in enumerate(rows):
            if p[i]==u2[i]:continue
            transitions.append(dict(id=r['id'],sid=r['sid'],author=r['author'],method=method,GT=c.LABELS[y[i]],U2=c.LABELS[u2[i]],new=c.LABELS[p[i]],
              fix=int(u2[i]!=y[i] and p[i]==y[i]),harm=int(u2[i]==y[i] and p[i]!=y[i]),
              new_false_S=int(y[i]!=0 and u2[i]!=0 and p[i]==0),prevented_false_S=int(y[i]!=0 and u2[i]==0 and p[i]!=0)))
    export=[]
    for i,r in enumerate(rows):
        item=dict(id=r['id'],sid=r['sid'],author=r['author'],fold=r['fold'],GT=c.LABELS[y[i]])
        for m,(p,_) in outputs.items():item[m]=c.LABELS[p[i]]
        export.append(item)
    c.put(folder/'metrics.json',metrics);c.put(folder/'paired.json',pairs)
    c.csvwrite(folder/'metrics.csv',table);c.csvwrite(folder/'patients.csv',patient)
    c.csvwrite(folder/'predictions.csv',export);c.csvwrite(folder/'nll_breakdown.csv',breakdown)
    c.csvwrite(folder/'reliability.csv',reliability)
    if transitions:c.csvwrite(folder/'transitions.csv',transitions)
    np.savez_compressed(folder/'probabilities.npz',ids=np.array([r['id'] for r in rows]),**{m:v[1] for m,v in outputs.items()})
    directions={m:dict(positive=sum(r['delta_correct']>0 for r in patient if r['method']==m),negative=sum(r['delta_correct']<0 for r in patient if r['method']==m),
      equal_patient_PA=float(np.mean([r['PA'] for r in patient if r['method']==m]))) for m in outputs}
    c.put(folder/'patient_directions.json',directions)
    return table
