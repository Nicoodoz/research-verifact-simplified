"""Tighten literal note candidates with known metadata and inspect visible time order."""
from pathlib import Path
from collections import defaultdict,Counter
import statistics
import alignment_common as s

if __name__=='__main__':
    bb=s.pilot.jsonl(s.OUT/'reference_diagnostics_001/blocks.jsonl')
    subjects={b['subject_id'] for b in bb}
    nn={n['ROW_ID']:n for n in s.pilot.subset_csv(s.RAW/'reference_ehr/ehr_noteevents.csv.gz','SUBJECT_ID',subjects)}
    rows=[]; byref=defaultdict(list)
    for b in bb:
        eligible=[nid for nid in b['literal_matching_note_ids'] if (nn[nid]['CHARTTIME'][11:] or 'Unknown')==b['time']
            and (b['description'] is None or nn[nid]['DESCRIPTION']==b['description'])]
        dates={nid:nn[nid]['CHARTTIME'] for nid in eligible}
        row=dict(case_id=b['case_id'],arm=b['arm'],number=b['number'],date=b['date'],time=b['time'],matching_note_ids=eligible,
            full_charttimes=dates,had_literal_but_metadata_mismatch=bool(b['literal_matching_note_ids']) and not eligible)
        rows.append(row);byref[(b['case_id'],b['arm'])].append(row)
    patient=[]; inversions=[]
    for (cid,arm),part in byref.items():
        singleton={b['matching_note_ids'][0] for b in part if len(b['matching_note_ids'])==1}
        possible={nid for b in part for nid in b['matching_note_ids']}
        patient.append(dict(case_id=cid,arm=arm,uniquely_identified_note_count=len(singleton),possible_note_union=len(possible),
            unresolved=sum(not b['matching_note_ids'] for b in part),ambiguous=sum(len(b['matching_note_ids'])>1 for b in part)))
        known=[b for b in part if b['time']!='Unknown']
        for a,b in zip(known,known[1:]):
            if (a['date'],a['time'])>(b['date'],b['time']):
                left=set(a['full_charttimes'].values());right=set(b['full_charttimes'].values())
                inversions.append(dict(case_id=cid,arm=arm,before=a['number'],after=b['number'],
                    visible_before=a['date']+' '+a['time'],visible_after=b['date']+' '+b['time'],
                    full_before=sorted(left),full_after=sorted(right),
                    consistent_with_full_charttime_order=bool(left and right) and all(x<=y for x in left for y in right)))
    summary=dict(metadata_mismatch_blocks=sum(x['had_literal_but_metadata_mismatch'] for x in rows),
        time_inversions=len(inversions),inversions_consistent_with_full_charttime_order=sum(x['consistent_with_full_charttime_order'] for x in inversions),
        by_arm_means={arm:{k:statistics.mean(x[k] for x in patient if x['arm']==arm) for k in ('uniquely_identified_note_count','possible_note_union','unresolved','ambiguous')} for arm in s.METHODS},
        caveat='Visible Date is CHARTDATE, clock Time is from CHARTTIME; do not infer a sorting-code bug from displayed clock inversions. Note linkage is literal metadata matching, not clinician evidence labels.')
    out=s.OUT/'metadata_linkage_001';out.mkdir(exist_ok=False)
    s.pilot.write_jsonl(out/'block_note_candidates.jsonl',rows)
    s.pilot.write_jsonl(out/'time_order_details.jsonl',inversions)
    s.pilot.write_csv(out/'note_coverage.csv',patient)
    s.pilot.write_json(out/'summary.json',summary)
    s.seal(out,[s.OUT/'reference_diagnostics_001/manifest.json',s.RAW/'reference_ehr/ehr_noteevents.csv.gz'],[Path(__file__)])
    print(s.pilot.canonical(summary))
    print(s.pilot.canonical(inversions[:2]))
