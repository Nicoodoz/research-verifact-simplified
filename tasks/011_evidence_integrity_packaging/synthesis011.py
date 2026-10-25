"""Summaries of repeated observations; no pooled performance or new labels."""
from pathlib import Path
from collections import Counter
import argparse
import study011 as s

def run(out):
    src=s.OUT/'pilot_analysis_001';s.check(src)
    rows=s.pilot.read_csv(src/'predictions_and_transitions.csv')[1]
    repeats=s.read_json(src/'repeats.json')
    patient=[];classes=[];transfers=[]
    for sid in sorted({r['subject_id'] for r in rows}):
        own=[r for r in rows if r['subject_id']==sid]
        correct={a:sum(r[a]==r['human_gt'] for r in own) for a in s.METHODS}
        patient.append(dict(subject_id=sid,unique_claims=len({r['proposition_id'] for r in own}),observations=len(own),**correct,
            B_minus_A=correct['B']-correct['A'],C_minus_B=correct['C']-correct['B'],C_minus_A=correct['C']-correct['A']))
    for author in ('llm','human'):
        for label in ('Supported','Not Supported','Not Addressed'):
            own=[r for r in rows if r['author_type']==author and r['human_gt']==label]
            classes.append(dict(author=author,label=label,unique_claims=len(own)//3,observations=len(own),**{a:sum(r[a]==label for r in own) for a in s.METHODS}))
        for before,after in (('B','C'),('A','B'),('A','C')):
            own=[r for r in rows if r['author_type']==author]
            transfers.append(dict(author=author,contrast=after+'_minus_'+before,**dict(Counter(r[after+'_minus_'+before] for r in own))))
    aa=s.pilot.read_csv(s.OUT/'pilot_preparation_001/assignments.csv')[1]
    normalized=s.pilot.jsonl(src/'normalized_responses.jsonl')
    chosen=s.read_json(s.TASK/'case_notes.json')['cases']
    selected={r['case_id'] for r in chosen}
    summary=dict(pilot_unique_claims=24,repeat_rounds=3,independent_claims_are_not_72=True,main_executed=False,
        budget_estimate_cny=s.read_json(src/'summary.json')['cost_cny'],
        failures=len(s.read_json(src/'summary.json')['failures']),
        read_cases=len(selected),read_logical_outputs=sum(a['case_id'] in selected for a in aa),
        read_distinct_outputs=len({a['request_id'] for a in aa if a['case_id'] in selected}),
        adherence_flags=dict(Counter(e for r in normalized for e in r['adherence_errors'])),
        all_variation_cases={a:[r['case_id'] for r in repeats if r['varying'][a]] for a in s.METHODS},
        status='Predefined pilot gate negative; main prepared but never run; execution completed pending independent review.')
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_csv(out/'patient_repeated_correct.csv',patient)
    s.pilot.write_csv(out/'class_repeated_correct.csv',classes)
    s.pilot.write_csv(out/'transitions_by_author.csv',transfers)
    s.pilot.write_json(out/'summary.json',summary)
    s.seal(out,[src/'manifest.json',s.OUT/'case_analysis_001/manifest.json'],[Path(__file__)])
    print(s.pilot.canonical(dict(summary=summary,patients=patient,classes=classes,transfers=transfers)))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=s.OUT/'synthesis_001')
    run(ap.parse_args().output)
