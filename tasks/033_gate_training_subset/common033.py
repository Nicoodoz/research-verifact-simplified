"""Task033 offline fixed-recipe subset research. Never import an API execution module."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/033_gate_training_subset';PREP=OUT/'preparation_001'
sys.path.insert(0,str(ROOT/'tasks/030_gate_training_stability'))
import common030 as old
c=old.v;old.offline()
read=old.read;lines=old.lines;put=old.put;jsonl=old.jsonl;csvwrite=old.csvwrite;csvread=old.csvread;sha=old.sha;require=old.require;now=old.now;write_text=old.write_text;digest=old.digest;LABELS=old.LABELS
HIST=old.OUT/'run_001';P31=ROOT/'outputs/031_training_expansion_confirmation'

def status(stage,**values):put(OUT/'execution_status.json',dict(stage=stage,updated_utc=now(),API_calls=0,**values));print(stage,values,flush=True)
def fit_probability(model,rows):return old.model_probability(model['final_fit'],rows)
def pred(rows,prob,threshold):
    ii={r['proposition_id']:i for i,r in enumerate(rows) if r['candidate']};p=np.array([r['u0'] for r in rows]);indices=list(ii.values());require(len(indices)==len(prob),'Prediction alignment');p[indices]=np.where(np.asarray(prob)>=threshold,0,p[indices]);return p
def candidate_rows(rows):return [r for r in rows if r['candidate']]
def point(rows,pp):return old.point(rows,np.asarray(pp))
def curves(rows,prob,threshold):
    candidates=candidate_rows(rows);mapping={r['proposition_id']:dict(probability=float(v),keep=bool(v>=threshold)) for r,v in zip(candidates,prob)};return old.evaluation.states(rows,mapping)
def training_summary(patients,full,features):
    rr=[r for r in features if r['subject_id'] in patients];ff=[r for r in full if r['subject_id'] in patients];R=sum(r['human_gt']=='Supported' for r in rr);H=sum(r['human_gt']!='Supported' and r['u0']==LABELS.index(r['human_gt']) for r in rr);W=len(rr)-R-H
    return dict(k=len(patients),train_candidates=len(rr),train_R=R,train_H=H,train_W=W,train_risk=H+W,train_R_fraction=R/len(rr) if rr else None,train_human_fraction=sum(r['author_type']=='human' for r in rr)/len(rr) if rr else None,train_full_claims=len(ff),train_patients=sorted(patients))
def sort_key(r):return (-int(r['eligible_retention80']),-r['robust_gain_per100R'],-r['MCC'],-r['correct'],r['risk'],r['k'],r['set_id'])

class Panel:
    def __init__(self,rows,reference_model):
        self.rows=rows;self.candidates=candidate_rows(rows);self.subjects=sorted({r['subject_id'] for r in rows});self.Rtotal=sum(r['human_gt']=='Supported' for r in self.candidates);self.u2=np.array([r['u2'] for r in rows]);self.refprob=fit_probability(reference_model,self.candidates);self.refpred=pred(rows,self.refprob,reference_model['threshold']);_,gp=old.frontier.global_states(rows);_,ap=curves(rows,self.refprob,reference_model['threshold']);self.refs={'global':gp,'A16':ap};self.refpoint=point(rows,self.refpred);self.weights=[np.ones(len(rows))]+[np.array([r['subject_id']!=s for r in rows],float) for s in self.subjects];self.counts={name:[old.frontier.counts(rows,pp,w) for w in self.weights] for name,pp in self.refs.items()}
    def evaluate(self,prob,threshold):
        pp=pred(self.rows,prob,threshold);m=point(self.rows,pp);values={};minimum=[];loo_positive=[]
        for name in self.refs:
            gains=[]
            for w,(R,F) in zip(self.weights,self.counts[name]):
                tr,tf=old.frontier.counts(self.rows,pp,w);match=old.frontier.matched(F,R,float(tf[0]),float(tr[0]));den=sum(w[i] for i,r in enumerate(self.rows) if r['candidate'] and r['human_gt']=='Supported');gains.append(match['R_gain_vs_mixture']/den*100 if den else 0.)
            values[name+'_gain_R']=gains[0]*self.Rtotal/100;values[name+'_loo_min_gain_per100R']=min(gains[1:]);values[name+'_loo_positive']=sum(x>1e-9 for x in gains[1:]);minimum+=gains
        delta=[]
        for s in self.subjects:
            ii=np.array([i for i,r in enumerate(self.rows) if r['subject_id']==s]);gt=np.array([LABELS.index(self.rows[i]['human_gt']) for i in ii]);delta.append(int(sum(pp[ii]==gt)-sum(self.refpred[ii]==gt)))
        return dict(**m,**values,robust_gain_per100R=min(minimum),eligible_retention80=m['rescue_retention'] is not None and m['rescue_retention']>=.8,positive_patients_vs_A16=sum(x>0 for x in delta),negative_patients_vs_A16=sum(x<0 for x in delta),tied_patients_vs_A16=sum(x==0 for x in delta),delta_correct_vs_A16=m['correct']-self.refpoint['correct'])
