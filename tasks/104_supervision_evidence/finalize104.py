"""Finalize curated candidates without rescuing blind disagreements by GT.

Every source candidate already has a per-case semantic teacher decision. The
fixed sampled API audit adds a quality gate; flagged responses need an explicit
post-audit decision, never an automatic relabel or best-answer replacement.
"""
from collections import Counter
from copy import deepcopy
import json
import common104 as c
import build104 as b


def quality_pass(result):
    return (result.get('valid') is True and result.get('recommendation')=='retain'
            and not result.get('critical_issues')
            and result.get('checks') and all(result['checks'].values()))


def finalize():
    manifest=c.read(c.OUT/'candidate_teacher_checked_manifest.json')
    assert manifest['all_teacher_comparisons_complete'] and manifest['pending']==0
    for path,sha in manifest['files'].items():assert c.sha(c.ROOT/path)==sha,path
    initial=c.lines(c.PRIVATE/'review_joined_initial.jsonl')
    checked={r['id']:r for r in c.lines(c.PRIVATE/'candidate_teacher_checked/evidence_brief.jsonl')}
    teacher_history={r['id']:r for r in c.lines(c.PRIVATE/'teacher_decision_history.jsonl')}
    audits=c.lines(c.PRIVATE/'api_quality_reviews.jsonl')
    quality={r['id']:r for r in audits if r['phase']=='quality'}
    jobs=c.lines(c.PRIVATE/'api_jobs.jsonl')
    assert {r['request_id'] for r in audits}=={r['request_id'] for r in jobs},'Finish frozen audit or record incomplete; do not call it final'
    path=c.PRIVATE/'post_audit_decisions.jsonl'
    overrides=c.lines(path) if path.exists() else []
    override={r['id']:r for r in overrides}
    assert len(override)==len(overrides)
    assert set(override)<=set(checked)
    decisions=[];quality_status=[]
    for row in initial:
        identifier=row['id'];source=checked.get(identifier)
        if source is None:
            state=row['initial_status']
            if state=='candidate_gt_explained':state='unresolved'
            reason='Initial blind disagreement/uncertainty remains isolated; original physician GT retained.'
            if identifier in teacher_history:
                reason='Candidate was quarantined during explicit teacher semantic curation.'
            decisions.append(dict(id=identifier,reviewer='root_final_assembly',final_status=state,
                                  quality_approved=False,revision_reason=reason))
            continue
        audit=quality.get(identifier)
        passing=audit is None or quality_pass(audit['result'])
        manual=override.get(identifier)
        if not passing and manual is None:
            raise ValueError('A flagged sampled candidate requires an explicit semantic decision: '+identifier)
        answer=json.loads(source['answer'])
        status='gt_explained'
        reason='Per-case source/semantic teacher curation completed; '+('sampled independent API QC passed.' if audit else 'not in fixed API quality sample; no claim of API review.')
        if manual:
            assert manual.get('reviewer') and manual.get('assessment')
            assert manual.get('action') in {'retain','revise','quarantine'}
            reason=manual['assessment']
            if manual['action']=='quarantine':
                status=manual.get('final_status','unresolved')
                assert status in {'reference_gap','unresolved'}
            if manual['action']=='revise':
                assert manual.get('relation') and manual.get('revision_notes')
                answer['relation']=manual['relation']
                if 'evidence_quotes' in manual:answer['evidence']=manual['evidence_quotes']
        metadata={k:deepcopy(source['metadata'][k]) for k in b.SUPERVISION_METADATA_FIELDS}
        if manual:
            metadata['teacher_review']['post_audit_review']=dict(
                action=manual['action'],reviewer=manual['reviewer'],
                decision_sha256=c.digest(c.canonical(manual)),
                output_relation_sha256=c.digest(answer['relation']) if status=='gt_explained' else None)
        decision=dict(id=identifier,reviewer=manual['reviewer'] if manual else 'root_final_assembly',
                      final_status=status,quality_approved=status=='gt_explained',revision_reason=reason,
                      evidence_quotes=answer['evidence'],relation=answer['relation'],
                      na_anchor='none' if not answer['evidence'] else row['na_anchor'],
                      supervision_metadata=metadata)
        decisions.append(decision)
        quality_status.append(dict(id=identifier,GT=row['GT'],sampled_API=audit is not None,
                                   API_pass=quality_pass(audit['result']) if audit else None,
                                   post_audit_action=manual['action'] if manual else None,
                                   final_included=status=='gt_explained'))
    c.putl(c.PRIVATE/'final_decisions.jsonl',decisions)
    result=b.build(c.PRIVATE,c.OUT,c.PRIVATE/'final_decisions.jsonl')
    c.putl(c.OUT/'final_quality_status.jsonl',quality_status)
    c.put(c.OUT/'finalization.json',dict(N=result['N'],GT=result['retained_GT'],
        original_blind_candidates=c.read(c.OUT/'candidate_paired_manifest.json')['N'],
        curated_candidates=manifest['N'],API_quality_N=len(quality),
        flagged_API=sum(not quality_pass(r['result']) for r in quality.values()),
        manual_post_audit_N=len(overrides),manual_actions=dict(Counter(r['action'] for r in overrides)),
        source_checked_manifest_sha256=c.sha(c.OUT/'candidate_teacher_checked_manifest.json'),
        final_decisions_sha256=c.sha(c.PRIVATE/'final_decisions.jsonl'),
        post_audit_decisions_sha256=c.sha(path) if path.exists() else None,
        blind_disagreement_rescued=0,original_GT_modified=False,
        no_claim_all_candidates_independently_API_audited=True))
    return result


if __name__=='__main__':
    result=finalize()
    print(c.canonical({k:result[k] for k in ('N','retained_GT','retained_patients','status_by_GT')}))
