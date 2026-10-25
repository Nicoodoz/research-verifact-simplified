"""010 receipt-only unified scoring; separate system reference, Judge, and drift."""
from pathlib import Path
from collections import Counter
import argparse
import alignment_common as s
from io010 import stage,normalize
from score009 import evaluate_scope,movement


def score(output):
    output=output.resolve()
    assert not (s.OUT/'live/judge/runner.lock').exists(),'Wait for the stage to stop'
    prep=s.OUT/'preparation_001'
    s.check(prep)
    cohort=s.pilot.read_csv(prep/'cohort.csv')[1]
    rows={r['proposition_id']:r for r in cohort}
    inputs={x['proposition_id']:x for x in s.pilot.jsonl(prep/'inputs.jsonl')}
    assignments=s.pilot.read_csv(prep/'assignments.csv')[1]
    repeats=s.read_json(prep/'repeats.json')
    values,attempts=stage('judge')
    pids={x['request_id']:x['proposition_id'] for x in assignments+repeats}
    normalized={rid:normalize(v['job'],v['receipt'],pids[rid]) for rid,v in values.items()}
    predictions={arm:[] for arm in s.METHODS}
    lookup={arm:{} for arm in s.METHODS}
    for a in assignments:
        result=normalized[a['request_id']]
        if result['status']=='success':
            assert result['request_sha256']==a['body_sha256']
            predictions[a['arm']].append(dict(proposition_id=a['proposition_id'],verdict=result['verdict']))
            lookup[a['arm']][a['proposition_id']]=result['verdict']
    metrics=evaluate_scope(cohort,predictions,s.METHODS,[('c48_reference','verifact_reference')])
    old_c48=s.pilot.read_csv(s.PRIOR/'analysis_001/predictions_C48.csv')[1]
    oldmap={p['proposition_id']:p['verdict'] for p in old_c48}
    drift=evaluate_scope(cohort,dict(old_c48=old_c48,new_c48=predictions['c48_reference']),('old_c48','new_c48'),[('old_c48','new_c48')])
    transitions=[]
    for row in cohort:
        pid=row['proposition_id']
        c48,vf=lookup['c48_reference'].get(pid),lookup['verifact_reference'].get(pid)
        transitions.append(dict(row,case_id=inputs[pid]['case_id'],old_009_C48=oldmap[pid],c48_reference=c48,verifact_reference=vf,
            reference_change=movement(c48,vf,row['human_gt']),same_body_c48_drift=movement(oldmap[pid],c48,row['human_gt'])))
    repetition=[]
    for r in repeats:
        first,second=normalized[r['canonical_request_id']],normalized[r['request_id']]
        repetition.append(dict(r,canonical_status=first['status'],repeat_status=second['status'],
            canonical_verdict=first.get('verdict'),repeat_verdict=second.get('verdict'),
            changed=first.get('verdict')!=second.get('verdict'),diagnostic_only=True))
    per_patient=[]
    for sid in sorted({r['subject_id'] for r in cohort}):
        for author in ('llm','human'):
            own=[r for r in cohort if r['subject_id']==sid and r['author_type']==author]
            ids={r['proposition_id'] for r in own}
            for arm,pred in predictions.items():
                p=[x for x in pred if x['proposition_id'] in ids]
                value=s.pilot.evaluate(own,p,profile='none') if len(p)==len(own) else dict(status='blocked_missing')
                per_patient.append(dict(subject_id=sid,author_type=author,arm=arm,**value))
    complete=set(rows)
    for arm in s.METHODS:
        complete &= set(lookup[arm])
    sensitivity=dict(required=len(complete)!=650,original_n=650,common_n=len(complete),excluded_ids=sorted(set(rows)-complete),role='common-complete sensitivity only, not replacement primary')
    if sensitivity['required']:
        own=[r for r in cohort if r['proposition_id'] in complete]
        if all(len({r['subject_id'] for r in own if r['author_type']==a})>=2 for a in ('llm','human')):
            sensitivity['metrics']=evaluate_scope(own,predictions,s.METHODS,[('c48_reference','verifact_reference')])
    usage={}
    for arm in s.METHODS:
        rr=[normalized[a['request_id']] for a in assignments if a['arm']==arm]
        usage[arm]=dict(logical_conditions=len(rr),success=sum(r['status']=='success' for r in rr),
            input_tokens=sum(r.get('usage',{}).get('input_tokens',0) for r in rr),output_tokens=sum(r.get('usage',{}).get('output_tokens',0) for r in rr),
            adherence_flags=dict(Counter(x for r in rr for x in r.get('adherence_errors',[]))))
    summary=dict(claims=650,valid_predictions={a:len(p) for a,p in predictions.items()},
        failures=[dict(request_id=rid,proposition_id=r['proposition_id'],status=r['status'],errors=r.get('structural_errors')) for rid,r in normalized.items() if r['status']!='success'],
        transitions={a:dict(Counter(r['reference_change'] for r in transitions if r['author_type']==a)) for a in ('llm','human')},
        c48_drift={a:dict(Counter(r['same_body_c48_drift'] for r in transitions if r['author_type']==a)) for a in ('llm','human')},
        repeat_pairs=len(repetition),repeat_changes=sum(r['changed'] for r in repetition),
        task_used_or_reserved_cny=sum(r['charge_cny'] for r in attempts),http_attempts=len(attempts),http_status_counts=dict(Counter(r['http_status'] for r in attempts)),
        usage=usage,independent_audit=False)
    output.mkdir(parents=True,exist_ok=False)
    s.pilot.write_json(output/'metrics.json',metrics)
    s.pilot.write_json(output/'cross_run_c48_drift.json',drift)
    s.pilot.write_json(output/'system_reference_metrics.json',s.read_json(prep/'system_reference_metrics.json'))
    s.pilot.write_json(output/'completeness_sensitivity.json',sensitivity)
    s.pilot.write_json(output/'repeat_diagnostics.json',repetition)
    s.pilot.write_json(output/'patient_metrics.json',per_patient)
    s.pilot.write_json(output/'summary.json',summary)
    s.pilot.write_jsonl(output/'normalized_responses.jsonl',list(normalized.values()))
    s.pilot.write_csv(output/'transitions.csv',transitions)
    s.pilot.write_csv(output/'attempts.csv',attempts)
    for arm,pred in predictions.items():
        s.pilot.write_csv(output/('predictions_'+arm+'.csv'),pred,fields=['proposition_id','verdict'])
    s.seal(output,[prep/'manifest.json',s.OUT/'live/judge/state.json'],[Path(__file__),s.TASK/'io010.py',s.ROOT/'tasks/009_retrieval_baselines/score009.py'])
    print(s.pilot.canonical(summary))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=s.OUT/'analysis_001')
    score(p.parse_args().output)
