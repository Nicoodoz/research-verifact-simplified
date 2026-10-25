"""Full-cohort source provenance, overlap, displacement and fixed anchor lookup."""
from collections import Counter
from pathlib import Path
import argparse
import study011 as s

def run(out):
    off=s.OUT/'offline_003';s.check(off)
    records=s.pilot.jsonl(off/'inputs.jsonl')
    views={r['passage_id']:r['views'] for r in s.pilot.jsonl(off/'views.jsonl')}
    subjects={r['subject_id'] for r in records}
    notes={n['ROW_ID']:n for n in s.pilot.subset_csv(s.RAW/'reference_ehr/ehr_noteevents.csv.gz','SUBJECT_ID',subjects)}
    for key,v in views.items():
        original=v['A'];note=notes[original['note_id']];text=note['TEXT']
        for a in s.METHODS:
            p=v[a]
            assert p['subject_id']==note['SUBJECT_ID'] and p['note_id']==note['ROW_ID']
            assert p['note_sha256']==s.pilot.digest_text(text)
            assert p['text']==text[p['start']:p['end_exclusive']] and p['description']==note['DESCRIPTION']
            assert p['start']<=original['start'] and p['end_exclusive']>=original['end_exclusive']
            for h in p.get('source_context',[]):
                assert h['text']==text[h['start']:h['end_exclusive']]
                assert h['scope_start']<=p['start'] and p['end_exclusive']<=h['scope_end']
    changes=[];heads=Counter();overlaps=[]
    for r in records:
        aa,bb,cc=[r['retrieval'][a] for a in s.METHODS]
        changes.append(dict(case_id=r['case_id'],author_type=r['author_type'],subject_id=r['subject_id'],
            B_A_changed=bb['reference']!=aa['reference'],C_B_changed=cc['reference']!=bb['reference'],
            B_A_selection_changed=set(bb['selected_ids'])!=set(aa['selected_ids']),C_B_selection_changed=set(cc['selected_ids'])!=set(bb['selected_ids']),
            C_has_context=any(views[k]['C']['source_context'] for k in cc['selected_ids']),
            B_lost_A=sorted(set(aa['selected_ids'])-set(bb['selected_ids'])),C_lost_B=sorted(set(bb['selected_ids'])-set(cc['selected_ids']))))
        for a in s.METHODS:
            seen=set();total=0
            for k in r['retrieval'][a]['selected_ids']:
                p=views[k][a];chars={(p['note_id'],i) for i in range(p['start'],p['end_exclusive'])}
                total+=len(chars);seen.update(chars)
                if a=='C':heads.update(h['kind']+' / '+h['text'] for h in p['source_context'])
            overlaps.append(dict(case_id=r['case_id'],arm=a,total_raw_span_characters=total,unique_raw_span_characters=len(seen),repeated_same_note_characters=total-len(seen)))
    lookup={r['case_id']:r for r in records}
    anchors=[]
    for x in s.read_json(s.ROOT/'outputs/010_verifact_baseline_alignment/reference_diagnostics_001/009_anchor_lookup.json'):
        row=dict(x);row.pop('hits');r=lookup[x['case_id']]
        row['hits']={a:[k for k in r['retrieval'][a]['selected_ids'] if views[k][a]['note_id']==x['source_note_id'] and ' '.join(x['quote'].split()) in ' '.join(views[k][a]['text'].split())] for a in s.METHODS}
        row['caveat']='Existing literal same-note diagnostic, not full gold evidence or medical recall.'
        anchors.append(row)
    summary=dict(source_views_checked=len(views)*3,headings=dict(heads),
        by_author={a:{k:sum(bool(r[k]) for r in changes if r['author_type']==a) for k in ('B_A_changed','C_B_changed','B_A_selection_changed','C_B_selection_changed','C_has_context')} for a in ('llm','human')},
        overlap_by_arm={a:sum(r['repeated_same_note_characters'] for r in overlaps if r['arm']==a) for a in s.METHODS},
        medical_gold=False,original_claim_not_used_in_repairs=True)
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_json(out/'summary.json',summary)
    s.pilot.write_jsonl(out/'changes.jsonl',changes)
    s.pilot.write_csv(out/'overlap.csv',overlaps)
    s.pilot.write_json(out/'existing_anchor_lookup.json',anchors)
    s.seal(out,[off/'manifest.json',s.RAW/'reference_ehr/ehr_noteevents.csv.gz'],[Path(__file__)])
    print(s.pilot.canonical({k:v for k,v in summary.items() if k!='headings'}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=s.OUT/'input_diagnostics_001')
    run(ap.parse_args().output)
