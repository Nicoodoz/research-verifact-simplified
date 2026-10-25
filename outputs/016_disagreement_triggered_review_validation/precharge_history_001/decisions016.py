"""Preregistered gate construction and progression decisions; GT never chooses triggers."""
from collections import defaultdict
import math
import common016 as c

BASE=('v4_first','qwen')

def correct(rows,key):return sum(r[key]==r['human_gt'] for r in rows)

def compose(rows,union=False):
    result=[dict(r) for r in rows]
    groups=defaultdict(list)
    for r in result:
        for role in c.ROLES:c.require(r[role] in c.LABELS,'Incomplete base role')
        r['cross_trigger']=r['v4_first']!=r['qwen'];r['self_trigger']=r['v4_first']!=r['v4_repeat']
        r['cross_review']=r['independent_review'] if r['cross_trigger'] else r['v4_first']
        r['cross_repeat']=r['v4_repeat'] if r['cross_trigger'] else r['v4_first']
        if union:
            r['union_trigger']=r['cross_trigger'] or r['self_trigger']
            r['union_review']=r['independent_review'] if r['union_trigger'] else r['v4_first']
            r['union_repeat']=r['v4_repeat'] if r['union_trigger'] else r['v4_first']
        groups[(r['subject_id'],r['author_type'])].append(r)
    for group in groups.values():
        ordered=sorted(group,key=lambda r:(c.hash_rank(r['proposition_id']),r['proposition_id']))
        chosen={r['proposition_id'] for r in ordered[:sum(r['cross_trigger'] for r in group)]}
        uchosen={r['proposition_id'] for r in ordered[:sum(r['union_trigger'] for r in group)]} if union else set()
        for r in group:
            r['hash_trigger']=r['proposition_id'] in chosen
            r['hash_review']=r['independent_review'] if r['hash_trigger'] else r['v4_first']
            if union:
                r['union_hash_trigger']=r['proposition_id'] in uchosen
                r['union_hash_review']=r['independent_review'] if r['union_hash_trigger'] else r['v4_first']
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
    conditions['complete']=n==601 and all(r[k] in c.LABELS for r in rows for k in (*c.ROLES,'released'))
    conditions['net_vs_best_single']=correct(rows,method)-max(correct(rows,k) for k in BASE)>=math.ceil(.02*n)
    for control in ('cross_repeat','v4_repeat','hash_review'):
        conditions['net_vs_'+control]=correct(rows,method)-correct(rows,control)>=math.ceil(.01*n)
    for a in ('llm','human'):
        rr=[r for r in rows if r['author_type']==a];d=[r for r in rr if r['cross_trigger']];agree=[r for r in rr if not r['cross_trigger']]
        ed=sum(r['v4_first']!=r['human_gt'] for r in d)/len(d) if d else 0
        ea=sum(r['v4_first']!=r['human_gt'] for r in agree)/len(agree) if agree else 0
        enriched=bool(d and agree and ed-ea>=.10 and ed>=1.5*ea)
        conditions[a+'_error_enrichment']=enriched
        enrichment[a]=dict(disagreement_n=len(d),agreement_n=len(agree),disagreement_V1_error_rate=ed,agreement_V1_error_rate=ea,
            relative_risk=ed/ea if ea else None,zero_agreement_error_rate=ea==0,criterion_met=enriched)
        m=metrics[a];chosen=m[method]
        conditions[a+'_gain']=correct(rr,method)-max(correct(rr,k) for k in BASE)>=math.ceil(.01*len(rr))
        conditions[a+'_mcc']=chosen['mcc']-max(m[k]['mcc'] for k in BASE)>=.025
        conditions[a+'_ac1']=chosen['gwet_ac1']>=max(m[k]['gwet_ac1'] for k in BASE)
        conditions[a+'_review_over_repeat_correct']=correct(rr,method)>correct(rr,'cross_repeat')
        conditions[a+'_review_over_repeat_mcc']=chosen['mcc']-m['cross_repeat']['mcc']>=.01
        for control in ('v4_repeat','hash_review'):
            conditions[a+'_'+control+'_no_loss']=correct(rr,method)>=correct(rr,control) and chosen['mcc']>=m[control]['mcc']
    safe,patients=protection(rows,metrics,method);conditions.update(safe)
    return dict(passed=all(conditions.values()),conditions=conditions,error_enrichment=enrichment,patient_net_vs_V1=patients,
        net_vs_best_single=correct(rows,method)-max(correct(rows,k) for k in BASE),
        net_vs_controls={k:correct(rows,method)-correct(rows,k) for k in ('cross_repeat','v4_repeat','hash_review','independent_review')})

