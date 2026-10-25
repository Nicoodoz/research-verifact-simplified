"""025 offline helpers and exact frozen decision semantics. No API imports."""
from pathlib import Path
import sys,math,struct,re,json
import numpy as np
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/025_lambda_flip_risk_separability'
sys.path.insert(0,str(ROOT/'tasks/022_competition_aware_support_calibration'))
from common022 import read,jl,csvrows,write,lines,csvwrite,sha,digest,canonical,require,evaluate,paired_compare,prediction,LABELS
S_NAMES=['s','ns','na','s_margin','non_s_margin','entropy','u0_ns']
E_NAMES=['all_coverage','best_chunk_coverage','best_jaccard','number_coverage','negative_context_coverage','repeated_coverage','rerank_max','selected_top3_mean','selected_unselected_gap']
D_NAMES=['peer_s','peer_margin','peer_u0_s','peer_u2_s','same_u0']
METHODS={'S':S_NAMES,'SE':S_NAMES+E_NAMES,'SD':S_NAMES+D_NAMES,'SED':S_NAMES+E_NAMES+D_NAMES}
def logs(scores):return np.array([math.log(max(scores[k]/100,1e-6)) for k in LABELS])
def decode(z,lam):
    z=np.asarray(z);non=np.where(z[...,1]>=z[...,2],1,2)
    return np.where(z[...,0]+lam>np.maximum(z[...,1],z[...,2]),0,non)
def first_switch(z):
    if decode(z,0)==0:return None
    def bits(x):return struct.unpack('>Q',struct.pack('>d',x))[0]
    def num(x):return struct.unpack('>d',struct.pack('>Q',x))[0]
    lo=bits(0.);hi=bits(16.)
    require(decode(z,16)==0,'Incomplete lambda range')
    while hi-lo>1:
        mid=(lo+hi)//2
        if decode(z,num(mid))==0:hi=mid
        else:lo=mid
    return num(hi)
def score_features(sc):
    p=np.array([sc[k]/100 for k in LABELS]);z=logs(sc)
    return dict(zip(S_NAMES,[*p,z[0]-max(z[1:]),abs(z[1]-z[2]),-sum(p*np.log(np.maximum(p,1e-6))),float(decode(z,0)==1)]))
def evidence_features(material):
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    def clean(s):return re.sub(r'\[\*\*.*?\*\*\]',' ',s,flags=re.S)
    def tokens(s):return set(re.findall(r'[a-z]+',clean(s).lower()))-ENGLISH_STOP_WORDS
    text=material['text'];reference=material['reference']
    parts=re.split(r'(?m)^\d+\. Date:.*?\| Text:\s*',reference)[1:]
    require(bool(parts),'Unrecognized frozen reference format')
    claim=tokens(text);tt=[tokens(p) for p in parts];alltok=set().union(*tt)
    cov=lambda t:len(claim&t)/max(1,len(claim))
    numbers=set(re.findall(r'\b\d+(?:\.\d+)?\b',clean(text)));nums=set(re.findall(r'\b\d+(?:\.\d+)?\b',clean(' '.join(parts))))
    neg=[s for part in parts for s in re.split(r'[.\n]',part) if re.search(r'\b(no|not|denies|denied|without|negative)\b',s,re.I)]
    base=[cov(alltok),max(map(cov,tt)),max(len(claim&t)/max(1,len(claim|t)) for t in tt),len(numbers&nums)/len(numbers) if numbers else 1.,cov(tokens(' '.join(neg))),sum(cov(t)>=.5 for t in tt)/len(tt)]
    scores=material.get('scores',{});selected=material.get('selected_ids',[])
    sv=sorted([scores[x] for x in selected],reverse=True);uv=[v for k,v in scores.items() if k not in set(selected)]
    retrieval=[max(scores.values()),float(np.mean(sv[:3])),max(sv)-max(uv) if uv else 0.] if scores and sv else [0.,0.,0.]
    return dict(zip(E_NAMES,base+retrieval))
def point(rows,pred):
    gt=np.array([LABELS.index(r['human_gt']) for r in rows]);u0=np.array([r['u0'] for r in rows]);p=np.asarray(pred);changed=p!=u0
    require(np.all(p[changed]==0),'Gate may only retain lambda S flips')
    m=evaluate(rows,prediction(rows,p),profile='none');R=int(sum(changed&(gt==0)));H=int(sum(changed&(gt!=0)&(u0==gt)));W=int(sum(changed&(gt!=0)&(u0!=gt)))
    return dict(n=len(rows),correct=int(sum(p==gt)),PA=m['percent_agreement'],MCC=m['mcc'],AC1=m['gwet_ac1'],R=R,H=H,W=W,risk=H+W,net=R-H,false_S=int(sum((p==0)&(gt!=0))),S_recall=m['per_class'][LABELS[0]]['recall'],NS_recall=m['per_class'][LABELS[1]]['recall'],NA_recall=m['per_class'][LABELS[2]]['recall'],confusion_matrix=m['confusion_matrix'])
