"""Post-hoc class coverage: retain all changed original-NS cases, including losses."""
from pathlib import Path
import alignment_common as s

if __name__=='__main__':
    original=s.pilot.jsonl(s.OUT/'review_001/packets.jsonl')
    ids={p['row']['proposition_id'] for p in original}
    rows=s.pilot.read_csv(s.OUT/'analysis_001/transitions.csv')[1]
    extra=[r for r in rows if r['human_gt']=='Not Supported' and r['c48_reference']!=r['verifact_reference'] and r['proposition_id'] not in ids]
    inputs={x['proposition_id']:x for x in s.pilot.jsonl(s.OUT/'preparation_001/inputs.jsonl')}
    outputs={x['request_id']:x for x in s.pilot.jsonl(s.OUT/'analysis_001/normalized_responses.jsonl')}
    assignments=s.pilot.read_csv(s.OUT/'preparation_001/assignments.csv')[1]
    request={(r['proposition_id'],r['arm']):r['request_id'] for r in assignments}
    released={r['proposition_id']:r['verdict'] for r in s.pilot.read_csv(s.OUT/'preparation_001/released_predictions.csv')[1]}
    for row in extra:
        pid=row['proposition_id']
        original.append(dict(row=row,reasons=['posthoc_all_original_NS_changes_for_class_coverage'],input=inputs[pid],
            released_system_verdict=released[pid],outputs={a:outputs[request[(pid,a)]] for a in s.METHODS}))
    original.sort(key=lambda p:p['row']['case_id'])
    out=s.OUT/'review_002';out.mkdir(exist_ok=False)
    s.pilot.write_jsonl(out/'packets.jsonl',original)
    s.pilot.write_json(out/'selection.json',dict(initial_cases=26,additional_cases=[r['case_id'] for r in extra],total_cases=len(original),posthoc=True,
        reason='Initial predefined sample had only one original NS. Add every remaining NS with different labels, not only successful cases; no new generation or primary-score changes.'))
    s.seal(out,[s.OUT/'review_001/manifest.json',s.OUT/'analysis_001/manifest.json'],[Path(__file__)])
    print(s.pilot.canonical(s.read_json(out/'selection.json')))
