"""Future CPU-only comparison against107's strong saved label_only baseline."""
from collections import Counter
from pathlib import Path
import argparse,sys
import common109 as c
sys.path.insert(0,str(c.ROOT/'src'))
from verifact_research.evaluation import evaluate,paired_compare

def metrics(rows,pred):
    truth=[dict(proposition_id=r['id'],subject_id=str(r['sid']),human_gt=r['GT']) for r in rows]
    verdicts=[dict(proposition_id=r['id'],verdict=pred[r['id']]) for r in rows]
    result=evaluate(truth,verdicts,profile='none');result.update(correct=sum(pred[r['id']]==r['GT'] for r in rows),
        false_S=sum(r['GT']!='Supported' and pred[r['id']]=='Supported' for r in rows),
        non_S=sum(r['GT']!='Supported' for r in rows))
    predicted_s=sum(pred[r['id']]=='Supported' for r in rows)
    result.update(false_S_rate=result['false_S']/result['non_S'] if result['non_S'] else None,
        predicted_S=predicted_s,predicted_S_FDR=result['false_S']/predicted_s if predicted_s else None,
        macro_F1=sum(result['per_class'][g]['f1'] or 0 for g in c.LABELS)/3)
    return result

def point_rule(old,new,panel,coverage,rule):
    dm=new['mcc']-old['mcc'];dp=new['percent_agreement']-old['percent_agreement'];df=new['false_S']-old['false_S']
    dr={g:new['per_class'][g]['recall']-old['per_class'][g]['recall'] if old['per_class'][g]['recall'] is not None and new['per_class'][g]['recall'] is not None else None for g in c.LABELS}
    guards=dict(coverage=coverage>=rule['valid_coverage_min'],MCC=dm>=-rule['guard_MCC_drop']-1e-12,
        PA=dp>=-rule['guard_PA_drop']-1e-12,false_S=df<=rule['guard_false_S_increase'],
        NS=dr['Not Supported'] is not None and dr['Not Supported']>=-rule['guard_NS_NA_recall_drop']-1e-12,
        NA=dr['Not Addressed'] is not None and dr['Not Addressed']>=-rule['guard_NS_NA_recall_drop']-1e-12)
    if panel=='natural':guards['S']=dr['Supported'] is not None and dr['Supported']>=-rule['guard_natural_S_recall_drop']-1e-12
    signal=dm>=rule['signal_MCC_gain']-1e-12 or (df<=-rule['signal_false_S_reduction'] and dp>=-rule['guard_PA_drop']-1e-12)
    return dict(delta_MCC=dm,delta_PA=dp,delta_false_S=df,delta_recall=dr,signal=signal,guards=guards,guard=all(guards.values()))

