"""Bind selected comparisons to source claims, votes, EHR and C48 pipeline."""
from pathlib import Path
import study012 as s

if __name__=='__main__':
    aligned=s.OUT/'alignment_002';s.check(aligned)
    rows=s.pilot.jsonl(aligned/'aligned_materials.jsonl');chosen=s.read_json(aligned/'selection.json')
    props={p['proposition_id']:p for p in s.pilot.subset_csv(s.RAW/'propositions/propositions.csv.gz','proposition_id',set(chosen))}
    doctors={p['proposition_id']:p for p in s.pilot.subset_csv(s.RAW/'propositions/human_verdicts.csv.gz','proposition_id',set(chosen))}
    validity={p['proposition_id']:p for p in s.pilot.subset_csv(s.RAW/'propositions/proposition_validity.csv.gz','proposition_id',set(chosen))}
    c48={p['proposition_id']:p for p in s.pilot.jsonl(s.NINE/'judge_preparation/inputs.jsonl')}
    corpus=s.pilot.jsonl(s.NINE/'preparation/corpus.jsonl')
    notes=s.pilot.subset_csv(s.RAW/'reference_ehr/ehr_noteevents.csv.gz','SUBJECT_ID',{r['row']['subject_id'] for r in rows})
    indexed={p['note_id'] for p in corpus};nn={n['ROW_ID']:n for n in notes}
    for p in corpus:
        assert p['text']==nn[p['note_id']]['TEXT'][p['start']:p['end_exclusive']]
        assert p['note_sha256']==s.pilot.digest_text(nn[p['note_id']]['TEXT'])
    packets=[]
    for r in rows:
        pid=r['row']['proposition_id']
        if pid not in chosen:continue
        assert props[pid]['text']==r['input']['text']==doctors[pid]['text']
        assert doctors[pid]['human_gt']==r['row']['human_gt'] and validity[pid]['invalid']=='False'
        old=c48[pid];ret=old['retrieval']['C48']
        assert ret['reference']==r['input']['references']['c48_reference']
        pp={p['passage_id']:p for p in corpus}
        reconstructed=s.source.previous.core.select_evidence(ret['candidate_ids'],old['scores'],pp,old['admission'])
        assert reconstructed['reference']==ret['reference']
        packets.append(dict(r,proposition=props[pid],human=doctors[pid],validity=validity[pid],C_pipeline=old,
            raw_scope_notes=[n['ROW_ID'] for n in notes if n['SUBJECT_ID']==r['row']['subject_id']],
            original_pipeline='not available; do not impute C48 ranks to O/V'))
    out=s.OUT/'materials_001';out.mkdir()
    s.pilot.write_jsonl(out/'packets.jsonl',packets)
    s.pilot.write_jsonl(out/'ehr_notes.jsonl',notes)
    s.pilot.write_jsonl(out/'corpus.jsonl',corpus)
    s.pilot.write_json(out/'summary.json',dict(selected=len(packets),raw_notes=len(notes),indexed_notes=len(indexed),source_spans_verified=len(corpus),new_api_calls=0))
    s.seal(out,[aligned/'manifest.json',s.NINE/'judge_preparation/inputs.jsonl',s.NINE/'preparation/corpus.jsonl',s.RAW/'reference_ehr/ehr_noteevents.csv.gz',s.RAW/'propositions/human_verdicts.csv.gz'],[Path(__file__)])
    print([(r['row']['case_id'],r['row']['author_type'],r['row']['subject_id'],r['row']['human_gt'],r['row']['O'],r['row']['V'],r['row']['C'],len(r['original']['reasoning_chain'] or '')) for r in packets])
