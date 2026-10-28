"""Freeze a small independent quality panel before any paid answer exists."""
from collections import Counter
import json
from pathlib import Path
import common104 as c
import api104 as api

def choose(rows, maximum, seed):
    return sorted(rows,key=lambda r:c.digest(seed+r['id']))[:maximum]

def main():
    manifest_path=c.OUT/'api_audit_freeze.json'
    if manifest_path.exists():
        freeze=c.read(manifest_path)
        for rel,h in freeze['files'].items():assert c.sha(c.ROOT/rel)==h,rel
        print(c.canonical(dict(already_frozen=True,plan=freeze['plan'])));return
    if (c.PRIVATE/'api_attempts').exists():raise RuntimeError('Cannot select new audit IDs after any paid attempt')
    from build104 import load_frozen_reviews
    load_frozen_reviews(c.PRIVATE,c.OUT)
    joined=c.lines(c.PRIVATE/'review_joined_initial.jsonl')
    teacher_manifest=c.read(c.OUT/'candidate_teacher_checked_manifest.json')
    assert teacher_manifest['all_teacher_comparisons_complete'] and teacher_manifest['pending']==0
    for rel,h in teacher_manifest['files'].items():assert c.sha(c.ROOT/rel)==h,rel
    pair_dir=c.PRIVATE/'candidate_teacher_checked'
    paired={r['id']:r for r in c.lines(pair_dir/'evidence_brief.jsonl')}
    cases={r['id']:r for r in c.lines(c.PRIVATE/'blind_cases.jsonl')}
    candidates=[r for r in joined if r['id'] in paired and r['initial_status']=='candidate_gt_explained']
    disputed=[r for r in joined if r['initial_status']!='candidate_gt_explained' and r['independent_verdict']!=r['GT']]
    quality=[]
    for label in c.LABELS:
        quality+=choose([r for r in candidates if r['GT']==label],16,'104_quality_audit_v1')
    disputes=choose(disputed,16,'104_dispute_audit_v1')
    jobs=[];samples=[]
    for phase,selected in [('quality',quality),('dispute',disputes)]:
        for row in selected:
            case=cases[row['id']]
            if phase=='quality':answer=json.loads(paired[row['id']]['answer'])
            else:
                answer=dict(evidence=row['evidence_quotes'],relation=row['relation'],verdict=row['GT'],
                            review_context='This relation was independently drafted BEFORE seeing the original label; it may not justify that label. Do not force agreement. Assess whether the current reference can bridge the mismatch, or contains missing/ambiguous facts. This is not a training candidate.',
                            blind_verdict=row['independent_verdict'])
            request=api.body(case,answer)
            rid=c.digest(c.canonical(dict(task=104,phase=phase,id=row['id'],body=request)))[:24]
            jobs.append(dict(request_id=rid,id=row['id'],phase=phase,GT=row['GT'],body=request,
                             reference_sha256=case['reference_sha256'],source_review_sha256=row['source_review_sha256'],
                             max_busy_reservation_cny=api.reserve_nano(request)/1e9))
            samples.append(dict(id=row['id'],GT=row['GT'],phase=phase,request_id=rid,reference_sha256=case['reference_sha256']))
    # Three failed/unknown attempts of the largest request fit the retained reserve
    # only if no other retry has consumed it; the runtime enforces each attempt.
    bound=sum(api.reserve_nano(j['body']) for j in jobs)/1e9
    if bound>16:raise RuntimeError(f'Fixed auxiliary panel upper bound {bound:.6f} leaves insufficient recovery room; reduce balanced audit BEFORE sending')
    c.putl(c.PRIVATE/'api_jobs.jsonl',jobs);c.putl(c.OUT/'api_audit_samples.jsonl',samples)
    plan=dict(quality_N=len(quality),dispute_N=len(disputes),total=len(jobs),hard_cap_cny=20,operating_line_cny=18,
              first_attempt_all_busy_byte_bound_cny=bound,anomaly_reserve_cny=2,
              quality_by_GT=dict(Counter(r['GT'] for r in quality)),dispute_by_GT=dict(Counter(r['GT'] for r in disputes)),
              quality_seed='104_quality_audit_v1',dispute_seed='104_dispute_audit_v1',
              selection_not_based_on_API_answers=True,GT_only_for_sampling_and_quality_context=True,
              disputes_not_training_candidates=True,no_cache_or_channel_discount_assumed=True)
    c.put(c.OUT/'api_budget_plan.json',plan)
    paths=[c.TASK/x for x in ['api104.py','freeze_api104.py','protocol.md','pricing_verification.md']]
    paths += [c.PRIVATE/'api_jobs.jsonl',pair_dir/'label_only.jsonl',pair_dir/'evidence_brief.jsonl',
              c.PRIVATE/'review_joined_initial.jsonl',c.OUT/'candidate_teacher_checked_manifest.json',
              c.OUT/'blind_review_freeze.json',c.OUT/'api_audit_samples.jsonl',c.OUT/'api_budget_plan.json']
    c.put(manifest_path,dict(utc=c.utc(),model=api.MODEL,endpoint=api.ENDPOINT,plan=plan,
                            files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},
                            verdict_not_relabelled=True,HTTP200_unfavorable_or_invalid_never_retried=True))
    print(c.canonical(plan))

if __name__=='__main__':main()
