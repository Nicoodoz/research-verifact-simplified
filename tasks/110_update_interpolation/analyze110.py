"""CPU comparison of both fixed candidates against107; no new model calls."""
from collections import Counter
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/109_boundary_replay'));import common109 as c
from analyze109 import metrics,point_rule
sys.path.insert(0,str(ROOT/'tasks/107_support_aux'));from evaluate107 import risk_deltas
sys.path.insert(0,str(ROOT/'src'));from verifact_research.evaluation import paired_compare
from sklearn.metrics import matthews_corrcoef,accuracy_score
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));from parse105 import parse
def changes(rows,old,new):
    return dict(by_class={g:dict(rescued=sum(r['GT']==g and r['pred'][old]!=g==r['pred'][new] for r in rows),harmed=sum(r['GT']==g and r['pred'][old]==g!=r['pred'][new] for r in rows)) for g in c.LABELS},
        false_S_new=sum(r['GT']!='Supported' and r['pred'][old]!='Supported'==r['pred'][new] for r in rows),
        false_S_avoided=sum(r['GT']!='Supported' and r['pred'][old]=='Supported'!=r['pred'][new] for r in rows))
def compare(old_bundle,old_work,work,bootstrap):
    base=c.rows(old_bundle/'data/baseline107.jsonl');lookup={r['id']:r for r in base};config=c.read(ROOT/'tasks/110_update_interpolation/config.json')
    old109={r['id']:r for r in c.rows(old_work/'evaluation/predictions.jsonl')};composition=c.read(work/'composition.json')
    keys={r['id']:r for r in c.rows(ROOT/'.local_models/107_support_aux/gpu_bundle_5090_run/frozen/eval_keys.jsonl')}
    data={'label_only107':lookup,'boundary_replay109':old109}
    for arm in config['candidates']:
        records=c.rows(work/arm/'predictions.jsonl');data[arm]={r['id']:r for r in records}
        if len(records)!=500 or len(data[arm])!=500 or set(data[arm])!=set(lookup):raise ValueError('Complete same500 first receipts required')
        if any(r['identity']!=composition['identities'][arm] for r in records):raise ValueError('Another adapter in candidate receipts')
        for r in records:
            if r['parsed']!=parse(r['content'],r['finish_reason']):raise ValueError('Stored output differs from unchanged original parser')
            if r['prompt_token_sha256']!=lookup[r['id']]['prompt_token_sha256'] or str(r['sid'])!=str(lookup[r['id']]['sid']):raise ValueError('Changed original input/patient')
    panels={}
    for panel,N in [('natural',400),('pressure',100)]:
        full=[r for r in base if r['panel']==panel];assert len(full)==N
        rows=[]
        for r in full:
            if all(data[arm][r['id']]['parsed']['valid'] for arm in data):
                if r['GT']!=keys[r['id']]['GT']:raise ValueError('Original GT mismatch')
                rows.append(dict(r,pred={**{arm:data[arm][r['id']]['parsed']['verdict'] for arm in data},'paper_r1':keys[r['id']]['paper_r1']}))
        scores={arm:metrics(rows,{r['id']:r['pred'][arm] for r in rows}) for arm in [*data,'paper_r1']}
        for arm in data:
            truth=[r['GT'] for r in rows];pred=[r['pred'][arm] for r in rows]
            if abs(matthews_corrcoef(truth,pred)-scores[arm]['mcc'])>1e-12 or abs(accuracy_score(truth,pred)-scores[arm]['percent_agreement'])>1e-12:raise ValueError('Independent metric mismatch')
        paired={}
        for arm in config['candidates']:
            part=[r for r in full if lookup[r['id']]['parsed']['valid'] and data[arm][r['id']]['parsed']['valid']]
            a={r['id']:lookup[r['id']]['parsed']['verdict'] for r in part};b={r['id']:data[arm][r['id']]['parsed']['verdict'] for r in part}
            aa,bb=metrics(part,a),metrics(part,b);direction=point_rule(aa,bb,panel,len(part)/N,config['effect_rule'])
            paired[arm]=dict(N=len(part),baseline=aa,candidate=bb,**direction)
            if bootstrap:
                cohort=[dict(proposition_id=r['id'],subject_id=str(r['sid']),human_gt=r['GT']) for r in part]
                pa=[dict(proposition_id=r['id'],verdict=a[r['id']]) for r in part];pb=[dict(proposition_id=r['id'],verdict=b[r['id']]) for r in part]
                paired[arm]['patient_paired']=paired_compare(cohort,pa,pb,iterations=1000)
            delta=changes(rows,'label_only107',arm);recover={}
            for g in c.LABELS:
                gains=[r for r in rows if r['GT']==g and r['pred']['label_only107']!=g==r['pred']['boundary_replay109']]
                lost=[r for r in rows if r['GT']==g and r['pred']['label_only107']==g!=r['pred']['boundary_replay109']]
                recover[g]=dict(new109_gains_N=len(gains),new109_gains_retained=sum(r['pred'][arm]==g for r in gains),correct107_harmed_by109_N=len(lost),correct107_harmed_by109_restored=sum(r['pred'][arm]==g for r in lost))
            subjects=sorted({str(r['sid']) for r in rows});patients=[]
            for index,sid in enumerate(subjects,1):
                group=[r for r in rows if str(r['sid'])==sid]
                patients.append(dict(patient_index=index,N=len(group),correct_delta=sum(int(r['pred'][arm]==r['GT'])-int(r['pred']['label_only107']==r['GT']) for r in group),false_S_delta=sum(int(r['GT']!='Supported' and r['pred'][arm]=='Supported')-int(r['GT']!='Supported' and r['pred']['label_only107']=='Supported') for r in group)))
            paired[arm].update(changes_vs107=delta,changes_vs109=changes(rows,'boundary_replay109',arm),retaining109_gains_and_restoring107=recover,patients=patients,
                patient_direction=dict(correct_improved=sum(p['correct_delta']>0 for p in patients),correct_worsened=sum(p['correct_delta']<0 for p in patients),unchanged=sum(p['correct_delta']==0 for p in patients)))
            if bootstrap:paired[arm]['risk_CI']=risk_deltas(rows,'label_only107',arm)
        panels[panel]=dict(frozen_N=N,common_all_valid_N=len(rows),patient_N=len({r['sid'] for r in rows}),scores=scores,paired_vs107=paired,
            coverage={arm:dict(received=N,valid=sum(data[arm][r['id']]['parsed']['valid'] for r in full),invalid=sum(not data[arm][r['id']]['parsed']['valid'] for r in full),
                strict_JSON=sum(data[arm][r['id']]['parsed'].get('strict_json',False) for r in full),exact_label_normalized=sum(data[arm][r['id']]['parsed'].get('exact_label_normalized',False) for r in full),
                truncated_finish=sum(data[arm][r['id']].get('finish_reason')=='length' for r in full),invalid_GT=dict(Counter(r['GT'] for r in full if not data[arm][r['id']]['parsed']['valid']))) for arm in data},
            author={author:{arm:metrics([r for r in rows if r['author']==author],{r['id']:r['pred'][arm] for r in rows if r['author']==author}) for arm in data} for author in sorted({r['author'] for r in rows})})
    keep={arm:all(p['paired_vs107'][arm]['guard'] for p in panels.values()) and any(p['paired_vs107'][arm]['signal'] for p in panels.values()) for arm in config['candidates']}
    return dict(task=110,panels=panels,prewritten_screening_reference_passed=keep,candidates_all_reported=True,source107_and109_full500_reused=True,
        no_new_training=True,new_paid_API_CNY=0,no_dense_alpha_search=True,independent_sklearn_metrics_match=True,
        decision='candidate_signal_requires_only_next_necessary_validation_decision' if any(keep.values()) else 'end_current109_weight_derivative_route_no_more_coefficients',
        development_selection_not_independent_blind_test=True,low_learning_rate_or_early_checkpoint_equivalence_established=False)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['old-bundle','old-work','work','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--bootstrap',action='store_true');a=p.parse_args();r=compare(a.old_bundle,a.old_work,a.work,a.bootstrap);c.put(a.output,r);print(c.canonical(dict(decision=r['decision'],candidate_screening=r['prewritten_screening_reference_passed'])))
