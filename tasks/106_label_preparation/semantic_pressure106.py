"""Private, lossless-by-map union of pressure references for bounded source reading.

Only ordinal prefixes are deduplicated; every original unit/offset/SHA is retained.
This is a reading aid, not a classifier or a new evidence construction.
"""
from collections import defaultdict
import json
from pathlib import Path
import re
from data106 import ROOT, OUT, PRIVATE, digest, put, putl, rows, read, sha

def assemble_review():
    source_map=read(PRIVATE/'pressure_reading/source_map.json')
    notes=read(PRIVATE/'pressure_reading/review_notes.json')
    cases=[r for r in rows(PRIVATE/'A_source_review_dossiers.jsonl') if r['panel']=='pressure']
    assert set(notes)=={r['id'] for r in cases},'Review every frozen pressure dossier, not just interesting errors'
    public=[];private=[]
    for r in cases:
        note=notes[r['id']]
        mapping=source_map[r['sid']]
        citations=[];quotes=[]
        for purpose in ('decisive_units','counterevidence_units'):
            for identifier in note[purpose]:
                unit=mapping['units'][identifier]
                locations=[x for x in unit['owners'] if x['case_id']==r['id']]
                assert locations,(r['id'],identifier,'unit not in this claim actual reference')
                for location in locations:
                    quoted=r['full_reference'][location['start']:location['end']]
                    assert digest(quoted)==location['sha256']
                    citations.append(dict(purpose=purpose,unit_id=identifier,**location))
                    quotes.append(dict(purpose=purpose,unit_id=identifier,quote=quoted,**location))
        value={k:r[k] for k in ('id','sid','panel','GT','before','after','groups','false_S_added','false_S_prevented','reference_sha256','claim_sha256')}
        value.update({k:v for k,v in note.items() if k not in ('decisive_units','counterevidence_units')})
        value.update(reviewer='106_data_statistics_source_review',full_actual_reference_content_read=True,
            reading_method='All complete units with exact per-case membership; repeated ordinal prefixes and note metadata losslessly interned, no clinical Text field omitted',
            cited_source_locations=citations,reference_characters=len(r['full_reference']),
            new_physician_gold=False,internal_model_mechanism_inferred=False,GT_modified=False,
            no_training_admission_or_prompt_rule_generated_from_development_case=True)
        public.append(value);private.append(dict(value,claim=r['claim'],quoted_units=quotes))
    putl(OUT/'semantic_A_pressure.jsonl',public)
    putl(PRIVATE/'semantic_A_pressure_private_quotes.jsonl',private)
    from collections import Counter
    summary=dict(N=len(public),all_new_false_S=sum(r['false_S_added'] for r in public),
        assessments=dict(Counter(r['assessment'] for r in public)),
        new_false_S_assessments=dict(Counter(r['assessment'] for r in public if r['false_S_added'])),
        boundary_counts=dict(Counter(r['boundary'] for r in public)),
        all_actual_references_read=True,source_citation_membership_checked=True,new_physician_gold=False,
        missing_target_event_does_not_prove_absence_from_full_EHR=True,
        files={str(p.relative_to(ROOT)):sha(p) for p in (PRIVATE/'A_source_review_dossiers.jsonl',PRIVATE/'pressure_reading/source_map.json',PRIVATE/'pressure_reading/review_notes.json')})
    put(OUT/'semantic_A_pressure_summary.json',summary)
    print(json.dumps({k:summary[k] for k in ('N','all_new_false_S','assessments','new_false_S_assessments')}))

def main():
    cases=[r for r in rows(PRIVATE/'A_source_review_dossiers.jsonl') if r['panel']=='pressure']
    grouped=defaultdict(list)
    for r in cases:grouped[r['sid']].append(r)
    counts=[]
    mapping={}
    for sid,group in grouped.items():
        unique={}
        owners=defaultdict(list)
        case_map={}
        for r in group:
            source=r['full_reference']
            previous=0;case_map[r['id']]=[]
            for span in r['complete_unit_spans']:
                assert span['start']==previous and digest(source[span['start']:span['end']])==span['sha256']
                previous=span['end']
                raw=source[span['start']:span['end']]
                canonical=re.sub(r'^\d+\. ', '', raw)
                key=digest(canonical)
                if key not in unique:unique[key]=dict(unit_id=f'U{len(unique)+1:03d}',text=canonical)
                unit=unique[key]
                where=dict(case_id=r['id'],start=span['start'],end=span['end'],sha256=span['sha256'])
                owners[key].append(where);case_map[r['id']].append(unit['unit_id'])
            assert previous==len(source)
        text=[f'PRESSURE PATIENT {sid}; lossless content union, original ordinal prefixes in source map.']
        for r in group:
            text.append(f"CASE {r['id']} | GT {r['GT']} | {r['before']} -> {r['after']} | GROUPS {r['groups']}\nCLAIM: {r['claim']}\nUNITS: {', '.join(case_map[r['id']])}\n")
        for key,unit in unique.items():
            refs='; '.join(f"{x['case_id'][:8]}:{x['start']}-{x['end']}" for x in owners[key])
            text.append(f"[{unit['unit_id']}] OWNERS {refs}\n{unit['text']}\n")
        target=PRIVATE/'pressure_reading'/f'{sid}.txt'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(('\n'.join(text)+'\n').encode('utf-8'))
        # A compact full-content reading view interns repeated note metadata;
        # nothing from the clinical Text field is dropped or summarized.
        notes={}; compact=[]
        for key,unit in unique.items():
            matched=re.fullmatch(r'Date: (.*?), Time: (.*?), Note Category: (.*?), Note Description: (.*?) \| Text: ([\s\S]*)',unit['text'])
            if matched:
                meta=matched.groups()[:4]
                if meta not in notes:notes[meta]=f'N{len(notes)+1:02d}'
                compact.append(f"{unit['unit_id']} {notes[meta]} {matched.group(5)}")
            else:compact.append(f"{unit['unit_id']} {unit['text']}")
        compact_header=[f'PATIENT {sid}. Complete Text fields; shared note metadata interned without deletion.']
        for r in group:compact_header.append(f"CASE {r['id']} | GT {r['GT']} | {r['before']} -> {r['after']} | {r['groups']}\nCLAIM: {r['claim']}\nUNITS {','.join(case_map[r['id']])}")
        compact_header += [f'{code} Date {meta[0]}; Time {meta[1]}; Category {meta[2]}; Description {meta[3]}' for meta,code in notes.items()]
        compact_path=PRIVATE/'pressure_reading'/f'{sid}_compact.txt'
        compact_path.write_bytes(('\n'.join(compact_header+compact)+'\n').encode('utf-8'))
        mapping[sid]=dict(cases=case_map,units={unit['unit_id']:dict(sha256=digest(unit['text']),owners=owners[key],text=unit['text']) for key,unit in unique.items()})
        counts.append(dict(sid=sid,cases=len(group),original_chars=sum(len(r['full_reference']) for r in group),unique_units=len(unique),unique_content_chars=sum(len(u['text']) for u in unique.values())))
    put(PRIVATE/'pressure_reading/source_map.json',mapping)
    print(json.dumps(counts))

if __name__=='__main__':
    import sys
    if '--assemble-review' in sys.argv:assemble_review()
    else:main()
