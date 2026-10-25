"""Fixed-hash balanced changes, stable controls, and predeclared 009 loss probes."""
from collections import defaultdict,Counter
from pathlib import Path
import alignment_common as s

MANDATORY={'N071','N293','N302','N394','N430','N527','N561','N563','N585','N644'}

if __name__=='__main__':
    analysis=s.OUT/'analysis_001';s.check(analysis)
    rows=s.pilot.read_csv(analysis/'transitions.csv')[1]
    inputs={x['proposition_id']:x for x in s.pilot.jsonl(s.OUT/'preparation_001/inputs.jsonl')}
    outputs={x['request_id']:x for x in s.pilot.jsonl(analysis/'normalized_responses.jsonl')}
    assignments=s.pilot.read_csv(s.OUT/'preparation_001/assignments.csv')[1]
    request={(r['proposition_id'],r['arm']):r['request_id'] for r in assignments}
    old={r['proposition_id']:r['verdict'] for r in s.pilot.read_csv(s.OUT/'preparation_001/released_predictions.csv')[1]}
    chosen=defaultdict(list)
    rank=lambda r:s.pilot.digest_text('010/review/v1:'+r['proposition_id'])
    for r in rows:
        if r['case_id'] in MANDATORY:
            chosen[r['proposition_id']].append('predeclared_009_loss_probe')
        if r['case_id']=='N119':
            chosen[r['proposition_id']].append('predeclared_009_same_input_fluctuation_probe')
        if r['reference_change']=='missing':
            chosen[r['proposition_id']].append('retain_missing_case')
    for author in ('llm','human'):
        for outcome in ('improved','worsened','changed_wrong','stable_correct','stable_wrong'):
            part=sorted([r for r in rows if r['author_type']==author and r['reference_change']==outcome],key=rank)
            for row in part[:1 if outcome.startswith('stable') else 2]:
                chosen[row['proposition_id']].append('fixed_hash:'+author+'/'+outcome)
    packets=[]
    for row in rows:
        pid=row['proposition_id']
        if pid in chosen:
            packets.append(dict(row=row,reasons=chosen[pid],input=inputs[pid],released_system_verdict=old[pid],
                outputs={a:outputs[request[(pid,a)]] for a in s.METHODS}))
    out=s.OUT/'review_001';out.mkdir(exist_ok=False)
    s.pilot.write_jsonl(out/'packets.jsonl',packets)
    s.pilot.write_json(out/'selection.json',dict(cases=len(packets),case_ids=[p['row']['case_id'] for p in packets],
        by_gt=dict(Counter(p['row']['human_gt'] for p in packets)),by_author=dict(Counter(p['row']['author_type'] for p in packets)),
        cases_not_a_prevalence_sample=True,rule='Predeclared probes plus 2 fixed-hash changes/cell, 1 stable control/cell, retain failures'))
    s.seal(out,[analysis/'manifest.json',s.OUT/'preparation_001/manifest.json'],[Path(__file__)])
    print(s.pilot.canonical(s.read_json(out/'selection.json')))