def select_limited(rows,metrics,stage1_gate):
    c.require(stage1_gate['passed'],'No second-stage selection after failed screen')
    safe,_=protection(rows,metrics,'union_review')
    gain=correct(rows,'union_review')-correct(rows,'cross_review')
    additional=sum(r['union_trigger'] and not r['cross_trigger'] for r in rows)
    union_conditions=dict(net_gain=gain>=math.ceil(.01*len(rows)),additional_review_efficiency=gain*10>=additional,**safe)
    for a in ('llm','human'):
        rr=[r for r in rows if r['author_type']==a]
        union_conditions[a+'_no_loss']=correct(rr,'union_review')>=correct(rr,'cross_review') and metrics[a]['union_review']['mcc']>=metrics[a]['cross_review']['mcc']
    selected='union_review' if all(union_conditions.values()) else 'cross_review'
    parsimony={'over_full_review':correct(rows,selected)-correct(rows,'independent_review')>=math.ceil(.01*len(rows))}
    for a in ('llm','human'):
        rr=[r for r in rows if r['author_type']==a]
        parsimony[a+'_no_loss']=correct(rr,selected)>=correct(rr,'independent_review') and metrics[a][selected]['mcc']>=metrics[a]['independent_review']['mcc']
    safe,_=protection(rows,metrics,selected);parsimony.update(safe)
    return dict(winner=selected if all(parsimony.values()) else None,selected_before_parsimony=selected,
        union_conditions=union_conditions,union_extra_review_calls=additional,union_extra_ordinary_V4_calls=len(rows),
        parsimony_conditions=parsimony,no_more_candidates=True)

def confirmation_gate(rows,metrics,pooled_pairs,winner):
    c.require(winner in ('cross_review','union_review'),'Invalid frozen winner')
    n=len(rows);conditions={'complete':n==879 and all(r[k] in c.LABELS for r in rows for k in (*c.ROLES,'released'))}
    conditions['net_vs_best_single']=correct(rows,winner)-max(correct(rows,k) for k in BASE)>=math.ceil(.02*n)
    repeat='union_repeat' if winner=='union_review' else 'cross_repeat'
    hashed='union_hash_review' if winner=='union_review' else 'hash_review'
    for control in (repeat,hashed,'v4_repeat','independent_review'):
        conditions['net_vs_'+control]=correct(rows,winner)-correct(rows,control)>=math.ceil(.01*n)
    for a in ('llm','human'):
        rr=[r for r in rows if r['author_type']==a];m=metrics[a];chosen=m[winner]
        conditions[a+'_pa']=chosen['percent_agreement']-max(m[k]['percent_agreement'] for k in BASE)>=.01
        conditions[a+'_mcc']=chosen['mcc']-max(m[k]['mcc'] for k in BASE)>=.025
        conditions[a+'_ac1']=chosen['gwet_ac1']>=max(m[k]['gwet_ac1'] for k in BASE)
        for control in (repeat,hashed,'v4_repeat','independent_review'):
            conditions[a+'_'+control+'_no_loss']=correct(rr,winner)>=correct(rr,control) and chosen['mcc']>=m[control]['mcc']
    for k in BASE:conditions['pooled_pa_ci_over_'+k]=pooled_pairs[k]['metrics']['percent_agreement']['ci95'][0]>0
    safe,patients=protection(rows,metrics,winner);conditions.update(safe)
    return dict(passed=all(conditions.values()),conditions=conditions,patient_net_vs_V1=patients)
