"""Metadata ordering and per-patient descriptive reference comparisons."""
from collections import defaultdict,Counter
from pathlib import Path
import statistics
import alignment_common as s
from inspect_references import blocks

if __name__=='__main__':
    prep=s.OUT/'preparation_001'
    inputs=s.pilot.jsonl(prep/'inputs.jsonl')
    rows=[]
    for item in inputs:
        headers={arm:ref[:ref.index('1. Date: ')] for arm,ref in item['references'].items()}
        for arm,ref in item['references'].items():
            bb=blocks(ref)
            known=[b for b in bb if b['time']!='Unknown']
            inversions=[dict(before=a['number'],after=b['number'],before_time=a['date']+' '+a['time'],after_time=b['date']+' '+b['time'])
                for a,b in zip(known,known[1:]) if (a['date'],a['time'])>(b['date'],b['time'])]
            rows.append(dict(case_id=item['case_id'],subject_id=item['subject_id'],arm=arm,matching_admission_header=len(set(headers.values()))==1,
                known_time_adjacent_inversions=inversions,date_inversions=sum(a['date']>b['date'] for a,b in zip(bb,bb[1:])),
                reference_characters=len(ref),clinical_text_characters=sum(len(b['text']) for b in bb),
                mean_text_chars=statistics.mean(len(b['text']) for b in bb),block_count=len(bb)))
    patient=[]
    for sid in sorted({r['subject_id'] for r in rows}):
        for arm in s.METHODS:
            own=[r for r in rows if r['subject_id']==sid and r['arm']==arm]
            patient.append(dict(subject_id=sid,arm=arm,claims=len(own),
                mean_reference_chars=statistics.mean(r['reference_characters'] for r in own),mean_clinical_text_chars=statistics.mean(r['clinical_text_characters'] for r in own),
                refs_with_time_inversion=sum(bool(r['known_time_adjacent_inversions']) for r in own)))
    summary=dict(all_headers_match=all(r['matching_admission_header'] for r in rows),
        by_arm={arm:dict(refs_with_time_inversion=sum(bool(r['known_time_adjacent_inversions']) for r in rows if r['arm']==arm),
            date_inversions=sum(r['date_inversions'] for r in rows if r['arm']==arm)) for arm in s.METHODS},
        inference='Order labels do not prove strict within-day ordering; not a causal outcome test')
    out=s.OUT/'metadata_diagnostics_001'
    out.mkdir(exist_ok=False)
    s.pilot.write_jsonl(out/'order_checks.jsonl',rows)
    s.pilot.write_csv(out/'patient_reference_features.csv',patient)
    s.pilot.write_json(out/'summary.json',summary)
    s.seal(out,[prep/'manifest.json'],[Path(__file__),s.TASK/'inspect_references.py'])
    print(s.pilot.canonical(summary))
