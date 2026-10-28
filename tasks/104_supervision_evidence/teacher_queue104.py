"""Prepare source-verified existing-teacher comparisons after blind freeze.

No GT join or real queue work occurs on import. The CLI requires an explicit
export/apply action. A manual semantic decision, not lexical overlap, determines
reuse, revision, rejection, or quarantine. All explanation bodies remain private.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from pathlib import Path
import argparse

import common104 as c
import build104 as b
import training104 as t

ACTIONS={'reuse','revise','reject_teacher_keep_blind','new_draft','quarantine'}


def teacher_priority(teacher):
    return (0 if teacher.get('model')=='R1-70B' else 1,
            teacher.get('model',''),teacher.get('rater_alias',''),
            c.digest(teacher.get('reason') or ''))


def choose_teacher(case,GT,teachers):
    eligible=[];excluded=Counter()
    for teacher in teachers:
        if teacher.get('proposition_id')!=case['id']:
            continue
        if teacher.get('claim_sha256')!=c.digest(case['claim']):
            excluded['claim_mismatch']+=1;continue
        if teacher.get('reference_id')!=case['reference_id'] or teacher.get('reference_sha256')!=c.digest(case['reference']):
            excluded['reference_mismatch']+=1;continue
        if teacher.get('verdict')!=GT:
            excluded['teacher_prediction_differs_from_original_GT']+=1;continue
        if not isinstance(teacher.get('reason'),str) or not teacher['reason'].strip():
            excluded['reason_missing']+=1;continue
        eligible.append(teacher)
    eligible.sort(key=teacher_priority)
    return (eligible[0] if eligible else None),len(eligible),dict(excluded)


def artifact(path):
    path=Path(path)
    return path.relative_to(c.ROOT).as_posix() if path.is_relative_to(c.ROOT) else str(path)


def frozen_write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=data:raise ValueError('Refuse to replace a frozen teacher comparison queue')
    else:path.write_bytes(data)


def candidate_context(private,out):
    # Guard the operation before GT keys, candidate answers, or teachers are read.
    b.load_frozen_reviews(private,out)
    manifest_path=out/'candidate_paired_manifest.json'
    if not manifest_path.is_file():raise ValueError('Build the frozen blind candidate package before teacher comparisons')
    manifest=c.read(manifest_path)
    if manifest.get('candidate_only') is not True:raise ValueError('Expected the original blind candidate package')
    pair=private/'candidate_paired'
    paths=(pair/'label_only.jsonl',pair/'evidence_brief.jsonl',private/'review_joined_initial.jsonl')
    for path in paths:
        if manifest['files'].get(artifact(path))!=c.sha(path):raise ValueError('Original blind candidate source changed')
    labels=t.load_rows(paths[0]);briefs=t.load_rows(paths[1])
    if [r['id'] for r in labels]!=manifest['paired_ids'] or len(labels)!=manifest['N']:
        raise ValueError('Candidate IDs/order differ from manifest')
    train={r['id']:r for r in c.lines(private/'train512_original.jsonl')}
    for label,brief in zip(labels,briefs):
        source=train[label['id']]
        if any(label[k]!=source[k] for k in ('id','sid','author','GT','claim','reference','reference_id')):
            raise ValueError('Candidate changed original training input or physician label')
    if labels:t.validate_pairs(labels,briefs,{r['sid'] for r in train.values()})
    joined={r['id']:r for r in c.lines(paths[2])}
    if any(joined[r['id']]['final_status']!='candidate_gt_explained' for r in labels):
        raise ValueError('Only original candidate_gt_explained cases enter this queue')
    return labels,briefs,joined,manifest_path


def export_queue(private,out):
    labels,briefs,joined,manifest_path=candidate_context(private,out)
    teacher_path=private/'teachers_same_reference.jsonl'
    teachers=c.lines(teacher_path)
    by_id=defaultdict(list)
    training_ids={r['id'] for r in c.lines(private/'train512_original.jsonl')}
    for teacher in teachers:
        if teacher['proposition_id'] not in training_ids:raise ValueError('Teacher asset contains a non-training ID')
        by_id[teacher['proposition_id']].append(teacher)
    queue=[]
    for label,brief in zip(labels,briefs):
        teacher,count,excluded=choose_teacher(label,label['GT'],by_id[label['id']])
        source=None
        if teacher is not None:
            source={k:teacher[k] for k in ('model','rater_alias','verdict','reason','reference_id','reference_sha256','claim_sha256')}
            source.update(reason_sha256=c.digest(teacher['reason']),record_sha256=c.digest(c.canonical(teacher)),
                          reasoning_chain_present=bool(teacher.get('reasoning_chain')),
                          reasoning_final_answer_present=bool(teacher.get('reasoning_final_answer')))
        first=joined[label['id']]
        row={k:label[k] for k in ('id','sid','GT','author','claim','reference','reference_id','reference_sha256','claim_sha256')}
        row.update(review_index=first['review_index'],independent_verdict=first['independent_verdict'],certainty=first['certainty'],
                   blind_relation=t.parse_answer(brief,'evidence_brief')['relation'],
                   blind_evidence_quotes=t.parse_answer(brief,'evidence_brief')['evidence'],
                   blind_na_anchor=first['na_anchor'],blind_review_sha256=first['source_review_sha256'],
                   blind_answer_sha256=c.digest(brief['answer']),
                   teacher=source,same_reference_correct_reason_candidates=count,
                   excluded_teacher_counts=excluded,new_draft_required=source is None,
                   source_semantic_approval=False)
        row['queue_item_sha256']=c.digest(c.canonical(row))
        queue.append(row)
    path=private/'teacher_queue.jsonl'
    frozen_write(path,''.join(c.canonical(r)+'\n' for r in queue).encode('utf-8'))
    manifest=dict(created_utc=c.utc(),N=len(queue),selection_rule='R1-70B first, then model ID, rater_alias and reason SHA; same claim/reference and teacher prediction equals original GT required',
                  queue_sha256=c.sha(path),blind_freeze_sha256=c.sha(out/'blind_review_freeze.json'),
                  original_candidate_manifest_sha256=c.sha(manifest_path),teacher_asset_sha256=c.sha(teacher_path),
                  builder_sha256=c.sha(Path(__file__)),new_API_calls=0,
                  GT_modified=False,teacher_agreement_is_not_semantic_approval=True,
                  coverage_by_GT={g:dict(N=sum(r['GT']==g for r in queue),teacher_available=sum(r['GT']==g and r['teacher'] is not None for r in queue),new_draft_required=sum(r['GT']==g and r['new_draft_required'] for r in queue)) for g in c.LABELS},
                  selected_teacher_models=dict(Counter(r['teacher']['model'] for r in queue if r['teacher'])),
                  ids=[r['id'] for r in queue])
    target=out/'teacher_queue_manifest.json'
    if target.exists():
        previous=c.read(target)
        manifest['created_utc']=previous['created_utc']
    frozen_write(target,(c.canonical(manifest)+'\n').encode('utf-8'))
    return manifest


def apply_decisions(private,out,decision_path,allow_partial=False):
    labels,briefs,joined,candidate_manifest=candidate_context(private,out)
    queue_path=private/'teacher_queue.jsonl';queue_manifest=c.read(out/'teacher_queue_manifest.json')
    if c.sha(queue_path)!=queue_manifest['queue_sha256'] or c.sha(candidate_manifest)!=queue_manifest['original_candidate_manifest_sha256']:
        raise ValueError('Teacher queue or source candidate package changed after queue freeze')
    queue=c.lines(queue_path);qmap={r['id']:r for r in queue}
    decisions=c.lines(decision_path);dmap={r['id']:r for r in decisions}
    if len(dmap)!=len(decisions) or set(dmap)-set(qmap):raise ValueError('Duplicate or out-of-queue teacher decision')
    if not allow_partial and set(dmap)!=set(qmap):raise ValueError('Finish every teacher comparison or explicitly mark partial')
    left=[];right=[];records=[];private_records=[]
    for label,brief in zip(labels,briefs):
        identifier=label['id'];q=qmap[identifier]
        if identifier not in dmap:
            records.append(dict(id=identifier,GT=q['GT'],action='pending',included=False));continue
        decision=dmap[identifier];action=decision.get('action')
        if action not in ACTIONS:raise ValueError('Unknown teacher decision action')
        if not decision.get('reviewer') or not decision.get('grounding_assessment') or decision.get('semantic_checked') is not True:
            raise ValueError('Teacher decision requires actual reviewer and substantive semantic assessment')
        teacher=q['teacher']
        if teacher and decision.get('teacher_reason_sha256')!=teacher['reason_sha256']:
            raise ValueError('Decision must identify the exact teacher reason reviewed')
        if action in {'reuse','revise'}:
            if teacher is None:raise ValueError('No existing teacher reason is available for reuse')
            if not isinstance(decision.get('retained_teacher_facts'),list) or not decision['retained_teacher_facts']:
                raise ValueError('Reuse requires explicit factual material actually retained from the teacher')
            relation=decision.get('relation',teacher['reason'] if action=='reuse' else None)
            if not isinstance(relation,str) or not relation.strip():raise ValueError('A final relationship explanation is required')
            if action=='reuse' and relation!=teacher['reason']:raise ValueError('Edited teacher text must be labelled revise, not exact reuse')
            if action=='revise' and (relation==teacher['reason'] or not decision.get('revision_notes')):
                raise ValueError('Revision requires an actual edited relationship and explicit changes')
        elif action=='new_draft':
            if teacher is not None:raise ValueError('An available teacher must be explicitly rejected before keeping a new draft')
            relation=decision.get('relation',q['blind_relation'])
        elif action=='reject_teacher_keep_blind':
            if teacher is None:raise ValueError('No teacher exists to reject')
            relation=q['blind_relation']
            if decision.get('relation',relation)!=relation:
                raise ValueError('This action keeps the documented blind relation; use an explicit new revision action for changes')
        else:relation=q['blind_relation']
        included=action!='quarantine'
        provenance=dict(id=identifier,GT=q['GT'],action=action,included=included,reviewer=decision['reviewer'],
                        teacher_model=teacher['model'] if teacher else None,
                        teacher_rater_alias=teacher['rater_alias'] if teacher else None,
                        teacher_reason_sha256=teacher['reason_sha256'] if teacher else None,
                        teacher_record_sha256=teacher['record_sha256'] if teacher else None,
                        source_queue_item_sha256=q['queue_item_sha256'],
                        final_relation_sha256=c.digest(relation) if included else None)
        records.append(provenance)
        private_records.append(dict(provenance,decision=decision,original_teacher=teacher,
                                    blind_relation=q['blind_relation'],final_relation=relation if included else None))
        if not included:continue
        quotes=decision.get('evidence_quotes',q['blind_evidence_quotes'])
        spans,issues=b.evidence_spans(q['reference'],quotes)
        na_anchor=decision.get('na_anchor',q['blind_na_anchor'])
        if issues:raise ValueError('A proposed teacher-derived answer contains non-source quotations')
        if not quotes and (q['GT']!='Not Addressed' or na_anchor!='none'):
            raise ValueError('Only reviewed no_anchor_na can omit evidence')
        if not isinstance(relation,str) or not relation.strip():raise ValueError('A nonempty final relation is required')
        metadata=deepcopy(label['metadata'])
        metadata.update(evidence_spans=spans,no_anchor_na=not quotes and q['GT']=='Not Addressed',
                        teacher_semantic_reviewed=True,teacher_review=provenance,
                        relation_origin={'reuse':'existing_teacher_exact','revise':'existing_teacher_revised','reject_teacher_keep_blind':'blind_draft_teacher_rejected','new_draft':'blind_new_draft_no_eligible_teacher'}[action])
        first=deepcopy(label);second=deepcopy(brief)
        first['metadata']=deepcopy(metadata);second['metadata']=deepcopy(metadata)
        answer=c.canonical(dict(evidence=quotes,relation=relation,verdict=q['GT']))
        second.update(answer=answer,answer_text=answer)
        if {k:v for k,v in first.items() if k not in {'answer','answer_text'}}!={k:v for k,v in second.items() if k not in {'answer','answer_text'}}:
            raise ValueError('Teacher integration changed paired input/metadata')
        t.parse_answer(first,'label_only');t.parse_answer(second,'evidence_brief')
        left.append(first);right.append(second)
    target=private/'candidate_teacher_checked'
    c.putl(target/'label_only.jsonl',left);c.putl(target/'evidence_brief.jsonl',right)
    c.putl(private/'teacher_decision_history.jsonl',private_records)
    decision_sha=c.sha(decision_path)
    snapshot=private/'teacher_decision_snapshots'/decision_sha
    frozen_write(snapshot/'decisions.jsonl',Path(decision_path).read_bytes())
    frozen_write(snapshot/'history.jsonl',''.join(c.canonical(r)+'\n' for r in private_records).encode('utf-8'))
    c.putl(out/'teacher_provenance.jsonl',records)
    if left:t.validate_pairs(left,right,{r['sid'] for r in labels})
    manifest=dict(created_utc=c.utc(),N=len(left),source_candidate_N=len(labels),
                  candidate_only=True,all_teacher_comparisons_complete=len(dmap)==len(qmap),
                  pending=len(qmap)-len(dmap),actions=dict(Counter(r['action'] for r in records)),
                  retained_GT=dict(Counter(r['GT'] for r in left)),
                  actions_by_GT={g:dict(Counter(r['action'] for r in records if r['GT']==g)) for g in c.LABELS},
                  source_queue_sha256=c.sha(queue_path),manual_decisions_sha256=c.sha(decision_path),
                  immutable_decision_snapshot=artifact(snapshot/'decisions.jsonl'),
                  immutable_history_sha256=c.sha(snapshot/'history.jsonl'),
                  original_blind_candidate_manifest_sha256=c.sha(candidate_manifest),
                  files={artifact(p):c.sha(p) for p in [target/'label_only.jsonl',target/'evidence_brief.jsonl',private/'teacher_decision_history.jsonl']},
                  private_raw_explanations_not_published=True,GT_modified=False,
                  lexical_matching_not_semantic_approval=True,new_API_calls=0,
                  fixed_quality_audit_not_yet_implied=True,paired_ids=[r['id'] for r in left])
    c.put(out/'candidate_teacher_checked_manifest.json',manifest)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--export-queue',action='store_true')
    action.add_argument('--apply-decisions',type=Path)
    parser.add_argument('--private',type=Path,default=c.PRIVATE)
    parser.add_argument('--out',type=Path,default=c.OUT)
    parser.add_argument('--allow-partial',action='store_true')
    args=parser.parse_args()
    result=export_queue(args.private,args.out) if args.export_queue else apply_decisions(args.private,args.out,args.apply_decisions,args.allow_partial)
    print(c.canonical(result))


if __name__=='__main__':main()
