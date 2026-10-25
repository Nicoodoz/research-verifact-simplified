"""Evaluate frozen 037 predictions. No fitting or selection occurs here."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score
import core037 as c
PAIRS=list(c.PRIMARY_PAIRS)+[('VM_switch','Std_V'),('Ratio_restore','Std_V'),
    ('Logistic_restore','Std_V'),('VM_switch','Std_M'),('Ratio_restore','Std_M'),
    ('Logistic_restore','Std_M')]
def point(rows,p,lp):
    m=c.evaluate(c.old.cohort(rows),c.old.predictions(rows,p),profile='research_patient',iterations=1000)
    y=np.array([r['y'] for r in rows]);d=c.brief(y,p)
    d.update(n=len(rows),**c.probability_point(y,lp))
    for label,name in zip(c.LABELS,('S','NS','NA')):
        pc=m['per_class'][label]
        for metric in ('recall','precision','f1'):
            d[name+'_'+metric]=pc[metric]
    d['nonS_mean_recall']=(d['NS_recall']+d['NA_recall'])/2
    return d,m

def paired_extra(rows,base,cand):
    y=np.array([r['y'] for r in rows]);sids=sorted({r['sid'] for r in rows});pcs=[]
    for p in (base,cand):
        pcs.append(np.array([c.cm(y[ii],p[ii]) for s in sids
            for ii in [[i for i,r in enumerate(rows) if r['sid']==s]]]))
    draws=[np.random.RandomState(seed).choice(len(sids),len(sids),replace=True) for seed in range(1000)]
    b,a=[np.array([m[t].sum(0) for t in draws]) for m in pcs]
    bm,am=c.metrics_from_confusions(b),c.metrics_from_confusions(a);result={}
    for j,name in enumerate(('PA','AC1','MCC')):
        v=am[:,j]-bm[:,j]
        result[name]=dict(ci97_5=np.quantile(v,[.0125,.9875]).tolist())
    for index,name in ((1,'NS_recall'),(2,'NA_recall')):
        den=b[:,index,:].sum(1);valid=den>0
        diff=(a[:,index,index]-b[:,index,index])[valid]/den[valid]
        cb,ca=c.cm(y,base),c.cm(y,cand)
        result[name]=dict(delta=float((ca[index,index]-cb[index,index])/cb[index].sum()),
            ci95=np.quantile(diff,[.025,.975]).tolist(),valid_draws=int(valid.sum()))
    return result

def transition(rows,base,cand):
    y=np.array([r['y'] for r in rows]);changed=base!=cand
    assert np.all((base[changed]==2)&(cand[changed]==1))
    return dict(changed=int(changed.sum()),NS_rescued=int(np.sum(changed&(y==1))),
        NA_harmed=int(np.sum(changed&(y==2))),S_wrong_still_wrong=int(np.sum(changed&(y==0))),
        delta_correct=int(np.sum(cand==y)-np.sum(base==y)),
        delta_false_S=int(np.sum((cand==0)&(y!=0))-np.sum((base==0)&(y!=0))))

def score_curves(rows,v,score,kind):
    y=np.array([r['y'] for r in rows]);mask=v==2
    ts=np.unique(np.r_[0.,.5 if kind=='ratio' else np.nextafter(1.,np.inf),score[mask]])
    if kind=='ratio':ts=ts[(ts>=0)&(ts<=.5)]
    out=[]
    for t in ts:
        p=c.restore(v,score,float(t));d=c.brief(y,p)
        d.update(threshold=float(t),NS_recall=d['NS_tp']/int(np.sum(y==1)),NA_recall=d['NA_tp']/int(np.sum(y==2)))
        out.append(d)
    return out

def envelope(curve,target):
    """GT-informed descriptive expected NA envelope, never used for fitting."""
    points={}
    for r in curve:points[r['NS_tp']]=max(points.get(r['NS_tp'],-1),r['NA_tp'])
    xy=sorted(points.items());best=None
    for x,y in xy:
        if x==target:best=max(y,best if best is not None else -1)
    for i,(x0,y0) in enumerate(xy):
        for x1,y1 in xy[i+1:]:
            if x0<=target<=x1:
                val=y0+(y1-y0)*(target-x0)/(x1-x0)
                best=max(val,best if best is not None else -1)
    return best

def diagnose(rows,outputs,aux,folder):
    y=np.array([r['y'] for r in rows]);v=outputs['Std_V'];z,_=c.arrays(rows)
    curves={k:score_curves(rows,v,aux[k],k) for k in ('ratio','lr')}
    for k,rs in curves.items():c.writecsv(folder/('descriptive_'+k+'_curve.csv'),rs)
    rankings=[]
    for area,mask in [('V_NA_only',(v==2)&(y!=0)),('V_nonS',(v!=0)&(y!=0))]:
        yy=(y[mask]==1).astype(int)
        for name in ('ratio','lr'):
            ss=aux[name][mask]
            rankings.append(dict(area=area,score=name,n=int(mask.sum()),true_NS=int(yy.sum()),true_NA=int(len(yy)-yy.sum()),
                AUC=float(roc_auc_score(yy,ss)) if len(set(yy.tolist()))==2 else None,AP=float(average_precision_score(yy,ss)) if yy.sum() else None))
    c.writecsv(folder/'ranking.csv',rankings);matched=[]
    for method in c.REPAIRS:
        b=c.brief(y,outputs[method]);ref=envelope(curves['ratio'],b['NS_tp'])
        matched.append(dict(method=method,NS_tp=b['NS_tp'],NA_tp=b['NA_tp'],ratio_expected_NA_at_same_NS=ref,
            delta_NA_vs_GT_informed_ratio_envelope=None if ref is None else b['NA_tp']-ref,
            interpretation='GT-informed diagnostic; not deployable or used for tuning'))
    c.writecsv(folder/'matched_NS_diagnostic.csv',matched)
    groups=defaultdict(list)
    for i,r in enumerate(rows):
        if v[i]==2:groups[(r['fold'],*r['scores'])].append(i)
    conflict=[];oracle_delta=0
    for key,ii in groups.items():
        counts=np.bincount(y[ii],minlength=3)
        oracle_delta+=max(0,int(counts[1]-counts[2]))
        if counts[1] and counts[2]:
            conflict.append(dict(fold=int(key[0]),scores=list(key[1:]),n=len(ii),true_S=int(counts[0]),
                true_NS=int(counts[1]),true_NA=int(counts[2]),ids=[rows[i]['id'] for i in ii]))
    d=dict(V_nonS_NS_recall_ceiling=float(np.sum((v!=0)&(y==1))/np.sum(y==1)),
        V_false_S_unhandled=int(np.sum((v==0)&(y!=0))),V_NA_score_cells=len(groups),mixed_NS_NA_cells=len(conflict),
        mixed_cells_rows=sum(r['n'] for r in conflict),identical_score_oracle_delta_correct=oracle_delta,
        oracle_interpretation='GT-informed impossible deployment bound for NA-to-NS choices at identical score cells',conflicts=conflict)
    c.put(folder/'score_conflicts.json',d)
    return dict(ranking=rankings,matched=matched,conflicts=d)

def analyze(name,rows,outputs,probs,aux,out):
    folder=out/name;folder.mkdir()
    metrics={};table=[];pairs={};patient=[];directions=[];swaps=[]
    for scope in ('all','human','llm'):
        ii=np.array([i for i,r in enumerate(rows) if scope=='all' or r['author']==scope]);rr=[rows[i] for i in ii]
        for method in c.METHODS:
            d,m=point(rr,outputs[method][ii],probs[method][ii]);metrics[scope+'/'+method]=m
            table.append(dict(dataset=name,scope=scope,method=method,**d,
                probability_source='Std_V unchanged' if method in c.REPAIRS else method))
        for new,old in PAIRS:
            b=outputs[old][ii];a=outputs[new][ii]
            p=c.paired_compare(c.old.cohort(rr),c.old.predictions(rr,b),c.old.predictions(rr,a),iterations=1000)
            p['extra']=paired_extra(rr,b,a);p['primary_pair']=(new,old) in c.PRIMARY_PAIRS
            pairs[scope+'/'+new+'-vs-'+old]=p
        for method in c.REPAIRS:
            swaps.append(dict(dataset=name,scope=scope,method=method,**transition(rr,outputs['Std_V'][ii],outputs[method][ii])))
    y=np.array([r['y'] for r in rows]);sidlist=sorted({r['sid'] for r in rows})
    for sid in sidlist:
        ii=np.array([i for i,r in enumerate(rows) if r['sid']==sid])
        for method in c.METHODS:
            d=c.brief(y[ii],outputs[method][ii]);mat=c.cm(y[ii],outputs[method][ii])
            patient.append(dict(sid=sid,method=method,n=len(ii),**d,NS_n=int(mat[1].sum()),NA_n=int(mat[2].sum()),
                NS_recall=float(mat[1,1]/mat[1].sum()) if mat[1].sum() else None,
                NA_recall=float(mat[2,2]/mat[2].sum()) if mat[2].sum() else None))
    for new,old in PAIRS:
        delta=[];pa=[]
        for sid in sidlist:
            aa=next(r for r in patient if r['sid']==sid and r['method']==new)
            bb=next(r for r in patient if r['sid']==sid and r['method']==old)
            delta.append(aa['correct']-bb['correct']);pa.append(aa['PA']-bb['PA'])
        total=sum(delta)
        directions.append(dict(pair=new+'-vs-'+old,positive=sum(x>0 for x in delta),negative=sum(x<0 for x in delta),
            tied=sum(x==0 for x in delta),delta_correct=total,patient_equal_delta_PA=float(np.mean(pa)),
            leave_one_out_delta_correct=[total-max(delta),total-min(delta)]))
    records=[]
    for i,r in enumerate(rows):
        records.append(dict(id=r['id'],sid=r['sid'],author=r['author'],fold=r['fold'],GT=c.LABELS[r['y']],
            **{m:c.LABELS[int(outputs[m][i])] for m in c.METHODS},ratio_score=float(aux['ratio'][i]),lr_score=float(aux['lr'][i])))
    c.writecsv(folder/'predictions.csv',records)
    c.put(folder/'metrics.json',metrics);c.writecsv(folder/'metrics.csv',table)
    c.put(folder/'paired.json',pairs);c.writecsv(folder/'patients.csv',patient)
    c.put(folder/'directions.json',directions);c.writecsv(folder/'transitions.csv',swaps)
    diagnostics=diagnose(rows,outputs,aux,folder)
    return dict(table=table,pairs=pairs,directions=directions,transitions=swaps,diagnostics=diagnostics)
