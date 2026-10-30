"""Freeze six diagnostic errors; no selected ID may become training data."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[2]


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def main():
    out=ROOT/'.local_models/131_source_context_probe';out.mkdir(exist_ok=True)
    predictions=rows(ROOT/'outputs/120_full_pool_sft/internal687_predictions_sanitized.jsonl')
    pool={r['id']:r for r in rows(ROOT/'.local_models/106_label_preparation/training_pool.jsonl')}
    reviewed={r['id'] for r in rows(ROOT/'.local_models/127_native_reason_data/protection_extension_reviewed47.jsonl')}
    selected=[];patients=set()
    for label in ('Not Supported','Not Addressed'):
        options=[r for r in predictions if r['GT']==label and r['candidate120']=='Supported'
                 and r['baseline107']!='Supported' and r['id'] not in reviewed]
        for _ in range(3):
            remaining=[r for r in options if r['id'] not in {s['id'] for s in selected}]
            remaining.sort(key=lambda r:(r['sid'] in patients,
                hashlib.sha256(('131/source_probe/v1/'+r['id']).encode()).hexdigest()))
            row=remaining[0];patients.add(row['sid'])
            selected.append(dict(pool[row['id']],baseline107=row['baseline107'],candidate120=row['candidate120']))
    payload=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected).encode()
    target=out/'cases_private.jsonl'
    if target.exists():
        if target.read_bytes()!=payload:raise ValueError('Existing frozen cases differ')
    else:target.write_bytes(payload)
    print(json.dumps(dict(cases=len(selected),patients=len(patients),no_training_use=True)))


if __name__=='__main__':main()
