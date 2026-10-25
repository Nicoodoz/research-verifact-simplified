"""Preregistered gate construction and progression decisions; GT never chooses triggers."""
from collections import defaultdict
import math
import common016 as c

BASE=('v4_first','qwen')

def correct(rows,key):return sum(r[key]==r['human_gt'] for r in rows)

def compose(rows):
    result=[dict(r) for r in rows]
    for r in result:
        for role in BASE:c.require(r[role] in c.LABELS,'Incomplete base role')
        r['cross_trigger']=r['v4_first']!=r['qwen']
        if r['cross_trigger']:
            for role in ('v4_repeat','independent_review'):c.require(r[role] in c.LABELS,'Incomplete disagreement review')
        r['cross_review']=r['independent_review'] if r['cross_trigger'] else r['v4_first']
        r['cross_repeat']=r['v4_repeat'] if r['cross_trigger'] else r['v4_first']
    return result

def protection(rows,metrics,method):
    conditions={};patient_deltas={}
    for author in ('llm','human'):
        rr=[r for r in rows if r['author_type']==author];m=metrics[author];chosen=m[method]
        for label in c.LABELS:
            b=m['v4_first']['per_class'][label]
            conditions[author+'_'+label+'_preserved']=chosen['per_class'][label]['tp']>=b['tp']-max(1,math.floor(.05*b['support']))
        conditions[author+'_false_S']=chosen['per_class']['Supported']['fp']<=min(m[x]['per_class']['Supported']['fp'] for x in BASE)+1
    for sid in sorted({r['subject_id'] for r in rows}):
        rr=[r for r in rows if r['subject_id']==sid];delta=correct(rr,method)-correct(rr,'v4_first');patient_deltas[sid]=delta
        conditions['patient_'+sid+'_harm_bound']=delta>=-max(2,math.ceil(.02*len(rr)))
    conditions['patients_positive']=sum(d>0 for d in patient_deltas.values())>=(4 if len(patient_deltas)==6 else 6)
    return conditions,patient_deltas

def first_gate(rows,metrics):
    n=len(rows);conditions={};enrichment={};method='cross_review'
    conditions['complete']=n==601 and all(r[k] in c.LABELS for r in rows for k in (*BASE,'cross_review','cross_repeat','released'))
    conditions['net_vs_best_single']=correct(rows,method)-max(correct(rows,k) for k in BASE)>=math.ceil(.02*n)
    for control in ('cross_repeat',):
        conditions['net_vs_'+control]=correct(rows,method)-correct(rows,control)>=math.ceil(.01*n)
    for a in ('llm','human'):
        rr=[r for r in rows if r['author_type']==a];d=[r for r in rr if r['cross_trigger']];agree=[r for r in rr if not r['cross_trigger']]
        ed=sum(r['v4_first']!=r['human_gt'] for r in d)/len(d) if d else 0
        ea=sum(r['v4_first']!=r['human_gt'] for r in agree)/len(agree) if agree else 0
        enriched=bool(d and agree and ed-ea>=.10 and ed>=1.5*ea)
        enrichment[a]=dict(disagreement_n=len(d),agreement_n=len(agree),disagreement_V1_error_rate=ed,agreement_V1_error_rate=ea,
            relative_risk=ed/ea if ea else None,zero_agreement_error_rate=ea==0,criterion_met=enriched)
        m=metrics[a];chosen=m[method]
        conditions[a+'_gain']=correct(rr,method)-max(correct(rr,k) for k in BASE)>=math.ceil(.01*len(rr))
        conditions[a+'_mcc']=chosen['mcc']-max(m[k]['mcc'] for k in BASE)>=.025
        conditions[a+'_ac1']=chosen['gwet_ac1']>=max(m[k]['gwet_ac1'] for k in BASE)
        conditions[a+'_review_over_repeat_correct']=correct(rr,method)>correct(rr,'cross_repeat')
        conditions[a+'_review_over_repeat_mcc']=chosen['mcc']-m['cross_repeat']['mcc']>=.01
    safe,patients=protection(rows,metrics,method);conditions.update(safe)
    return dict(passed=all(conditions.values()),conditions=conditions,error_enrichment=enrichment,patient_net_vs_V1=patients,
        net_vs_best_single=correct(rows,method)-max(correct(rows,k) for k in BASE),
        net_vs_controls={k:correct(rows,method)-correct(rows,k) for k in ('cross_repeat',)})

