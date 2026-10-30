"""Select a small training-patient semantic pilot; no model calls or GT changes."""
from pathlib import Path
from collections import Counter
import hashlib,json

ROOT=Path(__file__).resolve().parents[2]
PRIVATE=ROOT/'.local_models/127_native_reason_data'
LABELS=('Supported','Not Supported','Not Addressed')
def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def digest(value):return hashlib.sha256(value.encode('utf-8')).hexdigest()
def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def main():
    pool=rows(ROOT/'.local_models/106_label_preparation/training_pool.jsonl')
    split_rows=rows(ROOT/'.local_models/117_verdict_probe/metadata.jsonl')
    patient_role={str(r['sid']):r['role'] for r in split_rows if r['role'] in ('train','validation')}
    screen_patients={str(r['sid']) for r in split_rows if r['role']=='screen'}
    assert Counter(patient_role.values())=={'train':32,'validation':8}
    assert len(pool)==3675 and len({r['id'] for r in pool})==3675
    assert {str(r['sid']) for r in pool}==set(patient_role)
    assert not set(patient_role)&screen_patients
    old=rows(ROOT/'.local_models/104_supervision_evidence/paired/evidence_brief.jsonl')
    old_by={r['id']:r for r in old}
    old_review={r['id']:r for r in rows(ROOT/'.local_models/104_supervision_evidence/review_joined.jsonl')}
    training_review={r['id']:r for r in rows(ROOT/'.local_models/106_label_preparation/semantic_B_private.jsonl')}
    assert all(str(r['sid']) in patient_role for r in training_review.values())
    selected=[]
    for label in LABELS:
        for role,kept_n,other_n in [('train',3,3),('validation',1,1)]:
            eligible=[r for r in pool if r['GT']==label and patient_role[str(r['sid'])]==role]
            kept=sorted((r for r in eligible if r['id'] in old_by),key=lambda r:digest('127/pilot/kept/'+r['id']))
            assert len(kept)>=kept_n
            chosen=kept[:kept_n]
            rest=[r for r in eligible if r['id'] not in old_by]
            # Disagreement triggers inspection and never decides whether a reason is admissible.
            def key(r):
                reviewed=r['id'] in training_review
                disagrees=r.get('paper_r1')!=r['GT']
                tagged=bool(old_review.get(r['id'],{}).get('issue_tags'))
                return (not reviewed,not disagrees,not tagged,digest('127/pilot/boundary/'+r['id']))
            chosen+=sorted(rest,key=key)[:other_n]
            assert len(chosen)==kept_n+other_n
            for r in chosen:
                selected.append(dict(r,fit_role=role,old105_paired=r['id'] in old_by,
                    teacher_disagreement=r.get('paper_r1')!=r['GT'],
                    old_review_available=r['id'] in old_review,
                    train106_review_available=r['id'] in training_review,
                    claim_sha256=digest(r['claim']),reference_sha256=digest(r['reference'])))
    assert len(selected)==len({r['id'] for r in selected})==24
    selected.sort(key=lambda r:(LABELS.index(r['GT']),r['fit_role'],not r['old105_paired'],r['id']))
    PRIVATE.mkdir(parents=True,exist_ok=True)
    target=PRIVATE/'pilot24_inputs.jsonl'
    payload=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in selected).encode()
    if target.exists() and target.read_bytes()!=payload:raise ValueError('Preserve an existing pilot; do not silently reselect')
    target.write_bytes(payload)
    prior=[dict(id=r['id'],old105=old_by.get(r['id']),old104_review=old_review.get(r['id']),
                train106_review=training_review.get(r['id'])) for r in selected]
    (PRIVATE/'pilot24_legacy.jsonl').write_bytes(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prior).encode())
    summary=dict(N=24,train_patients=32,validation_patients=8,source_pool=3675,
        pilot_patients=len({r['sid'] for r in selected}),
        by_role_label={f'{role}/{label}':sum(r['fit_role']==role and r['GT']==label for r in selected)
                       for role in ('train','validation') for label in LABELS},
        old105_paired=sum(r['old105_paired'] for r in selected),
        teacher_disagreement=sum(r['teacher_disagreement'] for r in selected),
        train106_review=sum(r['train106_review_available'] for r in selected),
        selection20_or_confirmation40_used=False,new_GPU=False,new_paid_API=False,
        reasons_generated=False,quality_not_yet_assessed=True)
    put(PRIVATE/'pilot24_selection.json',summary)
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
