"""One training-patient source-gap check within existing lawful EHR calendar scope."""
import re
import sys
import duckdb
from data106 import ROOT, OUT, PRIVATE, digest, put, putl, read, rows, sha

def assemble_review():
    summary=read(OUT/'data_ehr_gapcheck.json')
    notes=rows(PRIVATE/'pair_reading/median_gap_legal_EHR_matching_notes.jsonl')
    note=next(r for r in notes if r['ROW_ID']=='637737')
    # The word occurs twice: the later occurrence is inside the explicit action
    # line, not the earlier home-medication list. Preserve exact raw offsets.
    target=note['occurrences'][-1]
    start=note['TEXT'].rfind('\n',0,target['start'])+1
    end=note['TEXT'].find('\n',target['end'])
    end=len(note['TEXT']) if end<0 else end
    quote=note['TEXT'][start:end]
    source=next(r for r in rows(PRIVATE/'training_pool.jsonl') if r['id']==summary['id'])
    assert quote not in source['reference']
    location=dict(note_id=note['ROW_ID'],note_sha256=note['note_sha256'],start=start,end=end,quote_sha256=digest(quote))
    summary.update(semantic_legal_EHR_check_pending=False,full_matching_notes_read=3,
        semantic_result='Additional lawful EHR explicitly records continuing the target home medication; the current actual reference omits that action. This explains an input-evidence gap, not an erroneous doctor GT.',
        decisive_extra_EHR_location=location,evidence_only_in_additional_legal_EHR=True,
        target_medication_continuation_found=True,attribution_of_recommendation_not_independently_resolved=True,
        target_reference_not_augmented=True,original_GT_modified=False,
        independent_physician_adjudication=False)
    put(OUT/'data_ehr_gapcheck.json',summary)
    put(PRIVATE/'pair_reading/median_gap_legal_EHR_decisive_quote.json',dict(location,quote=quote))
    print('Additional lawful EHR contains explicit continuation; current reference unchanged; both candidate arms exclude the source-gap case.')

def main():
    identifier='e5f545ac-9a01-bebf-b501-68692c57fc0c'
    source=next(r for r in rows(PRIVATE/'training_pool.jsonl') if r['id']==identifier)
    allowed=set(read(ROOT/'outputs/103_lora_selection/patient_roles.json')['patients']['train'])
    assert source['sid'] in allowed
    folder=ROOT/'data/00_raw/verifact-bhc/1.1.0/reference_ehr'
    with duckdb.connect() as db:
        cursor=db.execute('SELECT * FROM read_csv_auto(?,all_varchar=true) WHERE SUBJECT_ID=?',[str(folder/'admissions.csv.gz'),source['sid']])
        names=[x[0] for x in cursor.description];admissions=[dict(zip(names,r)) for r in cursor.fetchall()]
        assert len(admissions)==1
        a=admissions[0]
        cursor=db.execute("SELECT ROW_ID,SUBJECT_ID,HADM_ID,CHARTDATE,CHARTTIME,CATEGORY,DESCRIPTION,TEXT FROM read_csv_auto(?,all_varchar=true) WHERE SUBJECT_ID=? AND substr(CHARTDATE,1,10)>=? AND substr(CHARTDATE,1,10)<=? AND lower(trim(CATEGORY))!='discharge summary' ORDER BY CHARTDATE,CHARTTIME,ROW_ID",[str(folder/'ehr_noteevents.csv.gz'),source['sid'],a['ADMITTIME'][:10],a['DISCHTIME'][:10]])
        names=[x[0] for x in cursor.description];notes=[dict(zip(names,r)) for r in cursor.fetchall()]
    pattern=re.compile(r'(?i)lexapro|escitalopram|\bssri\b|antidepressant|selective serotonin')
    matches=[]
    for n in notes:
        positions=[dict(start=m.start(),end=m.end(),term_sha256=digest(m.group())) for m in pattern.finditer(n['TEXT'])]
        if positions:matches.append(dict(n,occurrences=positions,note_sha256=digest(n['TEXT'])))
    putl(PRIVATE/'pair_reading/median_gap_legal_EHR_matching_notes.jsonl',matches)
    put(OUT/'data_ehr_gapcheck.json',dict(id=identifier,sid=source['sid'],GT=source['GT'],original_GT_modified=False,
        admission_id=a['HADM_ID'],calendar_start=a['ADMITTIME'][:10],calendar_end=a['DISCHTIME'][:10],
        existing_scope_rule='100/evidence100.py calendar-inclusive target admission; discharge summaries excluded; training patient only',
        legal_notes_N=len(notes),matched_notes_N=len(matches),
        matched_note_metadata=[{k:n[k] for k in ('ROW_ID','HADM_ID','CHARTDATE','CHARTTIME','CATEGORY','DESCRIPTION','note_sha256','occurrences')} for n in matches],
        current_reference_sha256=digest(source['reference']),current_reference_changed=False,
        no_material_added_to_training_reference=True,raw_source_files={str(p.relative_to(ROOT)):sha(p) for p in (folder/'admissions.csv.gz',folder/'ehr_noteevents.csv.gz')},
        semantic_legal_EHR_check_pending=True,new_API_calls=0,GPU_calls=0))
    print(dict(legal_notes=len(notes),matched_notes=len(matches),matching_note_ids=[n['ROW_ID'] for n in matches]))

if __name__=='__main__':
    if '--assemble-review' in sys.argv:assemble_review()
    else:main()
