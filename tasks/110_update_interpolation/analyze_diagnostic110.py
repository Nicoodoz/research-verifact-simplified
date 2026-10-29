"""CPU paired192 diagnostic. Training fit is not development-set improvement."""
from pathlib import Path
from collections import Counter
import argparse,sys,statistics
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tasks/109_boundary_replay'));import common109 as c
def analyze(old,work):
    selected=c.rows(old/'selected_manifest.jsonl');train=c.rows(old/'train.jsonl')
    if [r['id'] for r in selected]!=[r['id'] for r in train]:raise ValueError('109 actual train IDs/order differ')
    import json
    if any(json.loads(r['answer'])['verdict']!=r['GT'] for r in train):raise ValueError('Historical teacher label differs from GT')
    before={r['id']:r for name in ['mining_a','mining_s'] for r in c.rows(old/name/'predictions.jsonl')};after={r['id']:r for r in c.rows(work/'train192/predictions.jsonl')}
    if len(after)!=192 or set(after)!={r['id'] for r in selected}:raise ValueError('Complete192 first predictions required')
    for r in selected:
        a=before[r['id']];z=after[r['id']]
        if a['checkpoint_adapter_sha256']!=c.SOURCE_ADAPTER_SHA or z['identity']['adapter_sha256']!='e3c83143648a2f64ccd60f5b68e1b94bec5e0279c75a3be43c2872ba6ee0b9e8':raise ValueError('Wrong diagnostic endpoint')
        if a['prompt_token_sha256']!=z['prompt_token_sha256'] or str(a['sid'])!=str(z['sid']):raise ValueError('Different actual prompt/patient')
    def pred(records,i):return records[i]['parsed'].get('verdict') if records[i]['parsed']['valid'] else None
    def summary(rows):
        return dict(N=len(rows),invalid=sum(pred(after,r['id']) is None for r in rows),before_correct=sum(pred(before,r['id'])==r['GT'] for r in rows),
            after_correct=sum(pred(after,r['id'])==r['GT'] for r in rows),rescued=sum(pred(before,r['id'])!=r['GT']==pred(after,r['id']) for r in rows),
            harmed=sum(pred(before,r['id'])==r['GT']!=pred(after,r['id']) for r in rows),after_predictions=dict(Counter(pred(after,r['id']) or 'INVALID' for r in rows)))
    hard=[r for r in selected if r['role']=='hard_error'];false=[r for r in hard if pred(before,r['id'])=='Supported'];na=[r for r in selected if r['GT']=='Not Addressed'];keepna=[r for r in na if r['role']=='retention']
    if len(hard)!=64 or len(false)!=35 or len(na)!=64 or len(keepna)!=32:raise ValueError('Historical fixed192 roles differ')
    result=dict(task=110,kind='training_fit_diagnostic_not_method_success',actual_train_N=192,GT=dict(Counter(r['GT'] for r in selected)),
        full=summary(selected),hard64=summary(hard),original_false_S35=dict(N=35,fixed_to_GT=sum(pred(after,r['id'])==r['GT'] for r in false),
            changed_to_another_error=sum(pred(after,r['id']) not in [None,'Supported',r['GT']] for r in false),still_false_S=sum(pred(after,r['id'])=='Supported' for r in false),invalid=sum(pred(after,r['id']) is None for r in false)),
        retained_NA32=summary(keepna),all_training_NA64=summary(na),
        by_role={role:summary([r for r in selected if r['role']==role]) for role in ['hard_error','protect_S','retention']},
        by_role_GT={role:{g:summary([r for r in selected if r['role']==role and r['GT']==g]) for g in c.LABELS} for role in ['hard_error','protect_S','retention']},
        historical_GT_answers_checkpoint_and_prompt_mapping_checks_passed=True,paid_API_CNY=0,new_training=False)
    result['original_false_S35']['by_GT']={g:dict(N=sum(r['GT']==g for r in false),fixed_to_GT=sum(r['GT']==g==pred(after,r['id']) for r in false),
        changed_to_another_error=sum(r['GT']==g and pred(after,r['id']) not in [None,'Supported',g] for r in false),still_false_S=sum(r['GT']==g and pred(after,r['id'])=='Supported' for r in false)) for g in c.LABELS[1:]}
    c.putl(work/'paired_training192_case_changes.jsonl',[dict(id=r['id'],sid=r['sid'],GT=r['GT'],role=r['role'],before=pred(before,r['id']),after=pred(after,r['id']),
        previous_false_S=r in false,repaired=pred(before,r['id'])!=r['GT']==pred(after,r['id']),harmed=pred(before,r['id'])==r['GT']!=pred(after,r['id'])) for r in selected])
    paths=[work/('NA32_loss_'+arm+'.jsonl') for arm in ['anchor107','update109']]
    if all(p.exists() for p in paths):
        a={r['id']:r for r in c.rows(paths[0])};z={r['id']:r for r in c.rows(paths[1])};ids={r['id'] for r in keepna}
        if set(a)!=ids or set(z)!=ids:raise ValueError('Loss cohort is not fixed32 retained NA')
        diff=[z[i]['verdict_token_mean_CE']-a[i]['verdict_token_mean_CE'] for i in ids]
        result['paired_NA32_true_label_loss']=dict(N=32,source='actual_teacher_forced_GT_token_CE',not_calibrated_class_probability=True,
            mean107=statistics.mean(a[i]['verdict_token_mean_CE'] for i in ids),mean109=statistics.mean(z[i]['verdict_token_mean_CE'] for i in ids),
            mean_delta=statistics.mean(diff),median_delta=statistics.median(diff),increased=sum(x>0 for x in diff),decreased=sum(x<0 for x in diff),
            original_segmented_loss_mean107=statistics.mean(a[i]['original_segmented_loss'] for i in ids),original_segmented_loss_mean109=statistics.mean(z[i]['original_segmented_loss'] for i in ids))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=analyze(a.old,a.work);c.put(a.output,r);print(c.canonical(r))
