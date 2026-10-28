"""Aggregate supervision diagnostics, not a new classification experiment."""
from collections import Counter
from pathlib import Path
import statistics
import json
import common104 as c

def distribution(rows):
    return dict(N=len(rows),GT=dict(Counter(r['GT'] for r in rows)),
                author=dict(Counter(r['author'] for r in rows)),patients=len({str(r['sid']) for r in rows}))

def summarize():
    from build104 import load_frozen_reviews
    frozen=load_frozen_reviews(c.PRIVATE,c.OUT)
    joined=c.lines(c.PRIVATE/'review_joined.jsonl')
    assert len(joined)==288
    accepted=c.lines(c.PRIVATE/'paired/evidence_brief.jsonl')
    labels=c.lines(c.PRIVATE/'paired/label_only.jsonl')
    assert len(accepted)==len(labels) and all(a['id']==b['id'] and a['GT']==b['GT'] and a['reference_sha256']==b['reference_sha256'] and a['messages']==b['messages'] for a,b in zip(accepted,labels))
    train=c.lines(c.PRIVATE/'train512_original.jsonl');trainmap={r['id']:r for r in train}
    assert len(trainmap)==512
    for row in accepted+labels:
        original=trainmap[row['id']]
        for key in ('id','sid','GT','author','claim','reference','reference_id'):
            assert row[key]==original[key],(row['id'],key)
    reviewed_ids={r['id'] for r in joined};retained_ids={r['id'] for r in accepted}
    unreviewed=[r for r in train if r['id'] not in reviewed_ids]
    assert len(unreviewed)==224 and all(r['GT']=='Supported' for r in unreviewed)
    quarantine=[r for r in joined if r['id'] not in retained_ids]
    api_reviews=c.lines(c.PRIVATE/'api_quality_reviews.jsonl') if (c.PRIVATE/'api_quality_reviews.jsonl').exists() else []
    public_api=[]
    for row in api_reviews:
        result=row['result']
        public_api.append(dict(id=row['id'],phase=row['phase'],request_id=row['request_id'],valid=result.get('valid',False),
                               recommendation=result.get('recommendation'),checks=result.get('checks'),
                               critical_issue_count=len(result.get('critical_issues',[]))))
    c.putl(c.OUT/'api_quality_checks.jsonl',public_api)
    result=dict(task=104,purpose='supervision diagnosis and paired data preparation, NOT model classification',
                asset_scope=distribution(train),reviewed=distribution(joined),unreviewed=distribution(unreviewed),
                retained=distribution(accepted),quarantined=distribution(quarantine),
                state_by_GT={g:dict(Counter(r['final_status'] for r in joined if r['GT']==g)) for g in c.LABELS},
                initial_state_by_GT={g:dict(Counter(r['initial_status'] for r in joined if r['GT']==g)) for g in c.LABELS},
                blind_confusion={g:dict(Counter(r['independent_verdict'] for r in joined if r['GT']==g)) for g in c.LABELS},
                blind_reviewers=dict(Counter(r['reviewer'] for r in frozen)),
                issue_tags_by_status={state:dict(Counter(tag for r in joined if r['final_status']==state for tag in r['issue_tags'])) for state in ('gt_explained','reference_gap','unresolved')},
                accepted_no_anchor_na=sum(r['metadata']['no_anchor_na'] for r in accepted),
                retained_teacher_actions=dict(Counter(r['metadata']['teacher_review']['action'] for r in accepted)),
                retained_teacher_actions_by_GT={g:dict(Counter(r['metadata']['teacher_review']['action'] for r in accepted if r['GT']==g)) for g in c.LABELS},
                relation_words=dict(N=len(accepted),min=min((len(json.loads(r['answer'])['relation'].split()) for r in accepted),default=0),
                                    mean=statistics.mean([len(json.loads(r['answer'])['relation'].split()) for r in accepted]) if accepted else 0,
                                    max=max((len(json.loads(r['answer'])['relation'].split()) for r in accepted),default=0)),
                independent_API=dict(total=len(public_api),by_phase={phase:dict(N=sum(r['phase']==phase for r in public_api),valid_N=sum(r['phase']==phase and r['valid'] for r in public_api),recommendations=dict(Counter(r['recommendation'] or 'invalid' for r in public_api if r['phase']==phase))) for phase in ('quality','dispute')}),
                original_GT_modified=False,new_classification_predictions=0,new_GPU=0,
                patient_scope='103 train40 only; no selection/confirmation clinical data used',
                result_scope='machine-assisted supervision, not new physician gold or proof of full chain-of-thought learning')
    # Count retained and quarantined rows against original input/annotation quality,
    # without treating physician disagreement as permission to change a label.
    assets={r['id']:r for r in c.lines(c.OUT/'asset_inventory512.jsonl')}
    quality={}
    for state in ('gt_explained','reference_gap','unresolved'):
        ids={r['id'] for r in joined if r['final_status']==state}
        subset=[assets[i] for i in ids]
        quality[state]=dict(N=len(subset),initial_three_agree=sum(int(r['round1_num_raters_agree'])==3 for r in subset),
                            paper_r1_matches_GT=sum(r['paper_r1_matches_GT'] for r in subset),
                            any_same_reference_correct_reason=sum(r['same_reference_correct_reason_candidates']>0 for r in subset),
                            by_GT={g:dict(N=sum(r['GT']==g for r in subset),initial_three_agree=sum(r['GT']==g and int(r['round1_num_raters_agree'])==3 for r in subset),
                                          same_reference_correct_reason=sum(r['GT']==g and r['same_reference_correct_reason_candidates']>0 for r in subset)) for g in c.LABELS})
    result['annotation_and_teacher_association']=quality
    result['annotation_disagreement_does_not_invalidate_original_GT']=True
    # 105 correction: preserve the published summary bound by 104 complete.json.
    target='supervision_summary_corrected.json' if (c.OUT/'complete.json').exists() else 'supervision_summary.json'
    c.put(c.OUT/target,result)
    c.put(c.OUT/'analysis_inputs.json',dict(files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [c.PRIVATE/'paired/label_only.jsonl',c.PRIVATE/'paired/evidence_brief.jsonl',c.PRIVATE/'review_joined.jsonl',c.OUT/'blind_review_freeze.json',c.OUT/'paired_manifest.json']},
                                        no_model_evaluation_or_training=True,no_historical_rewrites=True))
    return result

if __name__=='__main__':
    result=summarize()
    print(c.canonical({k:result[k] for k in ('reviewed','retained','quarantined','state_by_GT','independent_API')}))
