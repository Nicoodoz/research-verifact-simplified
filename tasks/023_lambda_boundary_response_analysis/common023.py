"""023 offline paths, exact legacy scalar logs, and binary64 switch diagnostics."""
from pathlib import Path
import math,struct,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/023_lambda_boundary_response_analysis'
sys.path.insert(0,str(ROOT/'tasks/022_competition_aware_support_calibration'))
from common022 import read,jl,csvrows,write,lines,csvwrite,sha,digest,canonical,require,seal,check,evaluate,prediction,LABELS
GRID=[i/100 for i in range(401)]
ANCHORS=[0,.5,1,1.5,2,3,4]
GROUPS=('019','020_R0','020_R1','pooled_R0')

def logs(scores):
    for s in scores:require(set(s)==set(LABELS) and all(type(v) is int and 0<=v<=100 for v in s.values()) and sum(s.values())==100,'Invalid score')
    return np.array([[math.log(max(s[k]/100,1e-6)) for k in LABELS] for s in scores],dtype=np.float64)
def decode(z,lam):
    require(math.isfinite(lam) and 0<=lam<=4,'Lambda outside diagnostic domain')
    non=np.where(z[:,1]>=z[:,2],1,2)
    return np.where(z[:,0]+lam>np.maximum(z[:,1],z[:,2]),0,non)
def is_S(z,lam):return z[0]+lam>max(z[1],z[2])
def bits(x):return struct.unpack('>Q',struct.pack('>d',x))[0]
def number(x):return struct.unpack('>d',struct.pack('>Q',x))[0]
def switching(z):
    theta=float(max(z[1],z[2])-z[0])
    if is_S(z,0.):return dict(theoretical_threshold=theta,status='already_S_at_0',first_S_lambda=None,previous_nonS_lambda=None)
    if not is_S(z,4.):return dict(theoretical_threshold=theta,status='no_switch_in_0_4',first_S_lambda=None,previous_nonS_lambda=None)
    lo=bits(0.);hi=bits(4.)
    while hi-lo>1:
        mid=(lo+hi)//2
        if is_S(z,number(mid)):hi=mid
        else:lo=mid
    require(not is_S(z,number(lo)) and is_S(z,number(hi)),'Switch binary search')
    return dict(theoretical_threshold=theta,status='switch_in_0_4',first_S_lambda=number(hi),previous_nonS_lambda=number(lo))
def subset(rows,group):
    return [r for r in rows if (group=='019' and r['source']=='019') or (group=='020_R0' and r['source']=='020' and r['repeat']==0) or (group=='020_R1' and r['repeat']==1) or (group=='pooled_R0' and r['repeat']==0)]

def point(rows,pred,base0,baseB):
    m=evaluate(rows,prediction(rows,pred),profile='none',missing='error');cm=m['confusion_matrix'];gt=np.array([LABELS.index(r['human_gt']) for r in rows]);pred=np.asarray(pred);base0=np.asarray(base0)
    changes=pred!=base0;require(np.all((base0[changes]!=0)&(pred[changes]==0)),'Not one-way S response')
    R=int(sum(changes&(gt==0)));H=int(sum(changes&(gt!=0)&(base0==gt)));W=int(sum(changes&(gt!=0)&(base0!=gt)))
    false=int(sum((gt!=0)&(pred==0)));nonS=int(sum(gt!=0));correct=int(sum(gt==pred))
    require(correct-int(sum(gt==base0))==R-H,'R-H accounting');require(false-int(sum((gt!=0)&(base0==0)))==H+W,'H+W accounting')
    result=dict(n=len(rows),correct=correct,PA=m['percent_agreement'],MCC=m['mcc'],AC1=m['gwet_ac1'],false_S=false,GT_nonS=nonS,false_S_rate=false/nonS if nonS else None,NS_to_S=cm[1][0],NA_to_S=cm[2][0],rescue=R,harm=H,wrong_to_falseS=W,delta_correct_U0=R-H,delta_correct_B=correct-int(sum(gt==np.asarray(baseB))))
    for i,key in enumerate(('S','NS','NA')):
        result.update({key+'_correct':cm[i][i],key+'_GT':sum(cm[i]),key+'_recall':m['per_class'][LABELS[i]]['recall']})
        for j,other in enumerate(('S','NS','NA')):result['cm_'+key+'_'+other]=cm[i][j]
    return result
