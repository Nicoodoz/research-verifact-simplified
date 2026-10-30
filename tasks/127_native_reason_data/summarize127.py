"""Publish counts and redacted review decisions; never publish clinical targets."""
from collections import Counter
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[2]


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reviews', type=Path, required=True)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--out', type=Path, default=ROOT/'outputs/127_native_reason_data')
    a = p.parse_args()
    review = rows(a.reviews)
    if len({r['id'] for r in review}) != len(review):
        raise ValueError('Duplicate reviewed ID')
    approved = [r for r in review if r['review']['status']=='approved']
    unresolved = [r for r in review if r['review']['status']!='approved']
    manifest = json.loads((a.dataset/'manifest.json').read_text(encoding='utf-8'))
    if manifest['reliable_paired_N'] != len(approved):
        raise ValueError('Reviewed approval count differs from actual dataset')
    old = [r for r in review if r['source_provenance']['old105_paired']]
    new_approved = [r for r in approved if not r['source_provenance']['old105_paired']]
    count = lambda r: dict(sorted(Counter(x['GT'] for x in r).items()))
    summary = dict(
        status='CPU_DATA_PREPARATION_COMPLETE_NOT_EFFECT_VALIDATED',
        original_pool_N=manifest['original_pool_N'],
        patient_split=dict(train=32,validation=8),
        reviewed_N=len(review),reviewed_class_counts=count(review),
        reliable_paired_N=len(approved),reliable_class_counts=count(approved),
        reliable_by_role_GT=dict(sorted(Counter(x['fit_role']+'/'+x['GT'] for x in approved).items())),
        unresolved_N=len(unresolved),unresolved_class_counts=count(unresolved),
        not_reviewed_N=manifest['original_pool_N']-len(review),
        all_label_only_N=manifest['all_label_only_N'],
        prior105_same_ID_N=len(old),
        prior105_comparison=dict(sorted(Counter(x['legacy_comparison']['assessment'] for x in old).items())),
        newly_usable_beyond105_N=len(new_approved),newly_usable_class_counts=count(new_approved),
        teacher_disagreement_reviewed_N=sum(x['source_provenance']['teacher_disagreement'] for x in review),
        teacher_disagreement_approved_N=sum(x['source_provenance']['teacher_disagreement'] for x in approved),
        unresolved_issue_counts=dict(sorted(Counter(c for x in unresolved for c in x['issue_codes']).items())),
        expanded_after_pilot=False,
        stop_reason='No demonstrated substantive semantic improvement on the12 prior105 pairs; only3 additional defensible reasons, including0 NS. Do not mass-generate to a quota.',
        original_GT_changed=False,original_claim_or_reference_changed=False,
        selection20_used=False,confirmation40_used=False,
        new_GPU_training=False,new_paid_API_calls=0,
        clinical_reason_source='AI-assisted Codex primary review and cross-review; not physician-authored or independently clinically certified',
        classifier_benefit_tested=False,
        dataset_private_path=str(a.dataset.resolve().relative_to(ROOT)).replace('\\','/'))
    write(a.out/'summary.json',summary)
    sanitized=[]
    for r in review:
        sanitized.append(dict(id=r['id'],GT=r['GT'],fit_role=r['fit_role'],
            review_status=r['review']['status'],ai_assisted=True,
            prior105_paired=r['source_provenance']['old105_paired'],
            historical_teacher_disagreement=r['source_provenance']['teacher_disagreement'],
            issue_codes=r['issue_codes'],legacy_assessment=r['legacy_comparison']['assessment'],
            reason_sentence_count=r['review']['sentence_count'],
            evidence_span_count=sum(x['kind']=='reference_span' for x in r['evidence_sources']),
            full_reference_primary_review=r['review']['primary_full_reference_read']))
    (a.out/'review_status_sanitized.jsonl').write_bytes(
        ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in sanitized).encode('utf-8'))
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
