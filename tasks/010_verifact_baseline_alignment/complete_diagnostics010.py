"""Receipt-only cost/patient summaries and a targeted raw-source check; no calls."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import alignment_common as s


def run(out):
    analysis=s.OUT/'analysis_001'
    s.check(analysis)
    out.mkdir(parents=True,exist_ok=False)
    attempts=s.pilot.read_csv(analysis/'attempts.csv')[1]
    costs=defaultdict(float); counts=Counter(); accounts=Counter()
    for a in attempts:
        costs[a['charge_basis']]+=float(a['charge_cny'])
        counts[a['charge_basis']]+=1
        accounts[a['account']+'/'+a['http_status']]+=1
    reps=s.read_json(analysis/'repeat_diagnostics.json')
    normalized={r['request_id']:r for r in s.pilot.jsonl(analysis/'normalized_responses.jsonl')}
    repeat_outputs=[dict(r,canonical_output=normalized[r['canonical_request_id']]['output_text'],
        repeat_output=normalized[r['request_id']]['output_text']) for r in reps if r['changed']]
    patient=s.read_json(analysis/'patient_metrics.json')
    patient_rows=[]
    for sid in sorted({r['subject_id'] for r in patient}):
        for author in ('llm','human'):
            rr={r['arm']:r for r in patient if r['subject_id']==sid and r['author_type']==author}
            c,v=rr['c48_reference'],rr['verifact_reference']
            patient_rows.append(dict(subject_id=sid,author_type=author,n=c['n'],
                c48_correct=sum(c['confusion_matrix'][i][i] for i in range(3)),
                verifact_correct=sum(v['confusion_matrix'][i][i] for i in range(3)),
                c48_mcc=c['mcc'],verifact_mcc=v['mcc'],delta_mcc=v['mcc']-c['mcc'],
                delta_pa=v['percent_agreement']-c['percent_agreement']))
    raw=next(n for n in s.pilot.subset_csv(s.RAW/'reference_ehr/ehr_noteevents.csv.gz','ROW_ID',{'471448'}))
    start=raw['TEXT'].index('RECOMMENDATIONS:')
    end=raw['TEXT'].index('These recommendations',start)
    source=dict(case_id='N642',subject_id=raw['SUBJECT_ID'],note_id=raw['ROW_ID'],
        raw_text_sha256=s.pilot.digest_text(raw['TEXT']),start=start,end_exclusive=end,text=raw['TEXT'][start:end],
        observation='C48 block 5 starts at raw character 4457 with STRICT NPO., losing the preceding if-clause. Published block 49 retains the condition; blocks 41/46 also retain PO diet permission. No reference or prediction was modified.')
    assert 'If there are any' in source['text'] and raw['TEXT'][4457:].startswith('STRICT NPO.')
    s.pilot.write_json(out/'cost_breakdown.json',dict(cny=dict(costs),attempts=dict(counts),accounts=dict(accounts),
        repeats=24,repeat_changes_by_arm=dict(Counter(r['arm'] for r in reps if r['changed'])),
        billing_caveat='Usage-based estimate plus unknown-request reservation, not a supplier invoice.'))
    s.pilot.write_json(out/'repeat_change_outputs.json',repeat_outputs)
    s.pilot.write_csv(out/'patient_differences.csv',patient_rows)
    s.pilot.write_json(out/'N642_raw_condition.json',source)
    s.seal(out,[analysis/'manifest.json',s.RAW/'reference_ehr/ehr_noteevents.csv.gz'],[Path(__file__)])
    print(s.pilot.canonical(dict(costs=dict(costs),accounts=dict(accounts),patients=patient_rows)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=s.OUT/'additional_diagnostics_001')
    run(p.parse_args().output)