def compare(bundle,work,bootstrap=False):
    bundle=Path(bundle);work=Path(work);manifest=c.read(bundle/'manifest.json')
    if c.sha(bundle/'data/baseline107.jsonl')!=manifest['files']['data/baseline107.jsonl']['sha256']:raise ValueError('Strong107 baseline was changed')
    done=c.read(work/'train/training_done.json');pointer=c.read(work/'train/resume.json')
    if done['step']!=24 or done['global_step']!=74 or done['fingerprint']!=pointer['fingerprint'] or done['fingerprint']['source_adapter_sha256']!=c.SOURCE_ADAPTER_SHA:raise ValueError('Actual final109 continuation required')
    complete=work/'train'/pointer['slot']/'checkpoint_complete.json'
    if c.sha(complete)!=pointer['complete_sha256']:raise ValueError('Final checkpoint commit mismatch')
    adapter_sha=c.read(complete)['files']['adapter_model.safetensors']
    baseline=c.rows(bundle/'data/baseline107.jsonl');candidate=c.rows(work/'evaluation/predictions.jsonl')
    if any(r.get('prediction_origin')!='actual_GPU_checkpoint' or r.get('checkpoint_adapter_sha256')!=adapter_sha for r in candidate):raise ValueError('Predictions are not this final109 adapter; no historical substitute')
    base={r['id']:r for r in baseline};new={r['id']:r for r in candidate}
    if len(base)!=500 or len(new)!=500 or len(candidate)!=500 or set(base)!=set(new):raise ValueError('Complete same500 receipts required; no fallback or missing-ID filtering')
    for i,row in new.items():
        if str(row['sid'])!=str(base[i]['sid']) or row['prompt_token_sha256']!=base[i]['prompt_token_sha256']:raise ValueError('Changed evaluation patient/prompt')
    config=c.read(bundle/'frozen/config109.json');panels={}
    for panel,n in [('natural',400),('pressure',100)]:
        allrows=[r for r in baseline if r['panel']==panel]
        if len(allrows)!=n:raise ValueError('Wrong original natural/pressure panel')
        rows=[r for r in allrows if r['parsed']['valid'] and new[r['id']]['parsed']['valid']]
        if not rows:raise ValueError('No jointly valid outputs; no method conclusion')
        old={r['id']:r['parsed']['verdict'] for r in rows};pred={r['id']:new[r['id']]['parsed']['verdict'] for r in rows}
        a,b=metrics(rows,old),metrics(rows,pred);changes={g:dict(rescued=sum(r['GT']==g and old[r['id']]!=g==pred[r['id']] for r in rows),
            harmed=sum(r['GT']==g and old[r['id']]==g!=pred[r['id']] for r in rows)) for g in c.LABELS}
        p=dict(all_receipts=n,joint_valid_N=len(rows),coverage=len(rows)/n,invalid_candidate=sum(not new[r['id']]['parsed']['valid'] for r in allrows),
            output_quality=dict(strict_json=sum(new[r['id']]['parsed'].get('strict_json',False) for r in allrows),
                exact_label_normalized=sum(new[r['id']]['parsed'].get('exact_label_normalized',False) for r in allrows)),
            invalid_candidate_GT=dict(Counter(r['GT'] for r in allrows if not new[r['id']]['parsed']['valid'])),
            baseline_full_panel=metrics(allrows,{r['id']:r['parsed']['verdict'] for r in allrows}),baseline_common=a,candidate_common=b,
            class_changes=changes,false_S_new=sum(r['GT']!='Supported' and old[r['id']]!='Supported'==pred[r['id']] for r in rows),
            false_S_avoided=sum(r['GT']!='Supported' and old[r['id']]=='Supported'!=pred[r['id']] for r in rows),
            **point_rule(a,b,panel,len(rows)/n,config['effect_rule']))
        if bootstrap:
            cohort=[dict(proposition_id=r['id'],subject_id=str(r['sid']),human_gt=r['GT']) for r in rows]
            pa=[dict(proposition_id=r['id'],verdict=old[r['id']]) for r in rows];pb=[dict(proposition_id=r['id'],verdict=pred[r['id']]) for r in rows]
            p['patient_paired']=paired_compare(cohort,pa,pb,iterations=1000)
        panels[panel]=p
    keep=all(p['guard'] for p in panels.values()) and any(p['signal'] for p in panels.values())
    return dict(task=109,baseline='107_label_only_first500',candidate='boundary_replay',direction='candidate-minus-baseline',panels=panels,
        worth_considering_matched_replay_control=keep,matched_control_automatically_authorized=False,
        selection_benefit_distinguished_from_more_training=False,second_arm_run=False,automatic_recipe_search=False,
        decision='candidate_signal_needs_user_decision_on_same_start_same_budget_ordinary_replay_control' if keep else 'stop_current_recipe_no_additional_GPU',
        new109_classification_results=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--bootstrap',action='store_true');a=p.parse_args()
    result=compare(a.bundle,a.work,a.bootstrap);c.put(a.output,result);print(c.canonical(dict(decision=result['decision'])))
