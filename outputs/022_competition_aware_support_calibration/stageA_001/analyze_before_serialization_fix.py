"""Frozen grouped OOF calibration screen; stageA never imports API clients."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse
import numpy as np
from scipy.special import softmax,logsumexp
import common022 as c
import calibration022 as k

def classify(rows,p):
    return c.evaluate(rows,c.prediction(rows,p),profile='none')

def counts(rows,p):
    y=np.array([c.LABELS.index(r['human_gt']) for r in rows]);p=np.asarray(p)
    return dict(correct=int(sum(y==p)),false_S=int(sum((y!=0)&(p==0))),NS_to_S=int(sum((y==1)&(p==0))),NA_to_S=int(sum((y==2)&(p==0))),NS_correct=int(sum((y==1)&(p==1))),NA_correct=int(sum((y==2)&(p==2))),S_correct=int(sum((y==0)&(p==0))),nonS=int(sum(y!=0)),NS=int(sum(y==1)))

def summary_point(rows,p):
    m=classify(rows,p);return dict(PA=m['percent_agreement'],MCC=m['mcc'],**counts(rows,p))

def quality(y,v):
    q=softmax(v,axis=1);n=len(y);one=np.eye(3)[y];bins=[]
    for cls in ('top',0,1,2):
        confidence=q.max(1) if cls=='top' else q[:,cls]
        truth=(k.labels(v)==y).astype(int) if cls=='top' else (y==cls).astype(int)
        indices=np.minimum((confidence*10).astype(int),9)
        for j in range(10):
            ix=indices==j
            bins.append(dict(class_name='top' if cls=='top' else c.LABELS[cls],bin=j,n=int(sum(ix)),mean_probability=float(confidence[ix].mean()) if ix.any() else None,observed_rate=float(truth[ix].mean()) if ix.any() else None))
    ece=sum(b['n']/n*abs(b['mean_probability']-b['observed_rate']) for b in bins if b['class_name']=='top' and b['n'])
    return dict(NLL=float(np.mean(logsumexp(v,axis=1)-v[np.arange(n),y])),Brier=float(np.mean(np.sum((q-one)**2,axis=1))),ECE=ece),bins

def gate(points,patients,leave):
    def core(a,b):return a['MCC']>b['MCC'] and a['PA']>=b['PA']-.01-1e-12 and a['false_S']<=b['false_S'] and a['NS_correct']>=b['NS_correct'] and a['NS_to_S']<b['NS_to_S']
    checks={}
    for scope in ('R0','R1'):
        checks[scope+'_vs_U2']=core(points[scope]['C'],points[scope]['U2'])
        a=points[scope]['C'];g=points[scope]['G']
        checks[scope+'_vs_G']=a['MCC']>g['MCC'] and a['PA']>=g['PA']-.01-1e-12 and a['false_S']<=g['false_S']
        for alt in ('M','V'):
            b=points[scope][alt]
            checks[scope+'_not_dominated_by_'+alt]=not (b['PA']>=a['PA'] and b['MCC']>=a['MCC'] and b['false_S']<=a['false_S'])
    a=points['R0']['C'];g=points['R0']['G']
    checks['R0_practical_vs_G']=(a['correct']>=g['correct']+3 and a['false_S']<=g['false_S']) or (a['false_S']<=g['false_S']-3 and a['PA']>=g['PA']-.005-1e-12)
    checks['patient_spread']=sum(p['correct_delta']>=0 for p in patients if p['scope']=='R0' and p['method']=='C')>=8
    checks['leave_one_patient_MCC']=all(v['MCC_delta']>=0 for v in leave)
    return dict(checks=checks,pass_to_stageB=all(checks.values()),stageB_executed=False,optional_Qwen_executed=False,new_API_calls=0,cost_cny=0)

def run(out):
    c.require(not out.exists(),'Refuse overwrite');c.check(c.OUT/'preparation_001')
    rows=c.jl(c.OUT/'preparation_001/rows.jsonl');z=k.scores_to_z([r['scores'] for r in rows]);y=np.array([c.LABELS.index(r['human_gt']) for r in rows]);n=len(rows)
    logits={a:np.full_like(z,np.nan) for a in c.LEARNED};fits=[]
    for fold in range(4):
        train,test=k.split_indices(rows,fold)
        for kind in c.LEARNED:
            result=k.fit(z[train],y[train],kind);logits[kind][test]=k.transform(z[test],kind,result['theta'])
            fits.append(dict(fold=fold,method=kind,train_patients=sorted({rows[i]['subject_id'] for i in train}),test_patients=sorted({rows[i]['subject_id'] for i in test}),train_claims=len(train),train_scoring_ids=[rows[i]['scoring_request_id'] for i in train],**result))
        print('Fitted fold',fold,flush=True)
    logits.update(U0=z.copy(),U2=k.transform(z,'U2'));c.require(all(np.isfinite(v).all() for v in logits.values()),'Incomplete OOF')
    pred={a:k.labels(v) for a,v in logits.items()};pred.update(B=np.array([c.LABELS.index(r['B']) for r in rows]),V_raw=np.array([c.LABELS.index(r['V_raw']) for r in rows]),Always_S=np.zeros(n,dtype=int))
    out.mkdir(parents=True);c.write(out/'fitted_parameters.json',fits)
    oof=[]
    for i,r in enumerate(rows):
        for a in c.METHODS:
            oof.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],GT=r['human_gt'],source=r['source'],repeat=r['repeat'],fold=r['fold'],method=a,verdict=c.LABELS[pred[a][i]],score_request_id=r['scoring_request_id'] if a not in ('B','Always_S') else None,baseline_request_id=r['baseline_request_id'] if a=='B' else None,probabilities=softmax(logits[a][i]).tolist() if a in logits else None,raw_final_mismatch=pred[a][i]!=pred['V_raw'][i]))
    c.lines(out/'oof_predictions.jsonl',oof)
    metrics={};paired={};core=[];prob=[];reliability=[];patients=[];transitions=[];points={};leave=[]
    scopes={'R0':[i for i,r in enumerate(rows) if r['repeat']==0],'R1':[i for i,r in enumerate(rows) if r['repeat']==1],'R0_020':[i for i,r in enumerate(rows) if r['repeat']==0 and r['source']=='020']}
    for scope,ix in scopes.items():
        sr=[rows[i] for i in ix];points[scope]={a:summary_point(sr,p[ix]) for a,p in pred.items()}
        for author in ('all','llm','human'):
            sel=[i for i in ix if author=='all' or rows[i]['author_type']==author];rr=[rows[i] for i in sel]
            for a,p in pred.items():
                key=f'{scope}/{author}/{a}';m=c.evaluate(rr,c.prediction(rr,p[sel]),iterations=1000,missing='error');metrics[key]=m
                core.append(dict(scope=scope,author=author,method=a,n=len(rr),PA=m['percent_agreement'],AC1=m['gwet_ac1'],MCC=m['mcc'],**counts(rr,p[sel])))
                if a in logits:
                    qs,bs=quality(y[sel],logits[a][sel]);prob.append(dict(scope=scope,author=author,method=a,n=len(sel),**qs));reliability.extend(dict(scope=scope,author=author,method=a,**b) for b in bs)
            for a,b in [('C','U2'),('C','G'),('C','M'),('C','V'),('G','U2'),('M','U2'),('V','U2'),('U2','B')]:
                paired[f'{scope}/{author}/{a}-minus-{b}']=c.paired_compare(rr,c.prediction(rr,pred[b][sel]),c.prediction(rr,pred[a][sel]),iterations=1000)
        for sid in sorted({r['subject_id'] for r in sr}):
            sel=[i for i in ix if rows[i]['subject_id']==sid];rr=[rows[i] for i in sel];base=summary_point(rr,pred['U2'][sel])
            for a,p in pred.items():
                v=summary_point(rr,p[sel]);patients.append(dict(scope=scope,subject_id=sid,method=a,n=len(rr),correct_delta=v['correct']-base['correct'],false_S_delta=v['false_S']-base['false_S'],**v))
            if scope=='R0':
                sel=[i for i in ix if rows[i]['subject_id']!=sid];rr=[rows[i] for i in sel];ca=summary_point(rr,pred['C'][sel]);b=summary_point(rr,pred['U2'][sel]);leave.append(dict(excluded_patient=sid,MCC_delta=ca['MCC']-b['MCC'],PA_delta=ca['PA']-b['PA']))
        for a,p in pred.items():
            for i in ix:
                b=pred['U2'][i];v=p[i];g=y[i];transitions.append(dict(scope=scope,proposition_id=rows[i]['proposition_id'],subject_id=rows[i]['subject_id'],author_type=rows[i]['author_type'],GT=c.LABELS[g],method=a,U2=c.LABELS[b],final=c.LABELS[v],rescue=bool(b!=g and v==g),harm=bool(b==g and v!=g),W_new_false_S=bool(g!=0 and b!=g and b!=0 and v==0),new_false_S=bool(g!=0 and b!=0 and v==0),removed_false_S=bool(g!=0 and b==0 and v!=0)))
        print('Scored',scope,flush=True)
    for name,obj in [('metrics',metrics),('paired',paired),('decision',gate(points,patients,leave))]:c.write(out/(name+'.json'),obj)
    for name,data in [('core_results',core),('probability',prob),('reliability',reliability),('patients',patients),('transitions',transitions),('leave_one_patient',leave)]:c.csvwrite(out/(name+'.csv'),data)
    # R0 andR1 on exactly the same879 claims; fit parameters fixed from other patients' R0.
    first={r['proposition_id']:i for i,r in enumerate(rows) if r['repeat']==0};stability=[]
    for j,r in enumerate(rows):
        if r['repeat']!=1:continue
        i=first[r['proposition_id']]
        for a,p in pred.items():stability.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],method=a,flip=bool(p[i]!=p[j]),stable_rescue=bool(p[i]==y[i] and p[j]==y[j] and pred['U2'][i]!=y[i] and pred['U2'][j]!=y[j]),stable_harm=bool(p[i]!=y[i] and p[j]!=y[j] and pred['U2'][i]==y[i] and pred['U2'][j]==y[j])))
    c.csvwrite(out/'stability.csv',stability)
    diag=[]
    for i,r in enumerate(rows):
        mix=float(softmax(z[i,1:])[0]);margin=float(z[i,0]-max(z[i,1:]));u0=pred['U0'][i];u2=pred['U2'][i];gt=y[i]
        event='unchanged' if u0==u2 else 'R' if gt==0 else 'H' if u0==gt else 'W'
        diag.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],source=r['source'],repeat=r['repeat'],GT=r['human_gt'],r_NS=mix,S_margin=margin,r_bin=min(int(mix*4),3),margin_bin=int(np.digitize(margin,[-4,-2,0,2])),U0=c.LABELS[u0],U2=c.LABELS[u2],event=event))
    c.csvwrite(out/'competition_diagnostic.csv',diag)
    grouped=defaultdict(Counter)
    for d in diag:
        for dim,val in [('all','all'),('author',d['author_type']),('patient',d['subject_id'])]:grouped[(d['repeat'],dim,val,d['r_bin'],d['margin_bin'],d['U0'])][d['event']]+=1
    c.csvwrite(out/'competition_bins.csv',[dict(repeat=key[0],dimension=key[1],value=key[2],r_bin=key[3],margin_bin=key[4],U0=key[5],**{e:counts[e] for e in ('R','H','W','unchanged')},n=sum(counts.values())) for key,counts in sorted(grouped.items())])
    c.write(out/'budget.json',dict(cap_cny=80,new_calls=0,known_cost_cny=0,unknown_reservation_cny=0,attempts=[],stage='historical_offline_A'))
    c.seal(out,[c.OUT/'preparation_001/manifest.json',c.OUT/'protocol_001.md'],[Path(__file__),c.TASK/'common022.py',c.TASK/'calibration022.py'])
    print(c.canonical(dict(results={scope:{a:p for a,p in v.items() if a in ('U2','C','G','M','V')} for scope,v in points.items()},decision=c.read(out/'decision.json'))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'stageA_001');run(p.parse_args().output)
